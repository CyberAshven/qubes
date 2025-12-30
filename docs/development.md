# Development

Guide for building, testing, and contributing to Qubes.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Rust** (latest stable)
- **Git**

## Setup

### Clone Repository

```bash
git clone https://github.com/bit-faced/Qubes.git
cd Qubes
```

### Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing
```

### Frontend Setup

```bash
cd qubes-gui
npm install
```

### Rust Setup

```bash
cd qubes-gui/src-tauri
cargo build
```

## Running in Development

### Start Backend Only

```bash
python gui_bridge.py
```

### Start Full App (Development Mode)

```bash
cd qubes-gui
npm run tauri dev
```

This starts:
- Vite dev server with hot reload
- Tauri app in development mode
- Python backend via subprocess

## Project Structure

```
qubes/
├── ai/                    # AI reasoning and providers
│   ├── providers/         # OpenAI, Anthropic, Google, etc.
│   ├── tools/             # Tool definitions and handlers
│   ├── reasoner.py        # Main reasoning loop
│   └── model_registry.py  # Model definitions
├── audio/                 # TTS/STT engines
├── blockchain/            # NFT minting, verification
├── cli/                   # Command-line interface
├── config/                # Settings management
├── core/                  # Core classes (Qube, Block, etc.)
├── crypto/                # Cryptographic utilities
├── network/               # P2P networking
├── orchestrator/          # User/Qube orchestration
├── relationships/         # Relationship tracking
├── shared_memory/         # Memory market, permissions
├── storage/               # Data persistence
├── utils/                 # Logging, skills, helpers
├── monitoring/            # Metrics collection
├── tests/                 # Test suite
├── qubes-gui/             # Tauri desktop app
│   ├── src/               # React TypeScript frontend
│   └── src-tauri/         # Rust backend
├── website/               # Server deployment
├── docs/                  # Documentation
├── gui_bridge.py          # Python-Tauri bridge
└── requirements.txt       # Python dependencies
```

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Tests

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Specific file
pytest tests/unit/test_qube.py

# Specific test
pytest tests/unit/test_qube.py::test_qube_creation
```

### Test Coverage

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Building for Production

### Build Desktop App

```bash
cd qubes-gui
npm run tauri build
```

Output: `qubes-gui/src-tauri/target/release/bundle/`

### Build Installer (Windows)

```bash
npm run tauri build -- --target x86_64-pc-windows-msvc
```

Output: `Qubes_x.x.x_x64-setup.exe`

## Code Style

### Python
- Follow PEP 8
- Use type hints
- Docstrings for public functions

```python
def create_qube(name: str, personality: Optional[Dict] = None) -> Qube:
    """
    Create a new Qube with the given name.

    Args:
        name: Display name for the Qube
        personality: Optional personality configuration

    Returns:
        Newly created Qube instance
    """
    ...
```

### TypeScript
- Use TypeScript strict mode
- Prefer functional components
- Use React hooks

### Rust
- Follow Rust conventions
- Use `clippy` for linting
- Handle all errors explicitly

## Adding a New AI Provider

1. Create provider file: `ai/providers/newprovider.py`

```python
from ai.providers.base import BaseProvider

class NewProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.client = NewProviderClient(api_key)

    async def generate(self, messages, **kwargs):
        response = await self.client.chat(messages)
        return response.content

    async def generate_stream(self, messages, **kwargs):
        async for chunk in self.client.chat_stream(messages):
            yield chunk.content
```

2. Register in `ai/model_registry.py`:

```python
MODELS["newprovider-model"] = {
    "provider": "newprovider",
    "context_window": 128000,
    ...
}
```

3. Add to provider factory in `ai/reasoner.py`

## Adding a New Tool

1. Define tool in `ai/tools/definitions.py`:

```python
TOOLS["my_new_tool"] = {
    "name": "my_new_tool",
    "description": "Does something useful",
    "parameters": {
        "param1": {"type": "string", "description": "..."},
    }
}
```

2. Implement handler in `ai/tools/handlers.py`:

```python
async def handle_my_new_tool(params: dict, context: ToolContext) -> str:
    param1 = params["param1"]
    # Do something
    return f"Result: {result}"
```

3. Register in tool dispatcher

## Git Workflow

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes
3. Run tests: `pytest`
4. Commit with clear message
5. Push and create PR

### Commit Messages

```
feat: Add new TTS provider
fix: Resolve memory leak in chain loading
docs: Update API documentation
refactor: Simplify key derivation
test: Add tests for relationship decay
```

## Release Process

1. Update version in:
   - `qubes-gui/src-tauri/tauri.conf.json`
   - `qubes-gui/package.json`

2. Update changelog

3. Create tag: `git tag v0.x.x`

4. Push tag: `git push origin v0.x.x`

5. GitHub Actions builds and publishes release

## Debugging

### Python Logging

```python
from utils.logging import get_logger
logger = get_logger(__name__)

logger.debug("Detailed info", extra={"key": "value"})
logger.info("General info")
logger.error("Error occurred", exc_info=True)
```

### Tauri DevTools

Press `F12` in development mode to open DevTools.

### Rust Logging

```rust
log::debug!("Debug message");
log::info!("Info message");
log::error!("Error: {}", err);
```

## Common Issues

### "Module not found"
Ensure virtual environment is activated and dependencies installed.

### "Tauri build fails"
- Check Rust is installed: `rustc --version`
- Update Rust: `rustup update`
- Clean build: `cargo clean`

### "Python backend not starting"
- Check Python version: `python --version` (need 3.11+)
- Check all dependencies installed
- Look for import errors in console

## Getting Help

- GitHub Issues: [github.com/bit-faced/Qubes/issues](https://github.com/bit-faced/Qubes/issues)
- Documentation: [docs/](.)
