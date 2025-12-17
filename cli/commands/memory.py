"""
Memory management commands.

Commands:
- memories: View memory blocks with pagination and filters
- memory: View specific block details
- summary: Generate AI-powered summary
- stats: Display memory statistics
- anchor: Anchor session blocks to permanent storage
"""

import asyncio
from typing import Optional, List
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from cli.utils.validators import resolve_qube
from utils.time_format import format_timestamp, format_timestamp_short

console = Console()

# Memory app
app = typer.Typer(help="Memory management and inspection")


@app.command("memories")
def memories_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of recent blocks to show"),
    block_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by block type"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search block content"),
    blocks_summary: bool = typer.Option(False, "--blocks", help="Show block type distribution"),
    json_output: bool = typer.Option(False, "--json", help="JSON output")
):
    """View memory blocks with pagination and filters"""
    from cli.main import get_orchestrator
    import json

    orchestrator = get_orchestrator()

    # Resolve Qube
    try:
        all_qubes = asyncio.run(orchestrator.list_qubes())
        qube_info = resolve_qube(name_or_id, orchestrator, all_qubes)
    except ValueError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)

    # Load Qube
    qube = asyncio.run(orchestrator.load_qube(qube_info["qube_id"]))
    favorite_color = getattr(qube.genesis_block, "favorite_color", "#4A90E2")

    # Get all blocks
    try:
        all_blocks = qube.memory_chain.get_all_blocks() if hasattr(qube.memory_chain, 'get_all_blocks') else []
    except:
        # Fallback: try to access blocks directly
        all_blocks = qube.memory_chain.blocks if hasattr(qube.memory_chain, 'blocks') else []

    if not all_blocks:
        console.print(f"[yellow]No memory blocks found for {qube.name}[/yellow]")
        console.print("[dim]Start a chat to create memories:[/dim] qubes chat " + qube.name)
        return

    # Show block type distribution if requested
    if blocks_summary:
        block_types = {}
        for block in all_blocks:
            block_type = block.get("type", "UNKNOWN")
            block_types[block_type] = block_types.get(block_type, 0) + 1

        console.print(Panel(
            _format_block_distribution(block_types, len(all_blocks)),
            title=f"Memory Block Distribution - {qube.name}",
            border_style=favorite_color
        ))
        return

    # Filter blocks
    filtered_blocks = all_blocks

    if block_type:
        filtered_blocks = [b for b in filtered_blocks if b.get("type", "").upper() == block_type.upper()]

    if search:
        filtered_blocks = [
            b for b in filtered_blocks
            if search.lower() in str(b.get("content", "")).lower()
        ]

    if not filtered_blocks:
        console.print(f"[yellow]No blocks match the filters[/yellow]")
        return

    # Limit to most recent
    recent_blocks = filtered_blocks[-limit:] if len(filtered_blocks) > limit else filtered_blocks
    recent_blocks.reverse()  # Most recent first

    # JSON output
    if json_output:
        output = {
            "qube": qube.name,
            "total_blocks": len(all_blocks),
            "filtered_blocks": len(filtered_blocks),
            "showing": len(recent_blocks),
            "blocks": [
                {
                    "index": i,
                    "type": b.get("type"),
                    "timestamp": b.get("timestamp"),
                    "content_preview": str(b.get("content", ""))[:100]
                }
                for i, b in enumerate(recent_blocks)
            ]
        }
        print(json.dumps(output, indent=2))
        return

    # Display table
    table = Table(
        title=f"\n{qube.name} - Recent Memories (Last {len(recent_blocks)} blocks)",
        border_style=favorite_color
    )
    table.add_column("#", style="dim", width=6)
    table.add_column("Type", style="cyan", width=15)
    table.add_column("Timestamp", style="yellow", width=20)
    table.add_column("Preview", style="white")

    for i, block in enumerate(recent_blocks):
        block_num = len(all_blocks) - i - (len(filtered_blocks) - len(recent_blocks))
        block_type_str = block.get("type", "UNKNOWN")
        timestamp = block.get("timestamp", 0)
        timestamp_str = format_timestamp_short(timestamp) if timestamp else "N/A"

        # Generate preview
        content = block.get("content", {})
        if isinstance(content, dict):
            preview = str(content.get("text", content.get("message", str(content))))[:60]
        else:
            preview = str(content)[:60]

        if len(str(content)) > 60:
            preview += "..."

        table.add_row(
            str(block_num),
            block_type_str,
            timestamp_str,
            preview
        )

    console.print(table)
    console.print(f"\n[dim]Total blocks: {len(all_blocks)} | Filtered: {len(filtered_blocks)} | Showing: {len(recent_blocks)}[/dim]")
    console.print(f"[dim]View details:[/dim] qubes memory {qube.name} <block_number>\n")


