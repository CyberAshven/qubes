"""
Comprehensive help system with examples and workflows.

Provides:
- Command overview
- Detailed command help
- Example workflows
- Keyboard shortcuts
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

console = Console()

# Help app
app = typer.Typer(help="Help and documentation")


@app.command("commands")
def commands_help():
    """Show overview of all commands"""

    console.print(Panel(
        "[bold cyan]Qubes CLI - Command Reference[/bold cyan]\n"
        "Complete list of available commands organized by category",
        border_style="cyan"
    ))

    # Core Management
    table = Table(title="\n📦 Core Management", border_style="cyan", show_header=True)
    table.add_column("Command", style="cyan", width=20)
    table.add_column("Description", style="white")

    table.add_row("create", "Create a new Qube (interactive wizard or scriptable)")
    table.add_row("list", "List all Qubes with metadata")
    table.add_row("info <qube>", "Show detailed information about a Qube")
    table.add_row("edit <qube>", "Edit mutable Qube fields (interactive menu)")
    table.add_row("delete <qube>", "Delete a Qube with confirmation")

    console.print(table)

    # Chat & Interaction
    table = Table(title="\n💬 Chat & Interaction", border_style="green", show_header=True)
    table.add_column("Command", style="cyan", width=20)
    table.add_column("Description", style="white")

    table.add_row("chat <qube>", "Interactive chat with a Qube")
    table.add_row("chat <qube> -m 'msg'", "Send single message (scriptable)")

    console.print(table)

    # Settings
    table = Table(title="\n⚙️  Settings & Configuration", border_style="yellow", show_header=True)
    table.add_column("Command", style="cyan", width=25)
    table.add_column("Description", style="white")

    table.add_row("settings set-ai <qube>", "Change AI model (interactive)")
    table.add_row("settings set-voice <qube>", "Change voice model (interactive)")
    table.add_row("settings set-color <qube>", "Change favorite color (interactive)")
    table.add_row("settings set <qube> --ai X", "Batch update settings (scriptable)")
    table.add_row("settings set-global", "Configure global CLI settings")

    console.print(table)

    # Memory Management
    table = Table(title="\n🧠 Memory Management", border_style="magenta", show_header=True)
    table.add_column("Command", style="cyan", width=30)
    table.add_column("Description", style="white")

    table.add_row("mem memories <qube>", "View recent memory blocks")
    table.add_row("mem memories <qube> --limit 50", "Show N recent blocks")
    table.add_row("mem memories <qube> --type MESSAGE", "Filter by block type")
    table.add_row("mem memories <qube> --blocks", "Show block distribution")
    table.add_row("mem memory <qube> <num>", "View specific block details")
    table.add_row("mem summary <qube>", "Generate AI-powered summary")
    table.add_row("mem stats <qube>", "Display memory statistics")

    console.print(table)

    # Other
    table = Table(title="\n🔧 Other Commands", border_style="blue", show_header=True)
    table.add_column("Command", style="cyan", width=20)
    table.add_column("Description", style="white")

    table.add_row("version", "Show Qubes version information")
    table.add_row("help commands", "Show this command reference")
    table.add_row("help examples", "Show example workflows")
    table.add_row("help <command>", "Show detailed help for a command")

    console.print(table)

    console.print("\n[dim]Tip: Use --help on any command for more details[/dim]")
    console.print("[dim]Example: qubes chat --help[/dim]\n")


@app.command("examples")
def examples_help():
    """Show example workflows and use cases"""

    console.print(Panel(
        "[bold cyan]Qubes CLI - Example Workflows[/bold cyan]\n"
        "Common usage patterns and scripting examples",
        border_style="cyan"
    ))

    examples = """
## 1. Getting Started - Create Your First Qube

### Interactive Mode (Recommended for beginners)
```bash
qubes create
# Follow the interactive wizard
```

### Scriptable Mode (For automation)
```bash
qubes create --name "AlphaBot" \\
             --genesis "You are a helpful coding assistant" \\
             --ai claude-sonnet-4.5 \\
             --voice openai:alloy \\
             --color "#41DAAA" \\
             --auto-yes
```

---

## 2. Basic Interaction - Chat with Your Qube

### Start Interactive Chat
```bash
qubes chat AlphaBot
# or use partial ID/name
qubes chat alph
```

### Mid-Chat Commands (while chatting)
```
/help        - Show available commands
/voice on    - Enable voice synthesis
/voice off   - Disable voice
/stats       - Show conversation stats
/anchor      - Anchor session to permanent memory
/clear       - Clear screen
/quit        - Exit chat
```

### Scriptable Single Message
```bash
qubes chat AlphaBot -m "What's 2+2?" --json --quiet
```

---

