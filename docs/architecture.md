# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Tauri Desktop App                        │
├─────────────────────────────────────────────────────────────┤
│  React/TypeScript Frontend    │    Rust Backend (lib.rs)    │
│  - Chat interfaces            │    - Input validation       │
│  - Qube roster                │    - Subprocess management  │
│  - Settings UI                │    - Secret handling        │
│  - Skills visualization       │    - Tauri commands         │
└───────────────┬───────────────┴──────────────┬──────────────┘
                │ invoke()                      │ spawn subprocess
                ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   gui_bridge.py (6300+ lines)               │
│  - 80+ command handlers                                     │
│  - Async message processing                                 │
│  - Streaming responses                                      │
└───────────────────────────────┬─────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌───────────────┐
│ UserOrchestrator│   │    AI Module    │     │   Blockchain  │
│ - Qube CRUD     │   │ - Reasoner      │     │ - NFT minting │
│ - API keys      │   │ - 6 providers   │     │ - Verification│
│ - Multi-qube    │   │ - Tool calling  │     │ - Chain sync  │
└───────┬─────────┘   └────────┬────────┘     └───────────────┘
        │                      │
        ▼                      ▼
┌───────────────┐     ┌─────────────────┐
│     Qube      │     │  External APIs  │
│ - Identity    │     │ - OpenAI        │
│ - Memory chain│     │ - Anthropic     │
│ - Relationships│    │ - Google        │
│ - Skills      │     │ - etc.          │
└───────────────┘     └─────────────────┘
```

## Component Details

### Frontend (TypeScript/React)
**Location**: `qubes-gui/src/`

Key files:
- `App.tsx` - Main application, routing, authentication
- `components/ChatInterface.tsx` - Single Qube chat
- `components/MultiQubeChatInterface.tsx` - Multi-Qube conversations
- `components/QubeRoster.tsx` - Qube selection and management
- `components/SettingsPanel.tsx` - Configuration UI
- `components/SkillsDisplay.tsx` - Solar system visualization

### Rust Backend
**Location**: `qubes-gui/src-tauri/src/lib.rs` (~2500 lines)

Responsibilities:
- **Input Validation**: Sanitizes all inputs before passing to Python
- **Path Traversal Prevention**: Validates file paths
- **Secret Handling**: Passes passwords via stdin, not CLI args
- **Subprocess Management**: Spawns Python bridge, handles I/O
- **Tauri Commands**: 60+ `#[tauri::command]` functions

### Python Bridge
**Location**: `gui_bridge.py` (~6300 lines)

Command dispatcher handling:
- Qube lifecycle (create, load, delete)
- Chat messaging and streaming
- Settings management
- Voice processing
- Blockchain operations
- Skills and relationships

### Core Module
**Location**: `core/`

| File | Purpose |
|------|---------|
| `qube.py` | Qube class - identity, memory, relationships |
| `block.py` | Block types and structure |
| `memory_chain.py` | Blockchain-like memory storage |
| `session.py` | Session management with anchoring |
| `exceptions.py` | Custom exception hierarchy |

### AI Module
**Location**: `ai/`

| File | Purpose |
|------|---------|
| `reasoner.py` | Main reasoning loop, tool calling |
| `model_registry.py` | 46+ model definitions |
| `providers/*.py` | Provider implementations |
| `tools/*.py` | Tool definitions and handlers |

### Data Flow

#### Message Processing
```
User Input
    │
    ▼
Tauri Command (Rust)
    │ validate input
    ▼
gui_bridge.py
    │ dispatch to handler
    ▼
UserOrchestrator
    │ get active qube
    ▼
Qube.process_message()
    │
    ├─► Create MESSAGE block
    │
    ▼
Reasoner.reason()
    │
    ├─► Call AI provider
    ├─► Handle tool calls
    ├─► Create response blocks
    │
    ▼
Stream response back to frontend
```

## Data Storage

```
data/
└── users/
    └── {username}/
        ├── config.yaml          # User settings
        ├── keys/
        │   └── master.key       # Encrypted master key
        └── qubes/
            └── {name}_{id}/
                ├── identity.json    # Qube metadata
                ├── private_key.pem  # Encrypted ECDSA key
                ├── public_key.pem   # Public key
                ├── chain/
                │   ├── chain_state.json
                │   └── blocks/
                │       ├── 0_GENESIS_*.json
                │       └── ...
                ├── relationships/
                │   └── relationships.json
                ├── skills/
                │   ├── skills.json
                │   └── skill_history.json
                └── session/
                    └── *.json
```

## CLI Module
**Location**: `cli/`

Full command-line interface using Typer:
- `cli/main.py` - Main entry point, core commands
- `cli/commands/` - Subcommand modules (settings, memory, monitoring, etc.)
- Interactive chat with mid-session commands
- Scriptable usage with JSON output

## Session Management

Sessions use negative indexing for temporary blocks:

```
Session Active
├── Block -1 (MESSAGE)
├── Block -2 (THOUGHT)
├── Block -3 (MESSAGE)
...

On Anchor:
├── Block N+1 (MESSAGE)      # Converted from -1
├── Block N+2 (THOUGHT)      # Converted from -2
├── Block N+3 (MESSAGE)      # Converted from -3
└── Block N+4 (SUMMARY)      # Auto-generated if ≥5 blocks
```

- **Auto-anchor threshold**: Configurable (default 50 blocks)
- **SUMMARY blocks**: Created when ≥5 blocks are anchored
- **Session recovery**: Unanchored sessions can be recovered on restart

## Monitoring & Metrics
**Location**: `monitoring/metrics.py`

Prometheus metrics for observability:

| Category | Metrics |
|----------|---------|
| Memory Chain | blocks_created, blocks_anchored, search_duration |
| AI API | calls_total, latency, tokens, cost_usd |
| P2P Network | peers_connected, messages_sent/received, bandwidth |
| Storage | operations, cache_hits/misses, disk_usage |
| Blockchain | nft_mints, verifications, transaction_latency |
| System | errors, warnings, active_qubes, uptime |

## Memory Permissions
**Location**: `shared_memory/permissions.py`

Selective memory sharing between Qubes:
- Grant access to specific block ranges
- READ or READ_WRITE permission levels
- Expiry-based permissions (optional)
- Cryptographically signed permissions

## Security Boundaries

1. **Rust Layer**: Validates all input, prevents injection attacks
2. **Python Layer**: Business logic, no direct user input
3. **Encryption**: Keys encrypted at rest with PBKDF2 (600K iterations)
4. **Secrets**: Never passed via command line, always stdin or env vars
