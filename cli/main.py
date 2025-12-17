"""
Qubes CLI Application

Command-line interface for managing Qubes.
From docs/11_Orchestrator_User_Interface.md Section 8.2
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from orchestrator import UserOrchestrator
from utils.logging import get_logger

logger = get_logger(__name__)

# CLI app
app = typer.Typer(
    name="qubes",
    help="Qubes - Sovereign Multi-Agent AI Platform",
    add_completion=False
)

# Add command subgroups
from cli.commands import settings, memory, help_system, monitoring, relationships, network, blockchain, export_import
app.add_typer(settings.app, name="settings", help="Qube settings and configuration")
app.add_typer(memory.app, name="mem", help="Memory management and inspection")
app.add_typer(help_system.app, name="help", help="Help and documentation")
app.add_typer(monitoring.app, name="monitor", help="Monitoring and diagnostics")
app.add_typer(relationships.app, name="social", help="Relationships and social dynamics")
app.add_typer(network.app, name="network", help="Network and P2P operations")
app.add_typer(blockchain.app, name="blockchain", help="Blockchain and NFT operations")
app.add_typer(export_import.app, name="data", help="Export and import Qubes")

# Rich console
console = Console()

# Global orchestrator instance
_orchestrator: Optional[UserOrchestrator] = None


def get_orchestrator() -> UserOrchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator

    if _orchestrator is None:
        # Load or create user ID
        config_dir = Path("data/config")
        config_dir.mkdir(parents=True, exist_ok=True)

        user_config = config_dir / "user.json"

        if user_config.exists():
            import json
            with open(user_config, "r") as f:
                data = json.load(f)
                user_id = data["user_id"]
        else:
            # First-time setup
            console.print(Panel(
                "[bold cyan]Welcome to Qubes![/bold cyan]\n\n"
                "First-time setup required.",
                title="✨ Qubes Setup",
                border_style="cyan"
            ))

            user_id = Prompt.ask("Enter your user ID", default="user1")

            import json
            with open(user_config, "w") as f:
                json.dump({"user_id": user_id}, f, indent=2)

            console.print(f"[green]✓[/green] User ID set to: [cyan]{user_id}[/cyan]\n")

        # Create orchestrator
        _orchestrator = UserOrchestrator(user_id=user_id)

        # Set master key from password
        password = Prompt.ask(
            "Enter master password (for encrypting private keys)",
            password=True
        )
        _orchestrator.set_master_key(password)

        console.print("[green]✓[/green] Orchestrator initialized\n")

    return _orchestrator


@app.command()
def create(
    name: Optional[str] = typer.Option(None, "--name", help="Qube name"),
    genesis: Optional[str] = typer.Option(None, "--genesis", help="Genesis prompt"),
    ai: Optional[str] = typer.Option(None, "--ai", help="AI model"),
    voice: Optional[str] = typer.Option(None, "--voice", help="Voice model"),
    color: Optional[str] = typer.Option(None, "--color", help="Favorite color (hex)"),
    blockchain: Optional[str] = typer.Option(None, "--blockchain", help="Home blockchain"),
    wallet: Optional[str] = typer.Option(None, "--wallet", help="BCH wallet address (REQUIRED for NFT)"),
    auto_yes: bool = typer.Option(False, "--auto-yes", "-y", help="Skip confirmations")
):
    """Create a new Qube with blockchain identity (NFT required)"""
    from cli.utils.interactive import select_ai_model, select_voice_model, select_color, confirm_with_preview
    from cli.utils.validators import validate_hex_color, normalize_hex_color

    # Check if scriptable mode (all required params provided, including wallet)
    scriptable = all([name, genesis, ai, wallet])

    if not scriptable:
        # Interactive mode
        console.print(Panel(
            "[bold cyan]Create New Qube[/bold cyan]\n"
            "Interactive wizard - follow the prompts to create your Qube",
            border_style="cyan"
        ))

        # Qube name
        if not name:
            name = Prompt.ask("\n[bold]Qube name[/bold]")

        # Genesis prompt
        if not genesis:
            console.print("\n[bold]Genesis prompt[/bold] (who is this Qube?)")
            genesis = Prompt.ask("Prompt")

        # AI Model selection
        if not ai:
            ai = select_ai_model()

        # Voice selection
        if voice is None:
            voice = select_voice_model()

        # Favorite color
        if not color:
            color = select_color()
        else:
            if not validate_hex_color(color):
                console.print(f"[red]✗ Invalid hex color:[/red] {color}")
                raise typer.Exit(1)
            color = normalize_hex_color(color)

        # Creator name
        creator = Prompt.ask("\n[bold]Your name[/bold] (creator)", default="User")

        # Home blockchain
        if not blockchain:
            blockchains = ["bitcoincash", "bitcoin", "ethereum"]
            console.print("\n[bold]Home Blockchain[/bold]")
            for i, bc in enumerate(blockchains, 1):
                console.print(f"  {i}. [cyan]{bc}[/cyan]")

            bc_choice = Prompt.ask(
                "Selection",
                choices=[str(i) for i in range(1, len(blockchains) + 1)],
                default="1"
            )
            blockchain = blockchains[int(bc_choice) - 1]

        # Capabilities
        console.print("\n[bold]Capabilities[/bold] (enable features)")
        web_search = Confirm.ask("  Web search?", default=True)
        image_generation = Confirm.ask("  Image generation?", default=True)
        code_execution = Confirm.ask("  Code execution?", default=False)

        # Trust level
        default_trust_level = int(Prompt.ask(
            "\n[bold]Default trust level[/bold] (0-100)",
            default="50"
        ))

        # Genesis prompt encryption
        encrypt_genesis = Confirm.ask("\n[bold]Encrypt genesis prompt?[/bold]", default=False)

        # Wallet address (REQUIRED - every qube needs blockchain identity)
        console.print(f"\n[bold cyan]🔗 Blockchain Identity (Required)[/bold cyan]")
        console.print(f"Every Qube needs a {blockchain.title()} NFT for on-chain identity")

        wallet_address = Prompt.ask(
            f"\n[bold]{blockchain.title()} wallet address[/bold] (CashToken-compatible)"
        )

        if not wallet_address:
            console.print("[red]✗ Wallet address is required for NFT minting[/red]")
            console.print("[yellow]Hint:[/yellow] Get a wallet at https://www.paytaca.com or https://cashonize.com")
            raise typer.Exit(1)

    else:
        # Scriptable mode - use defaults for optional params
        if color:
            if not validate_hex_color(color):
                console.print(f"[red]✗ Invalid hex color:[/red] {color}")
                raise typer.Exit(1)
            color = normalize_hex_color(color)
        else:
            color = "#4A90E2"

        creator = "User"
        blockchain = blockchain or "bitcoincash"
        web_search = True
        image_generation = True
        code_execution = False
        default_trust_level = 50
        encrypt_genesis = False
        wallet_address = wallet  # Use wallet parameter (required in scriptable mode)

    # Build config
    config = {
        "name": name,
        "creator": creator,
        "genesis_prompt": genesis,
        "ai_model": ai,
        "voice_model": voice,
        "favorite_color": color,
        "home_blockchain": blockchain,
        "capabilities": {
            "web_search": web_search,
            "image_generation": image_generation,
            "tts": bool(voice),
            "stt": bool(voice),
            "code_execution": code_execution
        },
        "default_trust_level": default_trust_level,
        "encrypt_genesis": encrypt_genesis,
        "wallet_address": wallet_address
    }

    # Preview and confirm (unless auto-yes)
    if not auto_yes:
        preview = {
            "Name": name,
            "AI Model": ai,
            "Voice": voice or "Disabled",
            "Color": f"[{color}]████[/{color}] {color}",
            "Blockchain": blockchain
        }

        if not confirm_with_preview("Create Qube", preview, color):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    # Initialize orchestrator
    orchestrator = get_orchestrator()

    # Create Qube
    console.print("\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Creating Qube...", total=None)

        try:
            qube = asyncio.run(orchestrator.create_qube(config))

            progress.update(task, completed=True)

            # Format birth date
            from utils.time_format import format_timestamp
            birth_date = format_timestamp(qube.genesis_block.birth_timestamp)

            console.print(f"\n[bold green]✓ Qube created successfully![/bold green]\n")
            console.print(f"[bold]Qube ID:[/bold] [cyan]{qube.qube_id}[/cyan]")
            console.print(f"[bold]Name:[/bold] [cyan]{name}[/cyan]")
            console.print(f"[bold]Birth Date:[/bold] {birth_date}")
            console.print(f"[bold]AI Model:[/bold] [cyan]{ai}[/cyan]")
            console.print(f"[bold]Favorite Color:[/bold] [{color}]●[/{color}] {color}")

            if wallet_address:
                nft_category = getattr(qube.genesis_block, 'nft_category_id', 'N/A')
                console.print(f"[bold]NFT Category:[/bold] [cyan]{nft_category}[/cyan]")

            console.print(f"\n[dim]Start chatting:[/dim] [cyan]qubes chat {name}[/cyan]\n")

        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"\n[bold red]✗ Failed to create Qube:[/bold red] {str(e)}")
            logger.error("create_command_failed", error=str(e), exc_info=True)
            raise typer.Exit(code=1)


@app.command()
def list():
    """List all Qubes"""
    orchestrator = get_orchestrator()

    console.print("\n")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Loading Qubes...", total=None)

        qubes = asyncio.run(orchestrator.list_qubes())

        progress.update(task, completed=True)

    if not qubes:
        console.print("\n[yellow]No Qubes found. Create one with:[/yellow] [cyan]qubes create[/cyan]\n")
        return

    table = Table(title="\n✨ Your Qubes", border_style="cyan")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta bold")
    table.add_column("AI Model", style="green")
    table.add_column("Birth Date", style="yellow")
    table.add_column("Status", style="blue")

    for qube_info in qubes:
        from utils.time_format import format_timestamp_short
        birth_date = format_timestamp_short(qube_info["birth_timestamp"])

        status = "[green]●[/green] Loaded" if qube_info["loaded"] else "[dim]○[/dim] Not loaded"

        table.add_row(
            qube_info["qube_id"][:16] + "...",
            qube_info["name"],
            qube_info["ai_model"],
            birth_date,
            status
        )

    console.print(table)
    console.print()


async def play_voice_response(text: str, voice_model: str):
    """
    Play TTS audio for the given text using the specified voice model.

    Args:
        text: Text to synthesize
        voice_model: Voice model string (e.g., "openai:alloy", "elevenlabs:adam")
    """
    from audio.audio_manager import AudioManager
    from audio.tts_engine import VoiceConfig

    # Parse voice model
    if ":" in voice_model:
        provider, voice = voice_model.split(":", 1)
    else:
        provider = "openai"
        voice = voice_model

    # Create voice config
    voice_config = VoiceConfig(
        provider=provider,
        voice_id=voice,
        speed=1.0
    )

    # Initialize audio manager and speak
    audio_manager = AudioManager()
    await audio_manager.speak(
        text=text,
        voice_config=voice_config,
        user_id="cli_user",
        use_cache=True
    )


@app.command()
def chat(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Single message (scriptable)"),
    voice: bool = typer.Option(False, "--voice", help="Enable voice from start"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
    json_output: bool = typer.Option(False, "--json", help="JSON output")
):
    """Chat with a Qube (interactive or scriptable)"""
    from cli.utils.validators import resolve_qube
    import json

    orchestrator = get_orchestrator()

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
    if not quiet:
        console.print(f"\n[cyan]Loading {qube_info['name']}...[/cyan]")

    qube = asyncio.run(orchestrator.load_qube(qube_info["qube_id"]))

    # Get favorite color from genesis block
    favorite_color = getattr(qube.genesis_block, "favorite_color", "#4A90E2")

    # Scriptable mode (single message)
    if message:
        async def send_single_message():
            response = await qube.process_message(message, sender_id="human")
            return response

        try:
            response = asyncio.run(send_single_message())

            if json_output:
                print(json.dumps({"response": response, "qube": qube.name}))
            elif not quiet:
                console.print(f"[bold {favorite_color}]{qube.name}:[/bold {favorite_color}] {response}")
        except Exception as e:
            if json_output:
                print(json.dumps({"success": False, "error": str(e)}))
            else:
                console.print(f"[red]✗ Error:[/red] {e}")
            raise typer.Exit(1)
        return

    # Interactive chat mode
    # Enable voice by default if Qube has voice_model configured
    has_voice_model = getattr(qube.genesis_block, 'voice_model', None) is not None
    voice_enabled = voice or (has_voice_model and not quiet)

    voice_status = "🔊 ON" if voice_enabled else "🔇 OFF"
    voice_model_text = getattr(qube.genesis_block, 'voice_model', 'Not set')

    # Check for existing session blocks from previous session
    from pathlib import Path
    session_dir = Path(qube.data_dir) / "blocks" / "session"
    existing_sessions = [p for p in session_dir.glob("*")] if session_dir.exists() else []

    if existing_sessions:
        # Found unanchored session(s)
        for old_session_dir in existing_sessions:
            session_blocks = [p for p in old_session_dir.glob("*.json")]
            if session_blocks:
                console.print(Panel(
                    f"[yellow]⚠️  Found {len(session_blocks)} unanchored blocks from previous session[/yellow]\n\n"
                    f"Session ID: [dim]{old_session_dir.name}[/dim]\n"
                    f"These blocks are temporary and will be lost if not anchored.\n\n"
                    f"[bold]What would you like to do?[/bold]\n"
                    f"  [green](A)nchor[/green] - Save to permanent memory\n"
                    f"  [red](D)iscard[/red] - Delete and start fresh\n"
                    f"  [cyan](V)iew[/cyan] - Show block details first",
                    title="⚠️  Previous Session Found",
                    border_style="yellow"
                ))

                choice = Prompt.ask("Choice", choices=["a", "A", "d", "D", "v", "V"], default="a").lower()

                if choice == "a":
                    # Recover and anchor the old session
                    console.print(f"\n[cyan]Recovering previous session...[/cyan]")
                    from core.session import Session
                    recovered_session = Session.recover_session(qube, old_session_dir.name)

                    if recovered_session:
                        qube.current_session = recovered_session
                        converted_blocks = asyncio.run(qube.current_session.anchor_to_chain(create_summary=True))
                        console.print(f"[green]✓ Anchored {len(converted_blocks)} blocks from previous session[/green]")

                        if converted_blocks:
                            first_block = converted_blocks[0].block_number
                            last_block = converted_blocks[-1].block_number
                            console.print(f"[dim]  Block range: {first_block} - {last_block}[/dim]\n")
                    else:
                        console.print(f"[red]✗ Failed to recover session[/red]\n")

                elif choice == "d":
                    # Discard the old session
                    import shutil
                    shutil.rmtree(old_session_dir)
                    console.print(f"[yellow]Discarded {len(session_blocks)} session blocks[/yellow]\n")

                elif choice == "v":
                    # View blocks
                    console.print(f"\n[bold]Session Blocks:[/bold]")
                    for block_file in sorted(session_blocks, key=lambda x: int(x.stem.split('_')[0])):
                        import json
                        with open(block_file) as f:
                            block_data = json.load(f)
                        block_type = block_data.get("block_type", "UNKNOWN")
                        console.print(f"  [{favorite_color}]{block_file.stem}[/{favorite_color}] - {block_type}")

                    console.print()
                    if Confirm.ask("Anchor these blocks?", default=True):
                        from core.session import Session
                        recovered_session = Session.recover_session(qube, old_session_dir.name)
                        if recovered_session:
                            qube.current_session = recovered_session
                            converted_blocks = asyncio.run(qube.current_session.anchor_to_chain(create_summary=True))
                            console.print(f"[green]✓ Anchored {len(converted_blocks)} blocks[/green]\n")
                    else:
                        import shutil
                        shutil.rmtree(old_session_dir)
                        console.print(f"[yellow]Discarded session blocks[/yellow]\n")

    console.print(Panel(
        f"[bold {favorite_color}]Chatting with {qube.name}[/bold {favorite_color}]\n"
        f"Qube ID: [dim]{qube_info['qube_id'][:16]}...[/dim]\n"
        f"AI Model: [green]{qube.genesis_block.ai_model}[/green]\n"
        f"Voice: [cyan]{voice_model_text}[/cyan] {voice_status}\n"
        f"Favorite Color: [{favorite_color}]●[/{favorite_color}] {favorite_color}\n\n"
        f"Type [bold]/help[/bold] for commands, [bold]/quit[/bold] to exit.",
        title="💬 Chat Session",
        border_style=favorite_color
    ))

    # Chat loop with mid-chat commands
    async def chat_loop():
        nonlocal voice_enabled

        while True:
            user_input = Prompt.ask(f"\n[bold green]You[/bold green]")

            # Handle mid-chat commands
            if user_input.startswith("/"):
                command = user_input.lower().strip()

                if command in ["/quit", "/exit"]:
                    console.print(f"\n[{favorite_color}]Goodbye![/{favorite_color}]\n")
                    break

                elif command == "/help":
                    console.print("\n[bold]Mid-Chat Commands:[/bold]")
                    console.print("  [cyan]/help[/cyan] - Show this help")
                    console.print("  [cyan]/quit, /exit[/cyan] - End conversation")
                    console.print("  [cyan]/voice on|off[/cyan] - Toggle voice")
                    console.print("  [cyan]/stats[/cyan] - Show conversation stats")
                    console.print("  [cyan]/anchor[/cyan] - Anchor session to permanent memory")
                    console.print("  [cyan]/clear[/cyan] - Clear screen")
                    continue

                elif command in ["/voice on", "/voice off"]:
                    if command == "/voice on":
                        voice_enabled = True
                        console.print("[green]✓ Voice enabled[/green]")
                    else:
                        voice_enabled = False
                        console.print("[yellow]Voice disabled[/yellow]")
                    continue

                elif command == "/stats":
                    # Show session stats
                    if qube.current_session:
                        session_blocks = len(qube.current_session.session_blocks)
                        console.print(f"\n[bold]Session Stats:[/bold]")
                        console.print(f"  Session ID: [dim]{qube.current_session.session_id}[/dim]")
                        console.print(f"  Session Blocks: [cyan]{session_blocks}[/cyan]")
                        console.print(f"  Permanent Blocks: [green]{qube.memory_chain.get_chain_length()}[/green]")
                    else:
                        console.print("[yellow]No active session[/yellow]")
                    continue

                elif command == "/anchor":
                    # Anchor session blocks to permanent storage
                    if not qube.current_session:
                        console.print("[yellow]No active session to anchor[/yellow]")
                        continue

                    session_block_count = len(qube.current_session.session_blocks)
                    if session_block_count == 0:
                        console.print("[yellow]No session blocks to anchor[/yellow]")
                        continue

                    console.print(f"\n[bold]Anchor {session_block_count} blocks to permanent memory?[/bold]")
                    console.print(f"  [dim]This will encrypt and save all session blocks permanently[/dim]")

                    if Confirm.ask("  Continue?", default=True):
                        try:
                            converted_blocks = asyncio.run(qube.current_session.anchor_to_chain(create_summary=True))
                            console.print(f"\n[green]✓ Successfully anchored {len(converted_blocks)} blocks[/green]")

                            if converted_blocks:
                                first_block = converted_blocks[0].block_number
                                last_block = converted_blocks[-1].block_number
                                console.print(f"[dim]  Block range: {first_block} - {last_block}[/dim]")

                                if len(converted_blocks) > session_block_count:
                                    console.print(f"[dim]  Summary block created: {last_block}[/dim]")

                            chain_length = qube.memory_chain.get_chain_length()
                            console.print(f"[dim]  New chain length: {chain_length}[/dim]")
                            console.print(f"\n[green]Session cleared. Ready for new conversation.[/green]")

                        except Exception as e:
                            console.print(f"\n[red]✗ Anchoring failed:[/red] {str(e)}")
                            logger.error("anchor_failed", error=str(e), exc_info=True)
                    else:
                        console.print("[yellow]Anchoring cancelled[/yellow]")
                    continue

                elif command == "/clear":
                    console.clear()
                    console.print(f"[{favorite_color}]Chat with {qube.name} continues...[/{favorite_color}]\n")
                    continue

                else:
                    console.print(f"[red]Unknown command:[/red] {command}")
                    console.print("Type [cyan]/help[/cyan] for available commands")
                    continue

            # Process regular message
            console.print()
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"[{favorite_color}]{qube.name} is thinking...", total=None)

                try:
                    response = await qube.process_message(user_input, sender_id="human")

                    progress.update(task, completed=True)

                    # Display response in Qube's favorite color
                    console.print(f"\n[bold {favorite_color}]{qube.name}[/bold {favorite_color}]: [{favorite_color}]{response}[/{favorite_color}]\n")

                    # Voice synthesis if enabled
                    if voice_enabled and getattr(qube.genesis_block, "voice_model"):
                        try:
                            await play_voice_response(response, qube.genesis_block.voice_model)
                        except Exception as voice_error:
                            logger.warning("voice_synthesis_failed", error=str(voice_error))
                            console.print(f"[dim yellow]⚠ Voice synthesis unavailable[/dim yellow]")

                except Exception as e:
                    progress.update(task, completed=True)
                    console.print(f"\n[red]✗ Error:[/red] {str(e)}\n")
                    logger.error("chat_message_failed", error=str(e), exc_info=True)

    # Run the chat loop with a single event loop
    asyncio.run(chat_loop())


@app.command()
def info(name_or_id: str = typer.Argument(..., help="Qube name or ID")):
    """Show detailed info about a Qube"""
    from cli.utils.validators import resolve_qube

    orchestrator = get_orchestrator()

    # Resolve Qube
    try:
        all_qubes = asyncio.run(orchestrator.list_qubes())
        qube_info = resolve_qube(name_or_id, orchestrator, all_qubes)
    except ValueError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)

    # Load Qube
    console.print(f"\n[cyan]Loading {qube_info['name']}...[/cyan]\n")
    qube = asyncio.run(orchestrator.load_qube(qube_info["qube_id"]))

    # Display info
    from utils.time_format import format_timestamp
    birth_date = format_timestamp(getattr(qube.genesis_block, "birth_timestamp"))

    # Get favorite color for styling
    favorite_color = getattr(qube.genesis_block, "favorite_color", "#4A90E2")

    # Truncate NFT info safely
    nft_category = getattr(qube.genesis_block, 'nft_category_id', 'Not minted')
    nft_category_display = nft_category[:16] + "..." if len(nft_category) > 16 else nft_category

    mint_tx = getattr(qube.genesis_block, 'mint_txid', 'N/A')
    mint_tx_display = mint_tx[:16] + "..." if len(mint_tx) > 16 else mint_tx

    info_text = f"""