@app.command("memory")
def memory_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    block_num: int = typer.Argument(..., help="Block number (use -1 for latest)")
):
    """View detailed information about a specific memory block"""
    from cli.main import get_orchestrator

    orchestrator = get_orchestrator()

    # Resolve Qube
    try:
        all_qubes = asyncio.run(orchestrator.list_qubes())
        qube_info = resolve_qube(name_or_id, orchestrator, all_qubes)
    except ValueError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)

    # Load Qube
    qube = asyncio.run(orchestrator.load_qube(qube_info["qube_id"]))
    favorite_color = getattr(qube.genesis_block, "favorite_color", "#4A90E2")

    # Get all blocks
    try:
        all_blocks = qube.memory_chain.get_all_blocks() if hasattr(qube.memory_chain, 'get_all_blocks') else []
    except:
        all_blocks = qube.memory_chain.blocks if hasattr(qube.memory_chain, 'blocks') else []

    if not all_blocks:
        console.print(f"[yellow]No memory blocks found for {qube.name}[/yellow]")
        return

    # Handle negative indexing
    if block_num < 0:
        block_num = len(all_blocks) + block_num

    # Validate block number
    if block_num < 0 or block_num >= len(all_blocks):
        console.print(f"[red]✗ Invalid block number:[/red] {block_num}")
        console.print(f"[dim]Valid range: 0 to {len(all_blocks) - 1}[/dim]")
        return

    # Get block
    block = all_blocks[block_num]

    # Format block details
    block_type = block.get("type", "UNKNOWN")
    timestamp = block.get("timestamp", 0)
    timestamp_str = format_timestamp(timestamp) if timestamp else "N/A"
    block_hash = block.get("hash", "N/A")
    prev_hash = block.get("previous_hash", "N/A")
    content = block.get("content", {})

    # Format content
    if isinstance(content, dict):
        content_str = ""
        for key, value in content.items():
            content_str += f"[bold]{key}:[/bold] {value}\n"
    else:
        content_str = str(content)

    # Build info panel
    info_text = f"""
[bold]Block #{block_num}[/bold]

[bold]Type:[/bold] [{favorite_color}]{block_type}[/{favorite_color}]
[bold]Timestamp:[/bold] {timestamp_str}
[bold]Hash:[/bold] [dim]{block_hash[:32]}...[/dim] if len(block_hash) > 32 else [dim]{block_hash}[/dim]
[bold]Previous Hash:[/bold] [dim]{prev_hash[:32]}...[/dim] if len(prev_hash) > 32 else [dim]{prev_hash}[/dim]

[bold]Content:[/bold]
{content_str}
"""

    console.print(Panel(
        info_text.strip(),
        title=f"Memory Block - {qube.name}",
        border_style=favorite_color
    ))
    console.print()


