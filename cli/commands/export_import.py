"""
Export and import commands with encryption.

Commands:
- export: Export Qube to encrypted .qube file
- import: Import Qube from .qube file
"""

import asyncio
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from cli.utils.validators import resolve_qube

console = Console()

# Export/Import app
app = typer.Typer(help="Export and import Qubes")


@app.command("export")
def export_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    output_path: Optional[str] = typer.Argument(None, help="Output file path (.qube)"),
    password: Optional[str] = typer.Option(None, "--password", help="Encryption password (for scripting)"),
    auto_yes: bool = typer.Option(False, "--auto-yes", "-y", help="Skip confirmation")
):
    """Export Qube to encrypted .qube file"""
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

    # Determine output path
    if not output_path:
        output_path = f"{qube.name.lower().replace(' ', '_')}.qube"

    output_file = Path(output_path)

    # Check if file exists
    if output_file.exists() and not auto_yes:
        if not Confirm.ask(f"[yellow]File {output_path} already exists. Overwrite?[/yellow]", default=False):
            console.print("[yellow]Export cancelled.[/yellow]")
            return

    # Get password if not provided
    if not password:
        password = Prompt.ask("\nEnter master password for export encryption", password=True)
        password_confirm = Prompt.ask("Confirm password", password=True)

        if password != password_confirm:
            console.print("[red]✗ Passwords do not match[/red]")
            raise typer.Exit(1)

    # Count data to export
    try:
        all_blocks = qube.memory_chain.get_all_blocks() if hasattr(qube.memory_chain, 'get_all_blocks') else []
    except:
        all_blocks = qube.memory_chain.blocks if hasattr(qube.memory_chain, 'blocks') else []

    block_count = len(all_blocks)

    # Preview
    if not auto_yes:
        preview_text = f"""
[bold]Export Preview:[/bold]

[bold]Qube:[/bold] {qube.name}
[bold]Qube ID:[/bold] {qube.qube_id}
[bold]Output File:[/bold] {output_path}

[bold]Data to Export:[/bold]
  • Genesis block
  • {block_count} memory blocks
  • Settings and configuration
  • NFT metadata

[bold]Encryption:[/bold] AES-256-GCM
[bold]Format:[/bold] MessagePack (.qube)

[dim]Note: Relationships and network data are not exported[/dim]
"""

        console.print(Panel(preview_text.strip(), border_style=favorite_color))

        if not Confirm.ask("\nProceed with export?", default=True):
            console.print("[yellow]Export cancelled.[/yellow]")
            return

    # Export (placeholder - actual implementation would use encryption)
    console.print("\n")

    console.print(Panel(
        f"[yellow]Full export with encryption not yet implemented[/yellow]\n\n"
        f"[dim]Export process will:[/dim]\n"
        f"  • Serialize Qube data to MessagePack format\n"
        f"  • Derive encryption key from password (PBKDF2)\n"
        f"  • Encrypt data with AES-256-GCM\n"
        f"  • Write to .qube file\n\n"
        f"[bold]Planned data structure:[/bold]\n"
        f"  • metadata (unencrypted): version, name, qube_id, export_date\n"
        f"  • encrypted_data: genesis_block, memory_blocks[], settings\n\n"
        f"[dim]File would be created at:[/dim] [cyan]{output_path}[/cyan]\n"
        f"[dim]Estimated size:[/dim] ~{block_count * 0.05:.1f} MB",
        title="Export Preview",
        border_style=favorite_color
    ))
    console.print()


@app.command("import")
def import_command(
    file_path: str = typer.Argument(..., help=".qube file to import"),
    password: Optional[str] = typer.Option(None, "--password", help="Decryption password (for scripting)"),
    auto_yes: bool = typer.Option(False, "--auto-yes", "-y", help="Skip confirmation")
):
    """Import Qube from .qube file"""
    from cli.main import get_orchestrator

    orchestrator = get_orchestrator()

    import_file = Path(file_path)

    # Check if file exists
    if not import_file.exists():
        console.print(f"[red]✗ File not found:[/red] {file_path}")
        raise typer.Exit(1)

    # Check file extension
    if import_file.suffix != ".qube":
        console.print(f"[yellow]⚠ Warning:[/yellow] File does not have .qube extension")
        if not auto_yes:
            if not Confirm.ask("Continue anyway?", default=False):
                console.print("[yellow]Import cancelled.[/yellow]")
                return

    # Get password if not provided
    if not password:
        password = Prompt.ask("\nEnter decryption password", password=True)

    # Import (placeholder)
    console.print("\n")

    console.print(Panel(
        f"[yellow]Full import with decryption not yet implemented[/yellow]\n\n"
        f"[dim]Import process will:[/dim]\n"
        f"  • Read .qube file\n"
        f"  • Derive decryption key from password (PBKDF2)\n"
        f"  • Decrypt data with AES-256-GCM\n"
        f"  • Deserialize MessagePack data\n"
        f"  • Check for naming conflicts\n"
        f"  • Import or merge Qube data\n\n"
        f"[bold]Conflict Resolution:[/bold]\n"
        f"  If a Qube with the same name exists:\n"
        f"    1. Skip import (keep existing)\n"
        f"    2. Merge memories (combine blocks)\n"
        f"    3. Replace completely\n\n"
        f"[dim]File:[/dim] [cyan]{file_path}[/cyan]\n"
        f"[dim]Size:[/dim] {import_file.stat().st_size / 1024:.1f} KB",
        title="Import Preview",
        border_style="cyan"
    ))
    console.print()


if __name__ == "__main__":
    app()
