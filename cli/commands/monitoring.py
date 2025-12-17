"""
Monitoring and dashboard commands.

Commands:
- dashboard: Live monitoring dashboard (auto-refresh)
- logs: View logs with filtering and streaming
- health: System health check
"""

import asyncio
import time
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout

from cli.utils.validators import resolve_qube
from utils.time_format import format_timestamp_short, format_timestamp

console = Console()

# Monitoring app
app = typer.Typer(help="Monitoring and diagnostics")


@app.command("dashboard")
def dashboard_command(
    name_or_id: Optional[str] = typer.Argument(None, help="Specific Qube (optional, shows all if omitted)"),
    refresh: int = typer.Option(2, "--refresh", "-r", help="Refresh interval in seconds")
):
    """Live monitoring dashboard (auto-refresh)"""
    from cli.main import get_orchestrator

    orchestrator = get_orchestrator()

    console.print("[cyan]Loading dashboard...[/cyan]")
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")

    def generate_dashboard():
        """Generate dashboard content"""
        # Get all Qubes
        all_qubes = asyncio.run(orchestrator.list_qubes())

        if not all_qubes:
            return Panel("[yellow]No Qubes found. Create one with: qubes create[/yellow]", title="Dashboard")

        # Filter to specific Qube if provided
        if name_or_id:
            try:
                qube_info = resolve_qube(name_or_id, orchestrator, all_qubes)
                all_qubes = [qube_info]
            except ValueError as e:
                return Panel(f"[red]Error: {e}[/red]", title="Dashboard")

        # Build dashboard layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body")
        )

        # Header
        layout["header"].update(Panel(
            f"[bold cyan]Qubes Dashboard[/bold cyan]  •  [dim]Refresh: {refresh}s  •  Qubes: {len(all_qubes)}[/dim]",
            border_style="cyan"
        ))

        # Qubes table
        table = Table(title="Active Qubes", border_style="cyan", show_header=True)
        table.add_column("Name", style="cyan", width=15)
        table.add_column("ID", style="dim", width=18)
        table.add_column("Blocks", style="yellow", width=8)
        table.add_column("AI Model", style="green", width=20)
        table.add_column("Last Active", style="magenta", width=20)
        table.add_column("Status", style="blue", width=10)

        for qube_data in all_qubes:
            # Load Qube to get block count
            try:
                qube = asyncio.run(orchestrator.load_qube(qube_data["qube_id"]))

                # Get block count
                try:
                    all_blocks = qube.memory_chain.get_all_blocks() if hasattr(qube.memory_chain, 'get_all_blocks') else []
                except:
                    all_blocks = qube.memory_chain.blocks if hasattr(qube.memory_chain, 'blocks') else []

                block_count = len(all_blocks)

                # Get last active time
                last_active = all_blocks[-1].get("timestamp", 0) if all_blocks else 0
                last_active_str = format_timestamp_short(last_active) if last_active else "Never"

                # Determine status
                if last_active == 0:
                    status = "[dim]Idle[/dim]"
                else:
                    # Active within last hour
                    time_diff = time.time() - last_active
                    if time_diff < 3600:
                        status = "[green]Active[/green]"
                    elif time_diff < 86400:
                        status = "[yellow]Recent[/yellow]"
                    else:
                        status = "[dim]Idle[/dim]"

                table.add_row(
                    qube_data["name"],
                    qube_data["qube_id"][:16] + "...",
                    str(block_count),
                    qube_data["ai_model"],
                    last_active_str,
                    status
                )

            except Exception as e:
                # Handle loading errors
                table.add_row(
                    qube_data["name"],
                    qube_data["qube_id"][:16] + "...",
                    "[red]Error[/red]",
                    qube_data["ai_model"],
                    "[red]N/A[/red]",
                    "[red]Error[/red]"
                )

        layout["body"].update(table)

        return layout

    # Live dashboard
    try:
        with Live(generate_dashboard(), refresh_per_second=1/refresh, console=console) as live:
            while True:
                time.sleep(refresh)
                live.update(generate_dashboard())
    except KeyboardInterrupt:
        console.print("\n[cyan]Dashboard closed.[/cyan]\n")