[bold]Name:[/bold] {qube.name}
[bold]Qube ID:[/bold] {qube.qube_id}
[bold]Birth Date:[/bold] {birth_date}
[bold]Creator:[/bold] {getattr(qube.genesis_block, 'creator', 'Unknown')}

[bold {favorite_color}]Personality[/bold {favorite_color}]
[bold]Favorite Color:[/bold] [{favorite_color}]●[/{favorite_color}] {favorite_color}
[bold]Home Blockchain:[/bold] {getattr(qube.genesis_block, 'home_blockchain', 'bitcoincash')}
[bold]Trust Level:[/bold] {getattr(qube.genesis_block, 'default_trust_level', 50)}/100

[bold cyan]AI Configuration[/bold cyan]
[bold]AI Model:[/bold] {qube.genesis_block.ai_model}
[bold]Voice Model:[/bold] {getattr(qube.genesis_block, 'voice_model', 'Not set')}

[bold cyan]Blockchain[/bold cyan]
[bold]NFT Category:[/bold] {nft_category_display}
[bold]Mint TX:[/bold] {mint_tx_display}

[bold cyan]Memory Chain[/bold cyan]
[bold]Total Blocks:[/bold] {len(qube.memory_chain.blocks) if hasattr(qube.memory_chain, 'blocks') else 'Unknown'}
[bold]Genesis Prompt Encrypted:[/bold] {getattr(qube.genesis_block, 'genesis_prompt_encrypted', False)}

