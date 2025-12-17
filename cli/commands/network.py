"""
Network and P2P commands.

Commands:
- network: View network status and peers
- peers: List connected peers
- send: Send P2P message to another Qube
- inbox: View inbox messages
"""

import asyncio
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cli.utils.validators import resolve_qube

console = Console()

# Network app
app = typer.Typer(help="Network and P2P operations")


@app.command("status")
def network_status_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    json_output: bool = typer.Option(False, "--json", help="JSON output")
):
    """View network status and peers"""
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

    console.print(Panel(
        f"[yellow]P2P network status not yet fully integrated[/yellow]\n\n"
        f"[dim]This command will display:[/dim]\n"
        f"  • Peer ID (libp2p)\n"
        f"  • Online/Offline status\n"
        f"  • Uptime\n"
        f"  • Active peer connections\n"
        f"  • Known peers count\n"
        f"  • Bootstrap node status\n"
        f"  • Subscribed topics (GossipSub)\n"
        f"  • Network statistics (messages sent/received, bandwidth)\n\n"
        f"[dim]Backend modules ready:[/dim]\n"
        f"  • network/p2p/discovery.py ✓\n"
        f"  • network/p2p/messaging.py ✓\n"
        f"  • network/p2p/gossipsub.py ✓",
        title=f"{qube.name} - Network Status",
        border_style=favorite_color
    ))
    console.print()


@app.command("peers")
def peers_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    online_only: bool = typer.Option(False, "--online", help="Show only online peers"),
    offline_only: bool = typer.Option(False, "--offline", help="Show only offline peers")
):
    """List connected peers"""
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

    console.print(Panel(
        f"[yellow]Peer discovery not yet fully integrated[/yellow]\n\n"
        f"[dim]This command will display:[/dim]\n"
        f"  • Qube name\n"
        f"  • Peer ID (libp2p)\n"
        f"  • Online/Offline status\n"
        f"  • Last seen timestamp\n"
        f"  • Connection latency\n\n"
        f"[dim]Filters:[/dim]\n"
        f"  • --online: Show only online peers\n"
        f"  • --offline: Show only offline peers",
        title=f"{qube.name} - Peers",
        border_style=favorite_color
    ))
    console.print()


@app.command("send")
def send_command(
    sender: str = typer.Argument(..., help="Sender Qube name or ID"),
    recipient: str = typer.Argument(..., help="Recipient Qube name or ID"),
    message: str = typer.Argument(..., help="Message to send"),
    encrypt: bool = typer.Option(False, "--encrypt", help="Encrypt message"),
    priority: str = typer.Option("normal", "--priority", help="Message priority (high, normal, low)")
):
    """Send P2P message to another Qube"""
    from cli.main import get_orchestrator

    orchestrator = get_orchestrator()

    # Resolve both Qubes
    try:
        all_qubes = asyncio.run(orchestrator.list_qubes())
        sender_info = resolve_qube(sender, orchestrator, all_qubes)
        recipient_info = resolve_qube(recipient, orchestrator, all_qubes)
    except ValueError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)

    # Load sender Qube
    sender_qube = asyncio.run(orchestrator.load_qube(sender_info["qube_id"]))

    console.print(Panel(
        f"[yellow]P2P messaging not yet fully integrated[/yellow]\n\n"
        f"[dim]This command will:[/dim]\n"
        f"  • Send message from {sender_qube.name} to {recipient_info['name']}\n"
        f"  • Support optional encryption\n"
        f"  • Allow priority setting (high, normal, low)\n"
        f"  • Support file attachments\n"
        f"  • Show delivery confirmation\n\n"
        f"[dim]Message:[/dim] {message}\n"
        f"[dim]Encrypted:[/dim] {encrypt}\n"
        f"[dim]Priority:[/dim] {priority}",
        title="P2P Message",
        border_style="cyan"
    ))
    console.print()


@app.command("inbox")
def inbox_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    unread_only: bool = typer.Option(False, "--unread", help="Show only unread messages"),
    from_qube: Optional[str] = typer.Option(None, "--from", help="Filter by sender")
):
    """View inbox messages"""
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

    console.print(Panel(
        f"[yellow]P2P inbox not yet fully integrated[/yellow]\n\n"
        f"[dim]This command will display:[/dim]\n"
        f"  • Sender name and ID\n"
        f"  • Message timestamp\n"
        f"  • Message preview\n"
        f"  • Read/Unread status\n"
        f"  • Priority indicator\n\n"
        f"[dim]Filters:[/dim]\n"
        f"  • --unread: Show only unread messages\n"
        f"  • --from <qube>: Filter by sender\n\n"
        f"[dim]Commands:[/dim]\n"
        f"  • qubes network read <msg_id>: Read full message\n"
        f"  • qubes network reply <msg_id>: Reply to message",
        title=f"{qube.name} - Inbox",
        border_style=favorite_color
    ))
    console.print()


if __name__ == "__main__":
    app()
