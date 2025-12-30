# CLI Reference

Qubes includes a full command-line interface built with Typer.

## Installation

The CLI is included with Qubes. Run from the project directory:

```bash
python -m cli.main
# or
qubes
```

## Commands

### `qubes create`
Create a new Qube with interactive wizard or scriptable flags.

```bash
# Interactive mode
qubes create

# Scriptable mode
qubes create --name "Alice" --genesis "A helpful AI assistant" \
    --ai "gpt-4o" --wallet "bitcoincash:qr..." -y
```

**Options:**
| Flag | Description |
|------|-------------|
| `--name` | Qube name |
| `--genesis` | Genesis prompt (personality) |
| `--ai` | AI model |
| `--voice` | Voice model (e.g., "openai:alloy") |
| `--color` | Favorite color (hex) |
| `--blockchain` | Home blockchain |
| `--wallet` | BCH wallet address (required for NFT) |
| `-y, --auto-yes` | Skip confirmations |

### `qubes list`
List all Qubes.

```bash
qubes list
```

### `qubes chat`
Interactive chat with a Qube.

```bash
# Interactive mode
qubes chat Alice

# Single message (scriptable)
qubes chat Alice -m "Hello, how are you?"

# With voice enabled
qubes chat Alice --voice

# JSON output
qubes chat Alice -m "Hello" --json
```

**Mid-Chat Commands:**
| Command | Action |
|---------|--------|
| `/help` | Show available commands |
| `/quit`, `/exit` | End conversation |
| `/voice on\|off` | Toggle voice synthesis |
| `/stats` | Show session statistics |
| `/anchor` | Anchor session to permanent memory |
| `/clear` | Clear screen |

### `qubes info`
Show detailed information about a Qube.

```bash
qubes info Alice
```

### `qubes edit`
Edit mutable Qube fields (AI model, voice, color).

```bash
qubes edit Alice
```

### `qubes delete`
Delete a Qube (with confirmation).

```bash
qubes delete Alice
qubes delete Alice -y  # Skip confirmation
```

### `qubes version`
Show version information.

```bash
qubes version
```

## Subcommands

### Settings (`qubes settings`)
Manage Qube and global settings.

```bash
qubes settings show Alice
qubes settings set Alice ai_model gpt-4o
```

### Memory (`qubes mem`)
Memory chain inspection and management.

```bash
qubes mem show Alice           # Show recent blocks
qubes mem search Alice "query" # Search memory
qubes mem export Alice         # Export memory chain
```

### Monitoring (`qubes monitor`)
Diagnostics and health checks.

```bash
qubes monitor health
qubes monitor metrics
qubes monitor logs
```

### Relationships (`qubes social`)
Relationship management.

```bash
qubes social list Alice        # List relationships
qubes social show Alice Bob    # Show specific relationship
qubes social stats Alice       # Relationship statistics
```

### Network (`qubes network`)
P2P network operations.

```bash
qubes network status
qubes network peers
qubes network discover
```

### Blockchain (`qubes blockchain`)
NFT and blockchain operations.

```bash
qubes blockchain status Alice
qubes blockchain verify Alice
qubes blockchain mint Alice
```

### Data (`qubes data`)
Export and import Qubes.

```bash
qubes data export Alice --output alice_backup.json
qubes data import alice_backup.json
```

## Session Management

The CLI manages sessions with automatic anchoring:

1. **Session blocks** use negative indices (temporary)
2. **Anchor** converts session blocks to permanent chain
3. **SUMMARY blocks** created when anchoring (if ≥5 blocks)
4. Previous sessions can be recovered on next chat

```
Session starts
    │
    ▼
Blocks: -1, -2, -3, ... (temporary)
    │
    ▼
/anchor command (or session end)
    │
    ▼
Blocks converted to: N+1, N+2, N+3, ... (permanent)
    │
    ▼
SUMMARY block created (if ≥5 blocks)
```

## Scriptable Usage

The CLI supports scriptable workflows:

```bash
# Create Qube and send message
qubes create --name "Bot" --genesis "Helper" --ai "gpt-4o" \
    --wallet "bitcoincash:qr..." -y

qubes chat Bot -m "Summarize this text: ..." --json | jq .response
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GOOGLE_API_KEY` | Google AI API key |
| `PINATA_API_KEY` | Pinata IPFS API key |
