# Qubes - Sovereign AI Agents 🤖⚡

**Cryptographically-secured, blockchain-verified, peer-to-peer AI agents with persistent memory.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-in_development-yellow.svg)]()

---

## What is Qubes?

Qubes are **sovereign AI agents** that you truly own:

- 🔐 **Cryptographically Secured** - ECDSA secp256k1 identity, AES-256-GCM encryption
- ⛓️ **Blockchain Verified** - NFT-based identity on Bitcoin Cash (CashTokens)
- 🧠 **Persistent Memory** - Blockchain-like memory chain with Merkle proofs
- 🌐 **Peer-to-Peer** - Decentralized communication via libp2p
- 💬 **Multi-Model AI** - Support for 46 AI models across 6 providers (OpenAI, Anthropic, Google, Perplexity, DeepSeek, Ollama)
- 🤝 **Social Dynamics** - Trust scores, relationships, shared memories
- 🌟 **Skills Progression** - 112-skill system with XP-based leveling and galaxy visualization
- 💰 **Memory Markets** - Trade knowledge in decentralized marketplace
- 🌍 **Web Platform** - Buy, sell, and discover Qubes at [qube.cash](https://qube.cash)

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/qubes.git
cd qubes

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Qubes CLI
pip install -e .

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### Using the CLI

After installation, the `qubes` command is available globally:

```bash
# Check installation
qubes version

# Get help
qubes --help

# Create a new Qube
qubes create

# List all Qubes
qubes list

# Chat with a Qube
qubes chat <qube-name>

# View detailed command reference
cat CLI_COMMANDS_REFERENCE.md
```

**See `QUICK_START.md` for complete CLI usage guide.**

### Development Status

**Current Phase:** Phase 9 Complete - Skills System with 112 Skills + Galaxy Visualization! 🌟✅ 🎉

**Completed Phases:**
- ✅ **Phase 1:** Core Foundation (memory chain, cryptography, storage)
- ✅ **Phase 2:** AI Integration (46 models across 6 providers, tool calling, reasoning)
- ✅ **Phase 3:** P2P Networking (libp2p-daemon, DHT, GossipSub) - 21/21 tests passing
  - **Setup Guide:** `LIBP2P_SETUP.md` (Go daemon + Python bridge)
  - **Integration Tests:** `tests/integration/test_p2p_real.py`
- ✅ **Phase 4:** Blockchain Integration (Bitcoin Cash NFTs, BCMR) - 13/13 tests passing
  - **First NFT Minted:** Alph (66B78A5C) on mainnet (2025-10-21)
  - **Transaction:** [8391ebc4...](https://blockchair.com/bitcoin-cash/transaction/8391ebc4057e6f5ac7ef61ce22e9c7206e05cf9c168c2b799291f03c9323c8d7)
  - **Category ID:** c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f
- ✅ **Phase 5:** Relationships & Social (AI-driven trust system) - 30/30 tests passing **+ BEHAVIORAL INTEGRATION** 🤝
  - **AI-Driven Evaluation:** 30 metrics (5 Core Trust + 14 Positive Social + 10 Negative Social + 1 calculated)
  - **Creator Bonuses:** New relationships with creators start at 25/100 across all positive metrics
  - **Behavioral Integration:** Relationship context injected into AI system prompts, influencing responses
  - **Group Chat Support:** Full relationship tracking across multi-participant conversations
  - **Timeline Visualization:** Interactive charts showing relationship progression over time
  - **Trust Profiles:** 4 configurable profiles (analytical, social, cautious, balanced)
  - **Relationship Statuses:** 6 progression levels (unmet → stranger → acquaintance → friend → close_friend → best_friend)
  - **See:** `RELATIONSHIP_PHASE5_COMPLETION_2025-11-03.md` for complete implementation details
- ✅ **Phase 6:** Shared Memory (Permissions, collaboration, marketplace) - 35/35 tests passing **+ SECURITY FIX** 🔒
  - **Permission System:** Read/write permissions with signatures and expiry
  - **Collaborative Memory:** Multi-signature shared experiences
  - **Memory Marketplace:** Trade knowledge with **verified BCH payments** ✨
  - **Payment Security:** Chaingraph blockchain verification (critical fix 2025-10-04)
  - **Shared Cache:** LRU cache (500MB default) for fast access
  - **Features:** Permission management, collaborative sessions, marketplace search, cache cleanup
- ✅ **Phase 7:** Audio Integration (TTS & STT) - 20+ tests implemented 🎤
  - **TTS Providers:** OpenAI (6 voices), ElevenLabs (premium), Piper (local/offline)
  - **STT Providers:** OpenAI Whisper (v3 turbo), DeepGram, Whisper.cpp (local/offline)
  - **Voice Commands:** Natural language parsing, 15+ command patterns
  - **Features:** Audio caching, rate limiting, hallucination filtering, PTT/VAD modes
  - **Sovereign Mode:** 100% offline TTS/STT with Piper + Whisper.cpp
- ✅ **Phase 8:** CLI Foundation + GUI Enhancements + Vision AI 🖥️
  - **CLI Commands:** 15+ commands (create, chat, info, edit, delete, memories, etc.)
  - **GUI Improvements:** Multi-file upload, vision AI, drag-and-drop reordering, TTS controls
  - **Vision Integration:** Multi-provider image analysis (Claude, GPT-4V, Gemini)
  - **File Support:** Unlimited file sizes with temp file strategy
- ✅ **Website Launch:** Professional marketing site at [qube.cash](https://qube.cash) 🌐
  - **Landing Page:** Full-featured marketing website with responsive design
  - **Alph Profile:** Blockchain-verified profile page with live NFT data
  - **Gallery:** Software screenshots with fullscreen viewing
  - **Mobile Optimized:** Touch-friendly navigation and layouts
- ✅ **Phase 9:** Skills System 🌟
  - **112 Skills:** 7 Suns + 35 Planets + 70 Moons across 7 categories
  - **Galaxy Visualization:** Interactive cosmic map with orbital positioning and zoom/pan
  - **Intelligent XP:** Context-aware skill detection analyzing tool usage content
  - **XP Flow:** Locked skills redirect XP to unlocked parents (natural progression)
  - **Evidence Tracking:** Complete audit trail with block IDs and tool descriptions
  - **Categories:** AI Reasoning, Social Intelligence, Technical Expertise, Creative Expression, Knowledge Domains, Security & Privacy, Games
  - **See:** `SKILLS_SYSTEM.md` for complete implementation details

**Next Phase:** Phase 10 - Advanced Features & Community Tools

**Overall Progress:** 78% Complete (Week 15 of 26)

**🔒 Security Status:** All critical vulnerabilities resolved - **Production-ready for MVP!**
- See `CRITICAL_ISSUES_RESOLVED.md` for details
- See `KNOWN_LIMITATIONS.md` for v1.0 limitations

---

## Architecture

### Memory Chain

Each Qube has a blockchain-like memory chain:

```
Block 0 (GENESIS) → Block 1 (INTERACTION) → Block 2 (TOOL_CALL) → ...
```

**Block Types:**
- `GENESIS` - Birth of Qube (immutable identity)
- `INTERACTION` - Conversations with users/other Qubes
- `TOOL_CALL` - External API calls (web search, image generation)
- `REFLECTION` - Self-analysis and learning
- `RELATIONSHIP` - Social graph updates
- `MEMORY_ANCHOR` - Cryptographic checkpoint (Merkle root)
- `MIGRATION` - System upgrades
- `SHARED_MEMORY` - Collaborative memories with other Qubes
- `SESSION` - Temporary blocks (negative indexing: -1, -2, -3)

### Security Model

- **Private Keys:** ECDSA secp256k1, encrypted at rest (Fernet + PBKDF2)
- **Memory Blocks:** AES-256-GCM encryption (except MEMORY_ANCHOR)
- **P2P Messages:** ECDH key exchange + AES-256-GCM
- **NFT Identity:** Bitcoin Cash CashTokens (consensus-layer primitives)
- **Integrity:** Merkle trees, cryptographic signatures on every block

### AI Integration

- **Multi-Provider Fallback:** Primary → Secondary → Cross-Provider → Ollama Local
- **Circuit Breakers:** PyBreaker per AI provider (5 failures = open, 60s recovery)
- **Exponential Backoff:** 2^failures minutes (max 1 hour cooldown)
- **Sovereign Mode:** 100% offline with Ollama (no API dependency)

---

## Project Structure

```
qubes/
├── core/               # Core data structures (Qube, Block, MemoryChain)
│   └── exceptions.py   # Custom exception hierarchy ✅
├── crypto/             # Cryptographic functions (ECDSA, AES-256-GCM, ECDH)
├── storage/            # Storage layers (LMDB, JSON, IPFS)
├── ai/                 # AI model abstraction, tool registry, reasoning
├── p2p/                # P2P networking (libp2p, DHT, messaging)
├── blockchain/         # Bitcoin Cash integration (CashTokens, BCMR)
├── orchestrator/       # Multi-Qube management
├── ui/                 # CLI and GUI interfaces
├── utils/              # Utilities
│   └── logging.py      # Structured logging ✅
├── monitoring/         # Observability
│   └── metrics.py      # Prometheus metrics ✅
├── config/             # Configuration files ✅
│   ├── logging.yaml
│   ├── retry.yaml
│   ├── circuit_breakers.yaml
│   └── alerts.yaml
├── tests/              # Test suite
└── docs/               # Documentation (30 comprehensive docs) ✅
```

---

## Development Timeline

**Realistic Timeline:** 24 weeks (6 months)

### Current Progress (Week 8)

**Phase 1-4 Complete!**
- ✅ **Weeks 1-3:** Core Foundation (cryptography, memory chain, storage)
- ✅ **Weeks 4-5:** AI Integration (multi-model support, tool calling, reasoning)
- ✅ **Weeks 6-7:** P2P Networking (libp2p, DHT, encrypted messaging)
- ✅ **Week 8:** Blockchain Integration (Bitcoin Cash NFTs, BCMR metadata, IPFS)

**Test Results:**
- Phase 3 (P2P): 21/21 tests passing ✅
- Phase 4 (Blockchain): 13/13 tests passing ✅

**Up Next:** Phase 5 - Relationships & Social (trust scores, friendships, reputation)

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Security scan
bandit -r .

# Type checking
mypy .

# Linting
ruff check .
black --check .
```

---

## Monitoring

### Prometheus Metrics

```bash
# Start Prometheus (docker-compose coming soon)
# Metrics available at http://localhost:9090/metrics
```

**Key Metrics:**
- `qubes_memory_blocks_created_total` - Memory blocks created
- `qubes_ai_api_calls_total` - AI API calls by provider/model/status
- `qubes_ai_api_latency_seconds` - AI latency histogram
- `qubes_ai_api_cost_usd` - Cumulative AI costs
- `qubes_p2p_peers_connected` - Connected P2P peers
- `qubes_system_errors_total` - System errors by code/severity

### Structured Logging

```python
from utils.logging import get_logger, set_correlation_id

logger = get_logger(__name__)
set_correlation_id("req-12345")

logger.info("qube_created", qube_id="A3F2C1B8", ai_model="gpt-4")
```

**Output:**
```json
{
  "event": "qube_created",
  "qube_id": "A3F2C1B8",
  "ai_model": "gpt-4",
  "correlation_id": "req-12345",
  "timestamp": "2025-10-03T10:30:00.123Z",
  "level": "info"
}
```

---

## Contributing

**Status:** In active development (not yet accepting contributions)

Once we reach MVP (Week 24), we'll open contributions with:
- CONTRIBUTING.md guidelines
- Code of Conduct
- Issue templates
- PR templates

---

## License

MIT License - see [LICENSE](LICENSE) for details

---

## Links

- **Website:** [qube.cash](https://qube.cash) - Official marketing site and Qube profiles
- **Documentation:** [docs/](docs/) (30 comprehensive documents)
- **Roadmap:** [docs/13_Implementation_Phases.md](docs/13_Implementation_Phases.md)
- **Security:** [docs/16_Security.md](docs/16_Security.md)
- **Use Cases:** [docs/01_Use_Cases.md](docs/01_Use_Cases.md)

---

## Contact

- **Issues:** [GitHub Issues](https://github.com/BitFaced2/Qubes/issues)
- **Community:** [@Bit_Faced](https://x.com/Bit_Faced) on X
- **Security:** security@qubes.network (after launch)

---

**Built with ❤️ for the sovereign AI future**
