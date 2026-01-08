# Changelog

All notable changes to Qubes are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - v0.2.8

### Added
- **Recall Last button** - Load most recent MESSAGE or SUMMARY block into empty chat for context continuity
- **Active Context panel** - Shows token estimates and recent messages preview in chat
- **Enhanced Block Recall** - BM25 search algorithm with configurable depth and token settings
- **Transaction History** - View BCH transaction history in wallet tab
- **Chess statistics** - Track win/loss/draw records per opponent

### Changed
- Block Browser now displays actual Qube avatar images with larger names
- Genesis block display enhanced (removed vestigial capabilities)
- Wallet awareness improvements and better UX
- Wallets tab shows addresses immediately when switching qubes
- Renamed "Wallet" label to "Qube" on cards

### Fixed
- Persistent wallet balance cache fixes 0.00000000 display bug on startup
- Block Browser avatar now shows actual image instead of letter fallback

### Security
- Enforced official Qubes category ID as consensus rule
- Removed hardcoded credentials and user data from repository

### Technical
- Chess module added to PyInstaller hidden imports

## [0.2.7] - 2025-01-06

### Fixed
- Lazy chess import for PyInstaller bundle compatibility

## [0.2.6] - 2025-01-06

### Added
- **Chess game system** - Qube vs Qube and Qube vs Human gameplay
- **Asymmetric multi-sig wallet system** - Enhanced wallet security with improved UI

## [0.2.5] - 2024-12-31

### Fixed
- Missing fonts for external users resolved

## [0.2.4] - 2024-12-30

### Added
- Skills Progression display in SUMMARY blocks

### Changed
- Improved splash screen layout and sizing

## [0.2.3] - 2024-12-29

### Added
- Clean documentation based on actual codebase

### Fixed
- Qube minting functionality restored

### Security
- Security improvements across the platform

## [0.2.2] - 2024-12-28

### Fixed
- Image display issues resolved

### Security
- Security hardening measures implemented

## [0.2.1] - 2024-12-22

### Added
- New splash screen design
- Window opens maximized by default

### Fixed
- Splash screen clipping on high-DPI displays

## [0.2.0] - 2024-12-22

First stable release with production-ready features.

### Added
- **Auto-update system** - Automatic updates via qube.cash endpoint
- **Full GUI application** - Tauri-based desktop app with React frontend
- **Multi-model AI support** - 46+ models across 6 providers (OpenAI, Anthropic, Google, Perplexity, DeepSeek, Ollama)
- **Cryptographic identity** - ECDSA secp256k1 keypairs for each Qube
- **Blockchain verification** - Bitcoin Cash CashTokens NFT minting
- **Memory chain** - Personal blockchain-like structure with Merkle proofs
- **Relationship system** - 30 AI-evaluated metrics tracking trust and social dynamics
- **Skills progression** - 112 skills across 7 categories with XP-based unlocking
- **Voice capabilities** - Multiple TTS/STT providers including local options
- **IPFS backup** - Encrypted backup/restore via Pinata
- **P2P networking** - libp2p-based peer-to-peer communication
- **Memory permissions** - Selective memory sharing between Qubes

---

## Pre-release History

### [0.1.9] - 2024-12-21
- Auto-update test release

### [0.1.8] - 2024-12-21
- Switched updater endpoint to qube.cash

### [0.1.7] - 2024-12-21
- Enabled updater artifact generation

### [0.1.6] - 2024-12-21
- Fixed updater signing with refreshed secrets

### [0.1.5] - 2024-12-20
- Fixed timezone crash in PyInstaller bundle

### [0.1.4] - 2024-12-20
- Fixed version display in settings
- Fixed API key persistence from wizard

[Unreleased]: https://github.com/BitFaced2/Qubes/compare/v0.2.7...HEAD
[0.2.7]: https://github.com/BitFaced2/Qubes/compare/v0.2.6...v0.2.7
[0.2.6]: https://github.com/BitFaced2/Qubes/compare/v0.2.5...v0.2.6
[0.2.5]: https://github.com/BitFaced2/Qubes/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/BitFaced2/Qubes/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/BitFaced2/Qubes/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/BitFaced2/Qubes/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/BitFaced2/Qubes/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/BitFaced2/Qubes/releases/tag/v0.2.0
