"""
Debugging and Monitoring CLI Commands

Tools for monitoring Qube health, memory usage, network status, etc.
From docs/13_Implementation_Phases.md Phase 8
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(name="debug", help="Debugging and monitoring tools")
console = Console()


@app.command()
def status(qube_id: Optional[str] = None):
    """
    Show system status and health

    Args:
        qube_id: Optional Qube ID to show specific Qube status
    """
    console.print(Panel(
        "[bold cyan]Qubes System Status[/bold cyan]",
        border_style="cyan"
    ))

    if qube_id:
        # Show specific Qube status
        console.print(f"\n[cyan]Qube Status:[/cyan] {qube_id}\n")
        # TODO: Implement Qube-specific status
        console.print("[yellow]⚠ Qube status not yet implemented[/yellow]")
    else:
        # Show global status
        _show_global_status()


def _show_global_status():
    """Show global system status"""
    import psutil
    from datetime import datetime

    # System resources
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Qubes count
    qubes_dir = Path("data/users")
    qube_count = 0
    if qubes_dir.exists():
        for user_dir in qubes_dir.iterdir():
            qubes_subdir = user_dir / "qubes"
            if qubes_subdir.exists():
                qube_count += len(list(qubes_subdir.iterdir()))

    status_text = f"""
[bold]Timestamp:[/bold] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

[bold cyan]System Resources[/bold cyan]
[bold]CPU Usage:[/bold] {cpu_percent}%
[bold]Memory Usage:[/bold] {memory.percent}% ({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)
[bold]Disk Usage:[/bold] {disk.percent}% ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)

[bold cyan]Qubes[/bold cyan]
[bold]Total Qubes:[/bold] {qube_count}

[bold cyan]Network[/bold cyan]
[bold]Status:[/bold] [yellow]Not implemented[/yellow]

