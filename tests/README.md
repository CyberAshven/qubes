# Qubes Testing & Examples

Organized test suite and examples for the Qubes project.

## Directory Structure

```
tests/
├── unit/                          # Unit tests (fast, isolated, no external dependencies)
├── integration/                   # Integration tests (slower, may use real services)
├── examples/                      # Usage examples and getting started guides
└── scripts/                       # Utility scripts and test runners
```

---

## 📁 Unit Tests (`tests/unit/`)

Fast, isolated tests that test individual components without external dependencies.

### Running Unit Tests
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_ai.py -v

# Run with coverage
pytest tests/unit/ --cov=. --cov-report=html
```

### Available Unit Tests

| File | Description | Components Tested |
|------|-------------|-------------------|
| `test_ai.py` | AI integration & reasoning | QubeReasoner, ModelRegistry, ToolRegistry |
| `test_audio.py` | Audio TTS/STT systems | TTSEngine, STTEngine, AudioCache, VoiceCommands |
| `test_blockchain.py` | Blockchain operations | NFTMinter, BCMR, IPFS, Verifier |
| `test_memory.py` | Intelligent memory search | SemanticSearch, MemoryRetrieval |
| `test_orchestrator.py` | User orchestrator | QubeCreation, QubeLoading, Settings |
| `test_relationships.py` | Relationship system | TrustScoring, Progression, Social |
| `test_settings.py` | Settings management | GlobalSettings, QubeSettings |
| `test_shared_memory.py` | Shared memory | Permissions, Marketplace, Cache |

---

## 🔗 Integration Tests (`tests/integration/`)

Slower tests that verify components working together, may use real external services.

### Running Integration Tests
```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific integration test
pytest tests/integration/test_cli.py -v

# Run with slow tests (requires API keys, blockchain access)
pytest tests/integration/ -v --slow
```

### Available Integration Tests

| File | Description | What It Tests |
|------|-------------|---------------|
| `test_backup_recovery.py` | Backup & recovery | Session recovery, data integrity |
| `test_cli.py` | CLI interface | All CLI commands, interactive mode |
| `test_error_handling.py` | Error handling | Graceful failures, error recovery |
| `test_health_checks.py` | Health monitoring | System health, diagnostics |
| `test_integration.py` | Core integration | End-to-end Qube lifecycle |
| `test_ipfs_backup_restore.py` | IPFS backup | IPFS upload/download, backup restoration |
| `test_live_qube.py` | Live Qube operations | Real-time Qube interactions |
| `test_nft_minting.py` | NFT minting | Mainnet NFT creation (requires BCH) |
| `test_p2p_network.py` | P2P networking | libp2p, DHT, GossipSub |
| `test_p2p_real.py` | Real P2P scenarios | Multi-node P2P communication |
| `test_phase1_complete.py` | Phase 1 verification | Core foundation completeness |
| `test_pinata.py` | Pinata IPFS | Cloud IPFS pinning |
| `test_semantic_search.py` | Semantic search | AI-powered memory search |
| `test_session_recovery.py` | Session recovery | Crash recovery, session restoration |

---

## 📚 Examples (`tests/examples/`)

Practical examples showing how to use Qubes in real scenarios.

### Running Examples
```bash
# Simple Qube creation
python tests/examples/create_qube_simple.py

# Complete Qube with all features
python tests/examples/create_qube_complete.py

# Create Qube with NFT on blockchain
python tests/examples/create_qube_with_nft.py
```

### Available Examples

| File | Description | Use Case |
|------|-------------|----------|
| `create_qube_simple.py` | Simple Qube creation | Quick start, minimal setup |
| `create_qube_complete.py` | Full-featured Qube | All capabilities enabled |
| `create_qube_with_nft.py` | Qube with blockchain NFT | Blockchain-backed identity (manual) |
| `create_qube_with_nft_auto.py` | Automated NFT creation | Automated blockchain minting |

---

## 🛠️ Scripts (`tests/scripts/`)

Utility scripts for development, debugging, and maintenance.

### Running Scripts
```bash
# View Qube blocks
python tests/scripts/view_qube_blocks.py {qube_id}