## 3. Viewing and Inspecting Memories

### List All Qubes
```bash
qubes list
```

### View Qube Information
```bash
qubes info AlphaBot
```

### Browse Recent Memories
```bash
# Last 20 blocks (default)
qubes mem memories AlphaBot

# Last 50 blocks
qubes mem memories AlphaBot --limit 50

# Filter by type
qubes mem memories AlphaBot --type MESSAGE

# Search content
qubes mem memories AlphaBot --search "python"

# Show block distribution
qubes mem memories AlphaBot --blocks
```

### Inspect Specific Block
```bash
# View block #45
qubes mem memory AlphaBot 45

# View latest block
qubes mem memory AlphaBot -1

# View 5th from last
qubes mem memory AlphaBot -5
```

### Generate Summary
```bash
qubes mem summary AlphaBot
qubes mem summary AlphaBot --blocks 200 --save
```

### View Statistics
```bash
qubes mem stats AlphaBot
qubes mem stats AlphaBot --json
```

---

## 4. Changing Settings

### Interactive Settings Change
```bash
# Change AI model (shows menu)
qubes settings set-ai AlphaBot

# Change voice model (shows menu)
qubes settings set-voice AlphaBot

# Change favorite color (shows color picker)
qubes settings set-color AlphaBot
```

### Batch Settings Update (Scriptable)
```bash
qubes settings set AlphaBot \\
    --ai gpt-5 \\
    --voice tts-1-hd \\
    --color "#FF5733" \\
    --auto-yes
```

### Edit Interactively (Alternative)
```bash
qubes edit AlphaBot
# Shows menu to edit AI model, voice, or color
```

---

## 5. Automation & Scripting

### Create Multiple Qubes
```bash
for name in Alpha Beta Gamma; do
    qubes create \\
        --name "${name}Bot" \\
        --genesis "You are ${name}, a helpful assistant" \\
        --ai claude-sonnet-4.5 \\
        --auto-yes
done
```

### Batch Update All Qubes
```bash
# Get all qube names and update their AI model
qubes list --json | jq -r '.[].name' | while read qube; do
    qubes settings set "$qube" --ai gpt-5 -y -q
done
```

### Automated Chat Sessions
```bash
# Send messages to multiple Qubes
for qube in AlphaBot BetaBot GammaBot; do
    response=$(qubes chat "$qube" -m "Hello!" --json -q)
    echo "$qube: $(echo $response | jq -r '.response')"
done
```

### Export Qube Stats
```bash
# Generate JSON reports for all Qubes
qubes list --json | jq -r '.[].name' | while read qube; do
    qubes mem stats "$qube" --json > "stats_${qube}.json"
done
```

---

## 6. Name/ID Matching Examples

### Exact Name Match
```bash
qubes chat AlphaBot
```

### Partial ID Match (min 4 characters)
```bash
qubes chat alph-d4e2
```

### Partial Name Match
```bash
qubes chat alph    # Matches "AlphaBot"
```

### Handling Ambiguous Matches
```bash
# If multiple qubes match, you'll see:
# 1. AlphaBot (alph-d4e2f1a8)
# 2. AlphaPrime (alph-a1b2c3d4)
# Selection:
```

---

## 7. Advanced Usage

### Global CLI Configuration
```bash
# Set defaults for new Qubes
qubes settings set-global \\
    --default-ai gpt-5 \\
    --default-voice tts-1-hd \\
    --default-color "#4A90E2" \\
    --timezone "US/Eastern"
```

### JSON Output for Parsing
```bash
# Get structured output
qubes list --json
qubes chat AlphaBot -m "test" --json
qubes mem stats AlphaBot --json
```

### Quiet Mode for Scripts
```bash
# Minimal output (errors only)
qubes settings set AlphaBot --ai gpt-5 -y -q
```

---

## 8. Deletion & Cleanup

### Delete Single Qube
```bash
qubes delete AlphaBot
# Shows confirmation with details
```

### Force Delete (Skip Confirmation)
```bash
qubes delete AlphaBot --auto-yes
```

---

## Tips & Tricks

1. **Use Tab Completion**: Most commands support partial name matching
2. **Mid-Chat Commands**: Use `/` prefix in chat for special commands
3. **Scriptable Flags**: Add `-y -q --json` for automation
4. **Negative Indexing**: Use `-1` for latest block, `-2` for second-to-last, etc.
5. **Block Filters**: Combine `--type`, `--search`, `--limit` for precise queries
6. **Color Coding**: Each Qube's output uses their favorite color
7. **Help Anywhere**: Add `--help` to any command for details

---

## Need More Help?

- Command reference: `qubes help commands`
- Detailed command help: `qubes <command> --help`
- Version info: `qubes version`

