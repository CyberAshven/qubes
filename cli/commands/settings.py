"""
Settings and configuration commands.

Commands:
- set-ai: Change AI model (interactive)
- set-voice: Change voice model (interactive)
- set-color: Change favorite color (interactive)
- set: Batch update settings (scriptable)
- set-global: Configure global CLI settings
"""

import asyncio
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from cli.utils.validators import resolve_qube, validate_hex_color, normalize_hex_color
from cli.utils.interactive import select_ai_model, select_voice_model, select_color, confirm_with_preview

console = Console()

# Settings app
app = typer.Typer(help="Qube settings and configuration")


@app.command("set-ai")
def set_ai_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    auto_yes: bool = typer.Option(False, "--auto-yes", "-y", help="Skip confirmation")
):
    """Change AI model (interactive menu)"""
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

    # Current model
    current_model = qube.genesis_block.ai_model
    console.print(f"\n[bold]Current AI Model:[/bold] [cyan]{current_model}[/cyan]")

    # Interactive selection
    new_model = select_ai_model(default=current_model)

    if new_model == current_model:
        console.print("[yellow]No change - model is the same.[/yellow]")
        return

    # Confirm
    if not auto_yes:
        preview = {
            "Qube": qube.name,
            "Current Model": current_model,
            "New Model": new_model
        }

        if not confirm_with_preview("Change AI model", preview, qube.genesis_block.favorite_color):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    # Update model
    try:
        qube.genesis_block.ai_model = new_model
        qube.save_genesis_block()

        console.print(f"\n[green]✓ AI model updated to[/green] [cyan]{new_model}[/cyan]")
    except Exception as e:
        console.print(f"[red]✗ Failed to update AI model:[/red] {e}")
        raise typer.Exit(1)


@app.command("set-voice")
def set_voice_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    auto_yes: bool = typer.Option(False, "--auto-yes", "-y", help="Skip confirmation")
):
    """Change voice model (interactive menu)"""
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

    # Current voice
    current_voice = getattr(qube.genesis_block, "voice_model")
    if current_voice:
        console.print(f"\n[bold]Current Voice Model:[/bold] [cyan]{current_voice}[/cyan]")
    else:
        console.print("\n[bold]Voice is currently disabled[/bold]")

    # Interactive selection
    new_voice = select_voice_model(default=current_voice)

    if new_voice == current_voice:
        console.print("[yellow]No change - voice model is the same.[/yellow]")
        return

    # Confirm
    if not auto_yes:
        preview = {
            "Qube": qube.name,
            "Current Voice": current_voice or "None",
            "New Voice": new_voice or "None (disabled)"
        }

        if not confirm_with_preview("Change voice model", preview, qube.genesis_block.favorite_color):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    # Update voice
    try:
        qube.genesis_block.voice_model = new_voice
        qube.save_genesis_block()

        if new_voice:
            console.print(f"\n[green]✓ Voice model updated to[/green] [cyan]{new_voice}[/cyan]")
        else:
            console.print("\n[green]✓ Voice disabled[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to update voice model:[/red] {e}")
        raise typer.Exit(1)


@app.command("set-color")
def set_color_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    auto_yes: bool = typer.Option(False, "--auto-yes", "-y", help="Skip confirmation")
):
    """Change favorite color (interactive picker)"""
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

    # Current color
    current_color = getattr(qube.genesis_block, "favorite_color", "#4A90E2")

    # Interactive selection
    new_color = select_color(default=current_color)

    if new_color == current_color:
        console.print("[yellow]No change - color is the same.[/yellow]")
        return

    # Confirm
    if not auto_yes:
        preview = {
            "Qube": qube.name,
            "Current Color": f"[{current_color}]████[/{current_color}] {current_color}",
            "New Color": f"[{new_color}]████[/{new_color}] {new_color}"
        }

        if not confirm_with_preview("Change favorite color", preview, new_color):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    # Update color
    try:
        qube.genesis_block.favorite_color = new_color
        qube.save_genesis_block()

        console.print(f"\n[green]✓ Favorite color updated to[/green] [{new_color}]████[/{new_color}] {new_color}")
    except Exception as e:
        console.print(f"[red]✗ Failed to update favorite color:[/red] {e}")
        raise typer.Exit(1)