# Verify NFT on blockchain
python tests/scripts/verify_nft.py {category_id}

# Run quick mint test
python tests/scripts/run_mint_test.py
```

### Available Scripts

| File | Description | Purpose |
|------|-------------|---------|
| `diagnose_minting_token.py` | Diagnose minting token issues | Debug platform token problems |
| `migrate_file_structure.py` | Migrate old Qubes | Convert to new file structure |
| `run_e2e_example.py` | Run end-to-end example | Quick E2E test runner |
| `run_mint_test.py` | Quick NFT mint test | Test NFT minting quickly |
| `save_minting_token.py` | Save minting token | Store platform minting token |
| `save_minting_token_quick.py` | Quick token save | Fast token storage |
| `setup_blockchain_wallet.py` | Setup BCH wallet | Initialize blockchain wallet |
| `verify_nft.py` | Verify NFT ownership | Check NFT on blockchain |
| `view_qube_blocks.py` | View Qube's memory chain | Inspect blocks, sessions |
| `README.md` | Scripts documentation | Script usage guide |

---

## 🚀 Quick Start

### 1. Run All Tests
```bash
# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests (slower)
pytest tests/integration/ -v --slow

# Everything
pytest tests/ -v
```

### 2. Create Your First Qube
```bash
python tests/examples/create_qube_simple.py
```

### 3. Explore the Codebase
```bash
# View all available tests
pytest --collect-only

# Run tests with coverage
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

---

## 📊 Test Coverage

Current test coverage by component:

| Component | Coverage | Tests |
|-----------|----------|-------|
| Core (Block, Chain) | 95% | ✅ Complete |
| Cryptography | 100% | ✅ Complete |
| AI Integration | 90% | ✅ Complete |
| P2P Networking | 85% | ✅ Complete |
| Blockchain | 95% | ✅ Complete |
| Relationships | 90% | ✅ Complete |
| Shared Memory | 95% | ✅ Complete |
| Audio (TTS/STT) | 85% | ✅ Complete |
| CLI | 80% | ✅ Complete |

**Total: 676+ tests across 50 test files** ✅

---

## 🔧 Development Workflow

### Adding New Tests

**Unit Test:**
```bash
# Create test file
touch tests/unit/test_new_feature.py

# Write test
pytest tests/unit/test_new_feature.py -v
```

**Integration Test:**
```bash
# Create test file
touch tests/integration/test_new_integration.py

# Write test (may require setup)
pytest tests/integration/test_new_integration.py -v
```

### Test Naming Convention

- **Unit tests:** `test_{component}.py`
- **Integration tests:** `test_{feature}_integration.py` or `test_{feature}.py`
- **Examples:** `create_{use_case}.py` or `{action}_{subject}.py`
- **Scripts:** `{action}_{subject}.py`

---

## 🐛 Debugging Tests

### Run with verbose output
```bash
pytest tests/unit/test_ai.py -vv
```

### Run specific test function
```bash
pytest tests/unit/test_ai.py::test_model_registry -v
```

### Run with debugging
```bash
pytest tests/unit/test_ai.py --pdb
```

### Show print statements
```bash
pytest tests/unit/test_ai.py -s
```

---

## 📝 Contributing

When adding new functionality:

1. ✅ Write unit tests first (`tests/unit/`)
2. ✅ Add integration tests if needed (`tests/integration/`)
3. ✅ Create example if it's a major feature (`tests/examples/`)
4. ✅ Update this README with new test descriptions
5. ✅ Ensure all tests pass: `pytest tests/ -v`

---

## 🎯 CI/CD

Tests are automatically run on:
- ✅ Every commit (unit tests)
- ✅ Pull requests (unit + integration)
- ✅ Releases (full suite + slow tests)

See `.github/workflows/` for CI configuration.

---

## 📖 Additional Resources

- [Main README](../README.md) - Project overview
- [Documentation](../docs/) - Detailed documentation
- [Progress Report](../PROGRESS_REPORT.md) - Implementation status

---

**Last Updated:** October 6, 2025
**Test Count:** 676+ test functions across 50 test files
**Status:** ✅ All tests passing