"""

    md = Markdown(examples)
    console.print(md)
    console.print()


@app.command("chat")
def chat_help():
    """Detailed help for chat command"""

    help_text = """
[bold cyan]qubes chat <name_or_id> [OPTIONS][/bold cyan]

[bold]Description:[/bold]
  Start an interactive chat session with a Qube, or send a single
  message in scriptable mode. Supports voice interaction and mid-chat
  commands for dynamic control.

[bold]Arguments:[/bold]
  [cyan]<name_or_id>[/cyan]    Qube name or ID (supports partial matching)

[bold]Options:[/bold]
  [cyan]-m, --message TEXT[/cyan]     Send single message (scriptable mode)
  [cyan]--voice[/cyan]                Enable voice from start
  [cyan]-q, --quiet[/cyan]            Minimal output (errors only)
  [cyan]--json[/cyan]                 JSON output for parsing

[bold]Interactive Mode:[/bold]
  Type messages normally to chat with the Qube.

  [bold]Mid-Chat Commands:[/bold]
    [cyan]/help[/cyan]           Show available commands
    [cyan]/quit, /exit[/cyan]    End conversation
    [cyan]/voice on|off[/cyan]   Toggle voice synthesis
    [cyan]/stats[/cyan]          Show conversation statistics
    [cyan]/anchor[/cyan]         Anchor session to permanent memory
    [cyan]/clear[/cyan]          Clear screen (keeps history)

[bold]Examples:[/bold]

  [dim]# Interactive chat[/dim]
  $ qubes chat AlphaBot

  [dim]# Chat with voice enabled[/dim]
  $ qubes chat AlphaBot --voice

  [dim]# Scriptable single message[/dim]
  $ qubes chat AlphaBot -m "Hello!" --json --quiet

  [dim]# Parse JSON response[/dim]
  $ response=$(qubes chat AlphaBot -m "2+2" --json -q)
  $ echo $response | jq '.response'

[bold]Tips:[/bold]
  • Use partial name/ID matching (min 4 chars for IDs)
  • Mid-chat commands start with /
  • Voice toggle works during conversation
  • Scriptable mode perfect for automation
"""

    console.print(Panel(help_text, border_style="cyan", title="Chat Command Help"))
    console.print()


@app.command("create")
def create_help():
    """Detailed help for create command"""

    help_text = """
[bold cyan]qubes create [OPTIONS][/bold cyan]

[bold]Description:[/bold]
  Create a new Qube using an interactive wizard or scriptable mode.
  The wizard guides you through all configuration options with menus
  and prompts. Scriptable mode allows full automation.

[bold]Options:[/bold]
  [cyan]--name TEXT[/cyan]         Qube name (required in scriptable mode)
  [cyan]--genesis TEXT[/cyan]      Genesis prompt (required in scriptable mode)
  [cyan]--ai TEXT[/cyan]           AI model name
  [cyan]--voice TEXT[/cyan]        Voice model (optional)
  [cyan]--color TEXT[/cyan]        Favorite color hex code
  [cyan]--blockchain TEXT[/cyan]   Home blockchain (default: bitcoincash)
  [cyan]-y, --auto-yes[/cyan]      Skip confirmation dialog

[bold]Interactive Mode (No Options):[/bold]
  Launches a guided wizard that prompts for:
  • Qube name
  • Genesis prompt (personality/purpose)
  • AI model (menu selection)
  • Voice model (optional, menu selection)
  • Favorite color (color picker with presets)
  • Creator name
  • Home blockchain
  • Capabilities (web search, image gen, code exec)
  • Trust level (0-100)
  • Genesis encryption
  • Wallet address (optional, for NFT minting)

[bold]Scriptable Mode:[/bold]
  Provide at minimum: --name, --genesis, --ai
  Other options use sensible defaults.

[bold]Examples:[/bold]

  [dim]# Interactive wizard (recommended for first time)[/dim]
  $ qubes create

  [dim]# Fully scriptable creation[/dim]
  $ qubes create \\
      --name "AlphaBot" \\
      --genesis "You are a helpful coding assistant" \\
      --ai claude-sonnet-4.5 \\
      --voice openai:alloy \\
      --color "#41DAAA" \\
      --blockchain bitcoincash \\
      --auto-yes

  [dim]# Minimal scriptable (uses defaults)[/dim]
  $ qubes create --name "Bot" --genesis "Helper" --ai gpt-5 -y

[bold]Tips:[/bold]
  • Interactive mode provides descriptions for all options
  • Color picker shows visual previews
  • Preview confirmation before creation (unless --auto-yes)
  • NFT minting requires wallet address
  • Name and genesis prompt are immutable after creation