[bold cyan]Blockchain[/bold cyan]
[bold]Status:[/bold] [yellow]Not implemented[/yellow]
"""

    console.print(status_text)


@app.command()
def memory(qube_id: str):
    """
    Show memory chain statistics for a Qube

    Args:
        qube_id: Qube ID (can be partial)
    """
    console.print(f"\n[cyan]Loading memory statistics for Qube: {qube_id}...[/cyan]\n")

    # Find Qube directory
    qubes_dir = Path("data/users")
    qube_dir = None

    if qubes_dir.exists():
        for user_dir in qubes_dir.iterdir():
            qubes_subdir = user_dir / "qubes"
            if qubes_subdir.exists():
                for qd in qubes_subdir.iterdir():
                    qube_json = qd / "qube.json"
                    if qube_json.exists():
                        import json
                        with open(qube_json, "r") as f:
                            data = json.load(f)
                            if data["qube_id"].startswith(qube_id):
                                qube_dir = qd
                                break

    if not qube_dir:
        console.print(f"[red]✗ Qube not found: {qube_id}[/red]")
        return

    # Analyze memory chain
    memory_dir = qube_dir / "memory"

    if not memory_dir.exists():
        console.print("[yellow]⚠ Memory chain directory not found[/yellow]")
        return

    # Count blocks by type from JSON files
    from collections import Counter
    import json

    try:
        blocks_dir = memory_dir / "blocks" / "permanent"
        if not blocks_dir.exists():
            console.print("[yellow]⚠ Blocks directory not found[/yellow]")
            return

        block_types = Counter()
        total_size = 0
        block_count = 0

        # Read all JSON block files
        for block_file in blocks_dir.glob("*.json"):
            try:
                with open(block_file, 'r') as f:
                    block = json.load(f)

                block_count += 1
                total_size += block_file.stat().st_size
                block_types[block.get("block_type", "UNKNOWN")] += 1
            except Exception as e:
                console.print(f"[yellow]⚠ Failed to read {block_file.name}: {e}[/yellow]")

        # Display statistics
        table = Table(title=f"\n📊 Memory Chain Statistics", border_style="cyan")
        table.add_column("Metric", style="cyan bold")
        table.add_column("Value", style="green")

        table.add_row("Total Blocks", str(block_count))
        table.add_row("Total Size", f"{total_size / 1024:.2f} KB")
        table.add_row("Average Block Size", f"{total_size / block_count if block_count > 0 else 0:.2f} bytes")

        console.print(table)

        # Block type distribution
        type_table = Table(title="\n📦 Block Type Distribution", border_style="cyan")
        type_table.add_column("Block Type", style="magenta")
        type_table.add_column("Count", style="yellow")
        type_table.add_column("Percentage", style="green")

        for block_type, count in block_types.most_common():
            percentage = (count / block_count * 100) if block_count > 0 else 0
            type_table.add_row(
                block_type,
                str(count),
                f"{percentage:.1f}%"
            )

        console.print(type_table)
        console.print()

    except Exception as e:
        console.print(f"[red]✗ Error reading memory chain:[/red] {str(e)}")


@app.command()
def network():
    """Show P2P network status"""
    console.print(Panel(
        "[bold cyan]P2P Network Status[/bold cyan]",
        border_style="cyan"
    ))

    console.print("\n[yellow]⚠ Network monitoring not yet implemented[/yellow]\n")

    # TODO: Implement network status
    # - Connected peers
    # - Network topology
    # - Message stats
    # - DHT status


@app.command()
def logs(
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output")
):
    """
    Show recent logs

    Args:
        lines: Number of log lines to display
        follow: Follow log output (tail -f behavior)
    """
    log_file = Path("logs/qubes.log")

    if not log_file.exists():
        console.print("[yellow]⚠ Log file not found[/yellow]")
        return

    if follow:
        console.print(f"[cyan]Following logs (Ctrl+C to stop)...[/cyan]\n")

        # Tail -f implementation
        import time

        with open(log_file, "r") as f:
            # Go to end of file
            f.seek(0, 2)

            try:
                while True:
                    line = f.readline()
                    if line:
                        console.print(line.rstrip())
                    else:
                        time.sleep(0.1)
            except KeyboardInterrupt:
                console.print("\n[cyan]Stopped following logs[/cyan]")
    else:
        # Show last N lines
        with open(log_file, "r") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]

            for line in recent_lines:
                console.print(line.rstrip())


@app.command()
def config():
    """Show current configuration"""
    from config import SettingsManager

    settings_manager = SettingsManager()
    global_settings = settings_manager.load_global_settings()

    # Display settings as tree
    tree = Tree("⚙️  [bold cyan]Global Settings[/bold cyan]")

    ai_branch = tree.add("[bold]AI Configuration[/bold]")
    ai_branch.add(f"Default Model: [green]{global_settings.default_ai_model}[/green]")
    ai_branch.add(f"Default Voice: [green]{global_settings.default_voice_model}[/green]")
    ai_branch.add(f"Temperature: [green]{global_settings.default_ai_temperature}[/green]")

    memory_branch = tree.add("[bold]Memory Configuration[/bold]")
    memory_branch.add(f"Max Session Blocks: [green]{global_settings.max_session_blocks}[/green]")
    memory_branch.add(f"Auto Anchor Threshold: [green]{global_settings.auto_anchor_threshold}[/green]")

    network_branch = tree.add("[bold]Network Configuration[/bold]")
    network_branch.add(f"Mode: [green]{global_settings.network_mode}[/green]")
    network_branch.add(f"P2P Port: [green]{global_settings.p2p_port}[/green]")

    audio_branch = tree.add("[bold]Audio Configuration[/bold]")
    audio_branch.add(f"TTS Enabled: [green]{global_settings.tts_enabled}[/green]")
    audio_branch.add(f"STT Enabled: [green]{global_settings.stt_enabled}[/green]")
    audio_branch.add(f"Cache Size: [green]{global_settings.audio_cache_size_mb}MB[/green]")

    budget_branch = tree.add("[bold]Cost Management[/bold]")
    budget_branch.add(f"Monthly Budget: [green]${global_settings.monthly_budget_usd}[/green]")
    budget_branch.add(f"Alert Threshold: [green]{global_settings.alert_threshold_percent}%[/green]")

    security_branch = tree.add("[bold]Security[/bold]")
    security_branch.add(f"Require Master Password: [green]{global_settings.require_master_password}[/green]")
    security_branch.add(f"Session Timeout: [green]{global_settings.session_timeout_minutes}min[/green]")

    console.print()
    console.print(tree)
    console.print()


if __name__ == "__main__":
    app()