@app.command("health")
def health_command(
    name_or_id: Optional[str] = typer.Argument(None, help="Specific Qube (optional)")
):
    """System health check"""
    from cli.main import get_orchestrator

    orchestrator = get_orchestrator()

    console.print("\n[cyan]Running health check...[/cyan]\n")

    # Get all Qubes
    all_qubes = asyncio.run(orchestrator.list_qubes())

    # Filter to specific Qube if provided
    if name_or_id:
        try:
            qube_info = resolve_qube(name_or_id, orchestrator, all_qubes)
            all_qubes = [qube_info]
        except ValueError as e:
            console.print(f"[red]✗ Error:[/red] {e}")
            raise typer.Exit(1)

    # Check each Qube
    healthy_count = 0
    warning_count = 0
    error_count = 0

    results = []

    for qube_data in all_qubes:
        qube_name = qube_data["name"]
        issues = []

        try:
            # Load Qube
            qube = asyncio.run(orchestrator.load_qube(qube_data["qube_id"]))

            # Check 1: Genesis block exists and valid
            if not hasattr(qube, 'genesis_block') or not qube.genesis_block:
                issues.append("Missing genesis block")

            # Check 2: Has blocks
            try:
                all_blocks = qube.memory_chain.get_all_blocks() if hasattr(qube.memory_chain, 'get_all_blocks') else []
            except:
                all_blocks = qube.memory_chain.blocks if hasattr(qube.memory_chain, 'blocks') else []

            if len(all_blocks) == 0:
                issues.append("No memory blocks (never used)")

            # Check 3: AI model configured
            if not getattr(qube.genesis_block, "ai_model"):
                issues.append("Missing AI model configuration")

            # Determine health status
            if len(issues) == 0:
                status = "[green]✓ Healthy[/green]"
                healthy_count += 1
            elif any("Missing" in i for i in issues):
                status = "[red]✗ Error[/red]"
                error_count += 1
            else:
                status = "[yellow]⚠ Warning[/yellow]"
                warning_count += 1

            results.append((qube_name, status, issues))

        except Exception as e:
            status = "[red]✗ Error[/red]"
            issues.append(f"Failed to load: {str(e)}")
            error_count += 1
            results.append((qube_name, status, issues))

    # Display results
    table = Table(title="Health Check Results", border_style="cyan", show_header=True)
    table.add_column("Qube", style="cyan", width=20)
    table.add_column("Status", width=15)
    table.add_column("Issues", style="yellow")

    for qube_name, status, issues in results:
        issues_str = ", ".join(issues) if issues else "None"
        table.add_row(qube_name, status, issues_str)

    console.print(table)

    # Summary
    total = len(all_qubes)
    summary = f"""
[bold]Summary:[/bold]
  Total Qubes: {total}
  [green]Healthy: {healthy_count}[/green]
  [yellow]Warnings: {warning_count}[/yellow]
  [red]Errors: {error_count}[/red]
"""

    overall_status = "Healthy" if error_count == 0 and warning_count == 0 else "Issues Detected"
    overall_color = "green" if error_count == 0 and warning_count == 0 else "yellow" if error_count == 0 else "red"

    console.print(Panel(
        summary.strip(),
        title=f"[{overall_color}]Overall Status: {overall_status}[/{overall_color}]",
        border_style=overall_color
    ))
    console.print()


@app.command("logs")
def logs_command(
    name_or_id: Optional[str] = typer.Argument(None, help="Specific Qube (optional)"),
    tail: int = typer.Option(100, "--tail", "-n", help="Number of lines to show"),
    level: Optional[str] = typer.Option(None, "--level", "-l", help="Filter by level (INFO, WARNING, ERROR)")
):
    """View logs with filtering (placeholder)"""

    console.print(Panel(
        "[yellow]Log viewing not yet implemented[/yellow]\n\n"
        "[dim]This feature will display:[/dim]\n"
        "  • Qube activity logs\n"
        "  • System events\n"
        "  • Error messages\n"
        "  • Debug information\n\n"
        "[dim]Coming soon in Phase 8.5![/dim]",
        title="Logs",
        border_style="yellow"
    ))
    console.print()


if __name__ == "__main__":
    app()