"""

    console.print(Panel(help_text, border_style="cyan", title="Create Command Help"))
    console.print()


@app.command("settings")
def settings_help():
    """Detailed help for settings commands"""

    help_text = """
[bold cyan]Settings Commands[/bold cyan]

All settings commands support both interactive and scriptable modes.
Only mutable fields can be changed: AI model, voice model, favorite color.
Name and genesis prompt are immutable.

[bold]Commands:[/bold]

[cyan]qubes settings set-ai <qube>[/cyan]
  Interactive AI model selection with descriptions.

[cyan]qubes settings set-voice <qube>[/cyan]
  Interactive voice model selection or disable voice.

[cyan]qubes settings set-color <qube>[/cyan]
  Interactive color picker with presets and custom hex entry.

[cyan]qubes settings set <qube> [OPTIONS][/cyan]
  Batch update settings (scriptable).
  Options: --ai, --voice, --color, --auto-yes, --quiet, --json

[cyan]qubes settings set-global [OPTIONS][/cyan]
  Configure global CLI defaults.
  Options: --default-ai, --default-voice, --default-color,
           --timezone, --theme, --autocomplete

[bold]Examples:[/bold]

  [dim]# Interactive AI model change[/dim]
  $ qubes settings set-ai AlphaBot

  [dim]# Interactive voice change[/dim]
  $ qubes settings set-voice AlphaBot

  [dim]# Interactive color picker[/dim]
  $ qubes settings set-color AlphaBot

  [dim]# Batch update (scriptable)[/dim]
  $ qubes settings set AlphaBot \\
      --ai gpt-5 \\
      --voice tts-1-hd \\
      --color "#FF5733" \\
      --auto-yes

  [dim]# Set global defaults[/dim]
  $ qubes settings set-global \\
      --default-ai claude-sonnet-4.5 \\
      --default-voice openai:alloy \\
      --timezone "US/Eastern"

[bold]Alternative: qubes edit[/bold]
  Use `qubes edit <qube>` for an interactive menu to change
  all mutable settings in one session.
"""

    console.print(Panel(help_text, border_style="cyan", title="Settings Commands Help"))
    console.print()


@app.command("memory")
def memory_help():
    """Detailed help for memory commands"""

    help_text = """
[bold cyan]Memory Commands[/bold cyan]

Inspect, search, and analyze Qube memory blocks.

[bold]Commands:[/bold]

[cyan]qubes mem memories <qube> [OPTIONS][/cyan]
  View recent memory blocks with optional filters.
  Options:
    --limit, -n N      Show N recent blocks (default: 20)
    --type TYPE        Filter by block type (MESSAGE, THOUGHT, etc.)
    --search TEXT      Search block content
    --blocks           Show block type distribution chart
    --json             JSON output

[cyan]qubes mem memory <qube> <block_num>[/cyan]
  View detailed information about a specific block.
  Supports negative indexing: -1 = latest, -2 = second-to-last

[cyan]qubes mem summary <qube> [OPTIONS][/cyan]
  Generate AI-powered summary of memories.
  Options:
    --blocks N         Number of recent blocks (default: 100)
    --save             Save summary as SUMMARY block
    --auto-yes         Skip confirmation

[cyan]qubes mem stats <qube>[/cyan]
  Display memory statistics with bar charts.
  Options: --json

[bold]Block Types:[/bold]
  MESSAGE            User/Qube conversation messages
  THOUGHT            Internal reasoning
  ACTION             Tool calls and actions
  OBSERVATION        Results from actions
  SUMMARY            AI-generated summaries
  DECISION           Decision points
  MEMORY_ANCHOR      Anchored memories
  COLLABORATIVE      Shared/collaborative memories

[bold]Examples:[/bold]

  [dim]# View last 20 blocks[/dim]
  $ qubes mem memories AlphaBot

  [dim]# View last 50 blocks[/dim]
  $ qubes mem memories AlphaBot --limit 50

  [dim]# Filter by message type[/dim]
  $ qubes mem memories AlphaBot --type MESSAGE

  [dim]# Search for keyword[/dim]
  $ qubes mem memories AlphaBot --search "python"

  [dim]# Show block distribution[/dim]
  $ qubes mem memories AlphaBot --blocks

  [dim]# View specific block[/dim]
  $ qubes mem memory AlphaBot 45

  [dim]# View latest block[/dim]
  $ qubes mem memory AlphaBot -1

  [dim]# Generate summary[/dim]
  $ qubes mem summary AlphaBot

  [dim]# View statistics[/dim]
  $ qubes mem stats AlphaBot
"""

    console.print(Panel(help_text, border_style="cyan", title="Memory Commands Help"))
    console.print()


if __name__ == "__main__":
    app()