@app.command("summary")
def summary_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    blocks: int = typer.Option(100, "--blocks", "-n", help="Number of recent blocks to summarize"),
    save: bool = typer.Option(False, "--save", help="Save summary as SUMMARY block"),
    auto_yes: bool = typer.Option(False, "--auto-yes", "-y", help="Skip confirmation")
):
    """Generate AI-powered summary of memories"""
    from cli.main import get_orchestrator

    orchestrator = get_orchestrator()

    # Resolve Qube
    try:
        all_qubes = asyncio.run(orchestrator.list_qubes())
        qube_info = resolve_qube(name_or_id, orchestrator, all_qubes)
    except ValueError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)

    # Load Qube
    qube = asyncio.run(orchestrator.load_qube(qube_info["qube_id"]))
    favorite_color = getattr(qube.genesis_block, "favorite_color", "#4A90E2")

    console.print(f"\n[{favorite_color}]Generating summary of last {blocks} blocks for {qube.name}...[/{favorite_color}]\n")

    # Get blocks to summarize
    try:
        all_blocks = qube.memory_chain.get_all_blocks() if hasattr(qube.memory_chain, 'get_all_blocks') else []
    except:
        all_blocks = qube.memory_chain.blocks if hasattr(qube.memory_chain, 'blocks') else []

    if not all_blocks:
        console.print(f"[yellow]No memory blocks found for {qube.name}[/yellow]")
        return

    recent_blocks = all_blocks[-blocks:] if len(all_blocks) > blocks else all_blocks

    # Build summary prompt (simplified - in production would use AI)
    block_types = {}
    for block in recent_blocks:
        block_type = block.get("type", "UNKNOWN")
        block_types[block_type] = block_types.get(block_type, 0) + 1

    # Generate simple summary
    summary_text = f"""
[bold]Memory Summary for {qube.name}[/bold]
[dim]Analyzing {len(recent_blocks)} blocks...[/dim]

[bold]Block Type Distribution:[/bold]
"""

    for block_type, count in sorted(block_types.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(recent_blocks)) * 100
        summary_text += f"  • {block_type}: {count} blocks ({percentage:.1f}%)\n"

    summary_text += f"""
[bold]Key Metrics:[/bold]
  • Total Blocks Analyzed: {len(recent_blocks)}
  • Time Span: {format_timestamp(recent_blocks[0].get('timestamp', 0))} to {format_timestamp(recent_blocks[-1].get('timestamp', 0))}

[dim]Note: AI-powered summary generation coming soon![/dim]
"""

    console.print(Panel(
        summary_text.strip(),
        title="Memory Summary",
        border_style=favorite_color
    ))

    if save:
        if not auto_yes:
            if not Confirm.ask("\nSave this summary as a SUMMARY block?", default=True):
                console.print("[yellow]Summary not saved.[/yellow]")
                return

        console.print("[yellow]⚠️  Summary block saving not yet implemented[/yellow]")

    console.print()


@app.command("stats")
def stats_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    json_output: bool = typer.Option(False, "--json", help="JSON output")
):
    """Display memory and interaction statistics"""
    from cli.main import get_orchestrator
    import json

    orchestrator = get_orchestrator()

    # Resolve Qube
    try:
        all_qubes = asyncio.run(orchestrator.list_qubes())
        qube_info = resolve_qube(name_or_id, orchestrator, all_qubes)
    except ValueError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)

    # Load Qube
    qube = asyncio.run(orchestrator.load_qube(qube_info["qube_id"]))
    favorite_color = getattr(qube.genesis_block, "favorite_color", "#4A90E2")

    # Get blocks
    try:
        all_blocks = qube.memory_chain.get_all_blocks() if hasattr(qube.memory_chain, 'get_all_blocks') else []
    except:
        all_blocks = qube.memory_chain.blocks if hasattr(qube.memory_chain, 'blocks') else []

    # Calculate statistics
    total_blocks = len(all_blocks)
    block_types = {}
    for block in all_blocks:
        block_type = block.get("type", "UNKNOWN")
        block_types[block_type] = block_types.get(block_type, 0) + 1

    # Birth and last active
    birth_timestamp = getattr(qube.genesis_block, "birth_timestamp", 0)
    birth_date = format_timestamp(birth_timestamp) if birth_timestamp else "Unknown"

    last_active = all_blocks[-1].get("timestamp", 0) if all_blocks else 0
    last_active_str = format_timestamp(last_active) if last_active else "Never"

    # JSON output
    if json_output:
        stats = {
            "qube": qube.name,
            "qube_id": qube.qube_id,
            "birth_date": birth_date,
            "last_active": last_active_str,
            "total_blocks": total_blocks,
            "block_types": block_types
        }
        print(json.dumps(stats, indent=2))
        return

    # Display stats panel
    stats_text = f"""
[bold]Memory Statistics[/bold]

[bold]Total Blocks:[/bold] {total_blocks}
[bold]Birth Date:[/bold] {birth_date}
[bold]Last Active:[/bold] {last_active_str}

[bold]Block Type Distribution:[/bold]
"""

    for block_type, count in sorted(block_types.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_blocks * 100) if total_blocks > 0 else 0
        bar_length = int(percentage / 5)  # Scale to 20 chars max
        bar = "█" * bar_length
        stats_text += f"  {block_type:20} {bar:20} {count:4} ({percentage:5.1f}%)\n"

    console.print(Panel(
        stats_text.strip(),
        title=f"📊 {qube.name} Statistics",
        border_style=favorite_color
    ))
    console.print()


