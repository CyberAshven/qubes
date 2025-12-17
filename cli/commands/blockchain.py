"""
Blockchain and NFT commands.

Commands:
- nft: View NFT status and metadata
- verify-nft: Verify NFT authenticity on blockchain
- balance: Check blockchain wallet balance
- transactions: View transaction history
"""

import asyncio
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cli.utils.validators import resolve_qube
from utils.time_format import format_timestamp_short

console = Console()

# Blockchain app
app = typer.Typer(help="Blockchain and NFT operations")


@app.command("nft")
def nft_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    json_output: bool = typer.Option(False, "--json", help="JSON output")
):
    """View NFT status and metadata"""
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

    # Get NFT data from genesis block
    nft_category = getattr(qube.genesis_block, 'nft_category_id')
    mint_txid = getattr(qube.genesis_block, 'mint_txid')
    home_blockchain = getattr(qube.genesis_block, 'home_blockchain', 'bitcoincash')

    if not nft_category:
        console.print(Panel(
            "[yellow]NFT not minted for this Qube[/yellow]\n\n"
            "[dim]To mint an NFT:[/dim]\n"
            "  • Qube must have a wallet address\n"
            "  • Use blockchain integration tools\n"
            "  • NFT category ID will be stored in genesis block\n\n"
            "[dim]Backend support available:[/dim]\n"
            "  • blockchain/nft_minting.py ✓\n"
            "  • blockchain/nft_verification.py ✓\n"
            "  • blockchain/ipfs_integration.py ✓",
            title=f"{qube.name} - NFT Status",
            border_style="yellow"
        ))
        return

    # Display NFT information
    from utils.time_format import format_timestamp
    birth_date = format_timestamp(getattr(qube.genesis_block, "birth_timestamp"))

    nft_info = f"""
[bold]Status:[/bold] [green]✓ Minted[/green]
[bold]Blockchain:[/bold] {home_blockchain.title()}
[bold]Token ID:[/bold] [cyan]{nft_category}[/cyan]

[bold]Metadata:[/bold]
  [bold]Name:[/bold] {qube.name}
  [bold]Symbol:[/bold] QUBE-{qube.name.upper()[:4]}
  [bold]Birth Date:[/bold] {birth_date}
  [bold]Genesis Hash:[/bold] [dim]{getattr(qube.genesis_block, 'hash', 'N/A')[:32]}...[/dim]

"""

    if mint_txid:
        nft_info += f"""[bold]Transaction:[/bold]
  [bold]TX Hash:[/bold] [dim]{mint_txid[:32]}...[/dim]
  [bold]View on Explorer:[/bold]
  [cyan]https://explorer.bitcoin.com/bch/tx/{mint_txid}[/cyan]
"""
    else:
        nft_info += "[dim]Transaction details not available[/dim]\n"

    nft_info += "\n[dim]Owner:[/dim] Self-owned by Qube"

    console.print(Panel(
        nft_info.strip(),
        title=f"{qube.name} - NFT",
        border_style=favorite_color
    ))
    console.print()


@app.command("verify-nft")
def verify_nft_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID")
):
    """Verify NFT authenticity on blockchain"""
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

    nft_category = getattr(qube.genesis_block, 'nft_category_id')

    if not nft_category:
        console.print(f"[yellow]No NFT found for {qube.name}[/yellow]")
        return

    console.print(f"\n[cyan]Verifying {qube.name} NFT on blockchain...[/cyan]\n")

    # Placeholder verification
    console.print(Panel(
        f"[yellow]NFT verification integration pending[/yellow]\n\n"
        f"[dim]Verification steps:[/dim]\n"
        f"  ✓ NFT Category ID: {nft_category}\n"
        f"  • Query blockchain for transaction\n"
        f"  • Verify confirmations (pending)\n"
        f"  • Validate metadata hash (pending)\n"
        f"  • Check genesis hash match (pending)\n"
        f"  • Verify token ID (pending)\n\n"
        f"[dim]Backend modules ready:[/dim]\n"
        f"  • blockchain/nft_verification.py ✓\n"
        f"  • Integration with blockchain explorer pending",
        title="NFT Verification",
        border_style="cyan"
    ))
    console.print()


@app.command("balance")
def balance_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    json_output: bool = typer.Option(False, "--json", help="JSON output")
):
    """Check blockchain wallet balance"""
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
        f"[yellow]Wallet balance checking not yet integrated[/yellow]\n\n"
        f"[dim]This command will display:[/dim]\n"
        f"  • Wallet address\n"
        f"  • Balance in native currency (BCH, BTC, ETH)\n"
        f"  • USD value\n"
        f"  • Unconfirmed balance\n"
        f"  • Transaction count\n\n"
        f"[dim]Backend support:[/dim]\n"
        f"  • blockchain/wallet.py ✓\n"
        f"  • Integration with blockchain APIs pending",
        title=f"{qube.name} - Wallet Balance",
        border_style=favorite_color
    ))
    console.print()


@app.command("transactions")
def transactions_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of recent transactions"),
    tx_type: Optional[str] = typer.Option(None, "--type", help="Filter by type (sent, received, all)")
):
    """View transaction history"""
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
        f"[yellow]Transaction history not yet integrated[/yellow]\n\n"
        f"[dim]This command will display:[/dim]\n"
        f"  • Transaction type (Send/Receive)\n"
        f"  • Timestamp\n"
        f"  • Amount\n"
        f"  • Transaction hash\n"
        f"  • Confirmation count\n\n"
        f"[dim]Filters:[/dim]\n"
        f"  • --limit N: Show N recent transactions\n"
        f"  • --type sent|received|all: Filter by type",
        title=f"{qube.name} - Transactions",
        border_style=favorite_color
    ))
    console.print()


if __name__ == "__main__":
    app()
