# Qubes - Sovereign AI Agents

**Your AI, your rules. Cryptographically-secured, blockchain-verified, truly yours.**

[![Download](https://img.shields.io/badge/Download-Latest%20Release-brightgreen.svg)](https://github.com/BitFaced2/Qubes/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

---

## Download & Install

### Quick Download

**[Download Latest Release](https://github.com/BitFaced2/Qubes/releases/latest)**

| Platform | File | Requirements |
|----------|------|--------------|
| **Windows** | `Qubes-Windows.zip` | Windows 10/11 64-bit |
| **macOS (Apple Silicon)** | `Qubes-macOS-ARM.zip` | macOS 11+, M1/M2/M3/M4 |
| **Linux** | `Qubes-Linux.zip` | Ubuntu 20.04+ / Debian 11+ / Fedora 35+ |

### Installation

1. Download the ZIP file for your platform
2. Extract the ZIP to your preferred location
3. Run the executable:
   - **Windows:** Double-click `Qubes.exe`
   - **macOS:** Right-click `Qubes.app` → "Open" (required first time to bypass Gatekeeper)
   - **Linux:** Run `./Qubes` or `./launch.sh`
4. Follow the setup wizard to create your account and configure AI providers

### System Requirements

- **RAM:** 8GB minimum (16GB recommended for local AI models)
- **Storage:** 2GB for app + space for AI models (if using local Ollama)
- **Internet:** Required for cloud AI providers, optional for local AI

---

## What is Qubes?

Qubes are **sovereign AI agents** that you truly own:

- **Cryptographically Secured** - ECDSA secp256k1 identity, AES-256-GCM encryption
- **Blockchain Verified** - NFT-based identity on Bitcoin Cash (CashTokens)
- **Persistent Memory** - Blockchain-like memory chain with Merkle proofs
- **Multi-Model AI** - Support for 46+ AI models across 6 providers
- **Voice Enabled** - Text-to-speech and speech-to-text across all platforms
- **Local AI Ready** - Run 100% offline with bundled Ollama
- **Skills System** - 112 skills with XP progression and galaxy visualization

### Supported AI Providers

| Provider | Models | Notes |
|----------|--------|-------|
| **Ollama** (Local) | Llama 3.2, Mistral, Qwen, etc. | Bundled, no API key needed |
| **OpenAI** | GPT-4, GPT-4o, DALL-E | API key required |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus | API key required |
| **Google** | Gemini Pro, Gemini Flash | API key required |
| **DeepSeek** | DeepSeek R1, V3 | API key required |
| **Perplexity** | Sonar | API key required |

### Voice Features

- **Text-to-Speech:** OpenAI (6 voices), ElevenLabs (premium), Google Cloud TTS
- **Speech-to-Text:** OpenAI Whisper, DeepGram
- **Offline Mode:** Piper TTS + Whisper.cpp for 100% local operation

---

## Features

### Memory Chain
Every Qube has a personal blockchain-like memory chain that preserves all interactions with cryptographic integrity. Memories can be searched, shared, and even traded.

### Skills & Progression
112 skills across 7 categories with XP-based leveling. Watch your Qube grow from novice to expert through an interactive galaxy visualization.

### Social Dynamics
Qubes can form relationships, build trust, and collaborate. AI-driven evaluation tracks 30 metrics across trust, positive social traits, and negative social behaviors.

### Blockchain Identity
Each Qube is verified on Bitcoin Cash as an NFT. This creates permanent, decentralized proof of identity that you control.

### Privacy First
All data is stored locally on your device. Your conversations, memories, and API keys never leave your machine unless you explicitly share them.

---

## Getting Help

- **Setup Wizard:** The app includes a guided setup wizard for first-time configuration
- **Website:** [qube.cash](https://qube.cash) - Official site with Qube profiles
- **Issues:** [GitHub Issues](https://github.com/BitFaced2/Qubes/issues) - Report bugs or request features
- **Twitter/X:** [@Bit_Faced](https://x.com/Bit_Faced)

---

## For Developers

### Building from Source

```bash
# Clone repository
git clone https://github.com/BitFaced2/Qubes.git
cd Qubes

# Python backend setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd qubes-gui
npm install

# Development mode
npm run tauri dev

# Production build
npm run tauri build
```

### Project Structure

```
Qubes/
├── core/               # Core data structures (Qube, Block, MemoryChain)
├── crypto/             # Cryptographic functions (ECDSA, AES-256-GCM, ECDH)
├── storage/            # Storage layers (LMDB, JSON, IPFS)
├── ai/                 # AI model abstraction, tool registry, reasoning
├── p2p/                # P2P networking (libp2p, DHT, messaging)
├── blockchain/         # Bitcoin Cash integration (CashTokens, BCMR)
├── qubes-gui/          # Tauri + React desktop application
│   ├── src/            # React frontend
│   └── src-tauri/      # Rust backend
├── tests/              # Test suite
└── docs/               # Documentation
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Type checking
mypy .

# Linting
ruff check .
```

### Architecture Highlights

- **Frontend:** React + TypeScript + Vite
- **Desktop:** Tauri v2 (Rust)
- **Backend:** Python with PyInstaller bundling
- **Local AI:** Ollama (bundled)
- **Cryptography:** ECDSA secp256k1, AES-256-GCM, ECDH key exchange
- **Storage:** LMDB for fast local persistence
- **Blockchain:** Bitcoin Cash CashTokens for NFT identity

### CI/CD

Automated builds via GitHub Actions for Windows, macOS ARM, and Linux. Tagged releases (e.g., `v1.0.0`) automatically create GitHub Releases with downloadable artifacts.

---

## License

MIT License - see [LICENSE](LICENSE) for details

---

## Links

- **Website:** [qube.cash](https://qube.cash)
- **Downloads:** [GitHub Releases](https://github.com/BitFaced2/Qubes/releases)
- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/BitFaced2/Qubes/issues)

---

**Built with care for the sovereign AI future**