@app.command("set")
def set_batch_command(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    ai: Optional[str] = typer.Option(None, "--ai", help="AI model"),
    voice: Optional[str] = typer.Option(None, "--voice", help="Voice model"),
    color: Optional[str] = typer.Option(None, "--color", help="Favorite color (hex)"),
    auto_yes: bool = typer.Option(False, "--auto-yes", "-y", help="Skip confirmation"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
    json_output: bool = typer.Option(False, "--json", help="JSON output")
):
    """Batch update settings (scriptable)"""
    from cli.main import get_orchestrator

    orchestrator = get_orchestrator()

    # Validate at least one setting provided
    if not any([ai, voice, color]):
        console.print("[red]✗ Error:[/red] At least one setting must be provided (--ai, --voice, --color)")
        raise typer.Exit(1)

    # Resolve Qube
    try:
        all_qubes = asyncio.run(orchestrator.list_qubes())
        qube_info = resolve_qube(name_or_id, orchestrator, all_qubes)
    except ValueError as e:
        if json_output:
            print(json.dumps({"success": False, "error": str(e)}))
        else:
            console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)

    # Load Qube
    qube = asyncio.run(orchestrator.load_qube(qube_info["qube_id"]))

    # Validate color if provided
    if color:
        if not validate_hex_color(color):
            error_msg = f"Invalid hex color format: {color}"
            if json_output:
                print(json.dumps({"success": False, "error": error_msg}))
            else:
                console.print(f"[red]✗ Error:[/red] {error_msg}")
            raise typer.Exit(1)
        color = normalize_hex_color(color)

    # Prepare updates
    updates = {}
    if ai:
        updates["ai_model"] = ai
    if voice:
        updates["voice_model"] = voice
    if color:
        updates["favorite_color"] = color

    # Confirm
    if not auto_yes and not quiet:
        console.print(f"\n[bold]Updating settings for {qube.name}:[/bold]")
        for key, value in updates.items():
            console.print(f"  • {key}: [cyan]{value}[/cyan]")
        console.print()

        if not Confirm.ask("Apply changes?", default=True):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    # Apply updates
    try:
        for key, value in updates.items():
            setattr(qube.genesis_block, key, value)

        qube.save_genesis_block()

        # Output
        if json_output:
            print(json.dumps({
                "success": True,
                "qube_id": qube.qube_id,
                "updates": updates
            }))
        elif not quiet:
            console.print(f"\n[green]✓ Updated {len(updates)} setting(s) for {qube.name}[/green]")

    except Exception as e:
        if json_output:
            print(json.dumps({"success": False, "error": str(e)}))
        else:
            console.print(f"[red]✗ Failed to update settings:[/red] {e}")
        raise typer.Exit(1)


@app.command("set-global")
def set_global_command(
    default_ai: Optional[str] = typer.Option(None, "--default-ai", help="Default AI model for new Qubes"),
    default_voice: Optional[str] = typer.Option(None, "--default-voice", help="Default voice model"),
    default_color: Optional[str] = typer.Option(None, "--default-color", help="Default favorite color"),
    timezone: Optional[str] = typer.Option(None, "--timezone", help="Display timezone (e.g., US/Eastern)"),
    theme: Optional[str] = typer.Option(None, "--theme", help="CLI theme: dark, light, auto"),
    autocomplete: Optional[bool] = typer.Option(None, "--autocomplete/--no-autocomplete", help="Enable autocomplete")
):
    """Configure global CLI settings"""

    # Validate at least one setting provided
    if not any([default_ai, default_voice, default_color, timezone, theme, autocomplete is not None]):
        console.print("[red]✗ Error:[/red] At least one setting must be provided")
        raise typer.Exit(1)

    # Load or create global config
    config_dir = Path("data/config")
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "cli_config.json"

    if config_file.exists():
        with open(config_file, "r") as f:
            config = json.load(f)
    else:
        config = {}

    # Update settings
    if default_ai:
        config["default_ai_model"] = default_ai
    if default_voice:
        config["default_voice_model"] = default_voice
    if default_color:
        if not validate_hex_color(default_color):
            console.print(f"[red]✗ Invalid hex color format:[/red] {default_color}")
            raise typer.Exit(1)
        config["default_favorite_color"] = normalize_hex_color(default_color)
    if timezone:
        config["timezone"] = timezone
    if theme:
        if theme not in ["dark", "light", "auto"]:
            console.print(f"[red]✗ Invalid theme:[/red] {theme}. Must be: dark, light, or auto")
            raise typer.Exit(1)
        config["theme"] = theme
    if autocomplete is not None:
        config["autocomplete"] = autocomplete

    # Save config
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    console.print("\n[green]✓ Global settings updated:[/green]")
    for key, value in config.items():
        console.print(f"  • {key}: [cyan]{value}[/cyan]")
    console.print()


if __name__ == "__main__":
    app()