@app.command("anchor")
def anchor_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    auto_yes: bool = typer.Option(False, "--auto-yes", "-y", help="Skip confirmation"),
    create_summary: bool = typer.Option(True, "--summary/--no-summary", help="Create summary block (default: yes)")
):
    """Anchor current session blocks to permanent storage"""
    from cli.main import get_orchestrator

    orchestrator = get_orchestrator()

    # Resolve Qube
    try:
        all_qubes = asyncio.run(orchestrator.list_qubes())
        qube_info = resolve_qube(name_or_id, orchestrator, all_qubes)
    except ValueError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)

    # Load Qube
    qube = asyncio.run(orchestrator.load_qube(qube_info["qube_id"]))
    favorite_color = getattr(qube.genesis_block, "favorite_color", "#4A90E2")

    # Check if there's an active session
    if not qube.current_session:
        console.print(f"\n[yellow]No active session for {qube.name}[/yellow]")
        console.print("[dim]Start a chat to create session blocks:[/dim] qubes chat " + qube.name + "\n")
        return

    # Get session block count
    session_block_count = len(qube.current_session.session_blocks)

    if session_block_count == 0:
        console.print(f"\n[yellow]No session blocks to anchor for {qube.name}[/yellow]\n")
        return

    # Show session info
    console.print(f"\n[bold]Session Information:[/bold]")
    console.print(f"  Qube: [{favorite_color}]{qube.name}[/{favorite_color}]")
    console.print(f"  Session ID: [dim]{qube.current_session.session_id}[/dim]")
    console.print(f"  Session Blocks: [cyan]{session_block_count}[/cyan]")
    console.print(f"  Create Summary: [{'green' if create_summary else 'red'}]{'Yes' if create_summary else 'No'}[/{'green' if create_summary else 'red'}]")

    # Confirm anchoring
    if not auto_yes:
        console.print()
        if not Confirm.ask(f"[bold]Anchor all {session_block_count} blocks to permanent storage?[/bold]", default=True):
            console.print("[yellow]Anchoring cancelled.[/yellow]\n")
            return

    # Perform anchoring
    console.print(f"\n[{favorite_color}]Anchoring {session_block_count} blocks...[/{favorite_color}]")

    try:
        converted_blocks = asyncio.run(qube.current_session.anchor_to_chain(create_summary=create_summary))

        console.print(f"\n[green]✓ Successfully anchored {len(converted_blocks)} blocks to permanent memory[/green]")

        # Show range of anchored blocks
        if converted_blocks:
            first_block = converted_blocks[0].block_number
            last_block = converted_blocks[-1].block_number
            console.print(f"[dim]  Block range: {first_block} - {last_block}[/dim]")

            if create_summary and len(converted_blocks) > session_block_count:
                console.print(f"[dim]  Summary block created: {last_block}[/dim]")

        # Show new chain length
        chain_length = qube.memory_chain.get_chain_length()
        console.print(f"[dim]  New chain length: {chain_length}[/dim]\n")

        console.print(f"[green]Session cleared and files cleaned up.[/green]\n")

    except Exception as e:
        console.print(f"\n[red]✗ Anchoring failed:[/red] {str(e)}\n")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


def _format_block_distribution(block_types: dict, total: int) -> str:
    """Format block type distribution for display"""
    text = ""
    for block_type, count in sorted(block_types.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        bar_length = int(percentage / 5)  # Scale to 20 chars max
        bar = "█" * bar_length
        text += f"{block_type:20} {bar:20} {count:4}\n"

    text += f"\n[bold]Total: {total} blocks[/bold]"
    return text


if __name__ == "__main__":
    app()
