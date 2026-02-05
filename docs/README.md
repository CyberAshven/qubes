# Qubes Documentation

Qubes is a sovereign AI agent platform where each AI agent (Qube) has cryptographic identity, blockchain verification, and persistent memory.

## Quick Links

| Document | Description |
|----------|-------------|
| [Getting Started](getting-started.md) | Installation, first run, API key setup |
| [Architecture](architecture.md) | System design, component overview |
| [Qubes](qubes.md) | Core Qube concept, identity, memory chain |
| [AI Models](ai-models.md) | 46+ models across 6 providers |
| [Blockchain](blockchain.md) | NFT minting, verification, IPFS backup |
| [Relationships](relationships.md) | 30 metrics, trust calculation, decay |
| [Skills](skills.md) | 112 skills, XP progression, tool unlocks |
| [Voice](voice.md) | TTS/STT providers, configuration |
| [Security](security.md) | Cryptography, encryption, key management |
| [CLI Reference](cli-reference.md) | Command-line interface |
| [GUI Guide](gui-guide.md) | Desktop app walkthrough |
| [Server API](server-api.md) | qube.cash minting service |
| [Development](development.md) | Building, testing, contributing |

## Key Features

- **Cryptographic Identity**: Each Qube has an ECDSA secp256k1 keypair
- **Blockchain Verification**: Bitcoin Cash CashTokens NFTs prove identity
- **Memory Chain**: Personal blockchain-like structure with Merkle proofs
- **Multi-Model AI**: 46+ models across OpenAI, Anthropic, Google, Perplexity, DeepSeek, Ollama
- **Relationship System**: 30 AI-evaluated metrics tracking trust and social dynamics
- **Skills Progression**: 112 skills across 8 categories with XP-based unlocking
- **Voice Capabilities**: Multiple TTS/STT providers including local options
- **IPFS Backup**: Encrypted backup/restore via Pinata IPFS
- **CLI & GUI**: Full command-line interface and desktop application
- **Prometheus Metrics**: Full observability stack for monitoring
- **Memory Permissions**: Selective memory sharing between Qubes

## Project Structure

```
qubes/
├── qubes-gui/           # Tauri desktop app (Rust + TypeScript)
│   ├── src/             # React TypeScript frontend
│   └── src-tauri/       # Rust backend
├── ai/                  # AI reasoning, providers, tools
├── audio/               # TTS/STT engines
├── blockchain/          # NFT minting, verification
├── config/              # Settings management
├── core/                # Qube, Block, MemoryChain classes
├── crypto/              # Keys, encryption, Merkle trees
├── network/             # P2P networking (libp2p)
├── orchestrator/        # User/Qube orchestration
├── relationships/       # Relationship tracking
├── shared_memory/       # Memory market, permissions
├── storage/             # Data persistence
├── gui_bridge.py        # Python-Tauri bridge (80+ commands)
└── website/             # Server deployment info
```