[bold cyan]Capabilities[/bold cyan]
"""

    capabilities = getattr(qube.genesis_block, 'capabilities', {})
    for cap, enabled in capabilities.items():
        status = "[green]✓[/green]" if enabled else "[dim]✗[/dim]"
        info_text += f"{status} {cap.replace('_', ' ').title()}\n"

    console.print(Panel(
        info_text.strip(),
        title=f"📋 {qube.name}",
        border_style=favorite_color
    ))
    console.print()


@app.command()
def edit(name_or_id: str = typer.Argument(..., help="Qube name or ID")):
    """Edit mutable Qube fields (interactive menu)"""
    from cli.utils.validators import resolve_qube
    from cli.utils.interactive import select_ai_model, select_voice_model, select_color

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
        f"[bold]Editing {qube.name}[/bold]\n"
        f"[dim]Note: Name and genesis prompt are immutable[/dim]",
        border_style=favorite_color
    ))

    # Interactive menu
    while True:
        console.print("\n[bold]What would you like to edit?[/bold]")
        console.print(f"  1. AI Model (current: [cyan]{qube.genesis_block.ai_model}[/cyan])")
        console.print(f"  2. Voice Model (current: [cyan]{getattr(qube.genesis_block, 'voice_model', 'Not set')}[/cyan])")
        console.print(f"  3. Favorite Color (current: [{favorite_color}]●[/{favorite_color}] {favorite_color})")
        console.print("  4. Done")

        choice = Prompt.ask("Selection", choices=["1", "2", "3", "4"], default="4")

        if choice == "1":
            new_ai = select_ai_model(default=qube.genesis_block.ai_model)
            qube.genesis_block.ai_model = new_ai
            qube.save_genesis_block()
            console.print(f"[green]✓ AI model updated to[/green] [cyan]{new_ai}[/cyan]")

        elif choice == "2":
            new_voice = select_voice_model(default=getattr(qube.genesis_block, "voice_model"))
            qube.genesis_block.voice_model = new_voice
            qube.save_genesis_block()
            if new_voice:
                console.print(f"[green]✓ Voice model updated to[/green] [cyan]{new_voice}[/cyan]")
            else:
                console.print("[green]✓ Voice disabled[/green]")

        elif choice == "3":
            new_color = select_color(default=favorite_color)
            qube.genesis_block.favorite_color = new_color
            qube.save_genesis_block()
            favorite_color = new_color
            console.print(f"[green]✓ Favorite color updated to[/green] [{new_color}]●[/{new_color}] {new_color}")

        elif choice == "4":
            console.print("\n[green]✓ Edits complete[/green]\n")
            break


@app.command()
def delete(
    name_or_id: str = typer.Argument(..., help="Qube name or ID"),
    auto_yes: bool = typer.Option(False, "--auto-yes", "-y", help="Skip confirmation")
):
    """Delete a Qube (with confirmation)"""
    from cli.utils.validators import resolve_qube, confirm_destructive_action

    orchestrator = get_orchestrator()

    # Resolve Qube
    try:
        all_qubes = asyncio.run(orchestrator.list_qubes())
        qube_info = resolve_qube(name_or_id, orchestrator, all_qubes)
    except ValueError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)

    # Load Qube to get details
    qube = asyncio.run(orchestrator.load_qube(qube_info["qube_id"]))

    # Count blocks
    try:
        all_blocks = qube.memory_chain.get_all_blocks() if hasattr(qube.memory_chain, 'get_all_blocks') else []
    except:
        all_blocks = qube.memory_chain.blocks if hasattr(qube.memory_chain, 'blocks') else []

    block_count = len(all_blocks)

    # Confirm deletion
    details = [
        f"All memory blocks ({block_count} blocks)",
        "Genesis block and identity",
        "NFT metadata (blockchain record remains)",
        "All relationships and shared memory"
    ]

    if not confirm_destructive_action(
        "Delete",
        f"Qube '{qube.name}' ({qube_info['qube_id'][:16]}...)",
        details,
        auto_yes
    ):
        console.print("[yellow]Deletion cancelled.[/yellow]")
        return

    # Delete Qube
    try:
        asyncio.run(orchestrator.delete_qube(qube_info["qube_id"]))
        console.print(f"\n[green]✓ Qube '{qube.name}' deleted successfully[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Failed to delete Qube:[/red] {e}")
        logger.error("delete_qube_failed", error=str(e), exc_info=True)
        raise typer.Exit(1)


@app.command()
def version():
    """Show Qubes version information"""
    console.print(Panel(
        "[bold cyan]Qubes - Sovereign Multi-Agent AI Platform[/bold cyan]\n\n"
        "[bold]Version:[/bold] 1.0.0-alpha\n"
        "[bold]Phase:[/bold] 8 (CLI Foundation)\n"
        "[bold]Status:[/bold] [green]Development[/green]\n\n"
        "[dim]Built with Bitcoin Cash, libp2p, and Claude[/dim]",
        title="✨ Qubes",
        border_style="cyan"
    ))


if __name__ == "__main__":
    app()
