#!/bin/bash
# =============================================================================
# Qubes Heavy Linux Bundle Builder
# =============================================================================
# Builds a self-contained directory with ALL dependencies, pre-downloaded
# models (Kokoro TTS, sentence-transformers, deepseek-r1:8b), and bundled
# Ollama. The output is a tar.gz that works on any Linux x86_64 machine.
#
# Usage: ./scripts/build-heavy-linux.sh [--skip-models] [--skip-tauri] [--ollama-model MODEL]
#
# Requirements:
#   - Python 3.11+ with venv support
#   - Node.js 20+ and npm
#   - Rust toolchain (for Tauri build)
#   - ~25 GB free disk space
#   - Internet connection (for downloading models)
# =============================================================================

set -euo pipefail

# Parse arguments
SKIP_MODELS=false
SKIP_TAURI=false
OLLAMA_MODEL="deepseek-r1:8b"
OLLAMA_VERSION="0.4.7"

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-models) SKIP_MODELS=true; shift ;;
        --skip-tauri) SKIP_TAURI=true; shift ;;
        --ollama-model) OLLAMA_MODEL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/dist-heavy"
DIST_DIR="$BUILD_DIR/Qubes"
HEAVY_VENV="$BUILD_DIR/heavy-venv"
TARGET_TRIPLE="x86_64-unknown-linux-gnu"

echo "============================================="
echo " Qubes Heavy Linux Bundle Builder"
echo "============================================="
echo "Project root:  $PROJECT_ROOT"
echo "Build dir:     $BUILD_DIR"
echo "Ollama model:  $OLLAMA_MODEL"
echo "Skip models:   $SKIP_MODELS"
echo "Skip Tauri:    $SKIP_TAURI"
echo ""

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
if [ "$SKIP_TAURI" = false ]; then
    command -v npm >/dev/null 2>&1 || { echo "ERROR: npm not found"; exit 1; }
    command -v cargo >/dev/null 2>&1 || { echo "ERROR: cargo not found"; exit 1; }
fi

# Clean previous build
echo ">>> Cleaning previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# =============================================================================
# Step 1: Create temporary venv with heavy dependencies
# =============================================================================
echo ""
echo ">>> Step 1/8: Installing Python heavy dependencies..."
python3 -m venv "$HEAVY_VENV"
source "$HEAVY_VENV/bin/activate"
pip install --upgrade pip wheel setuptools 2>&1 | tail -1
# Install CUDA torch for GPU acceleration (local heavy build)
pip install torch torchaudio --extra-index-url https://download.pytorch.org/whl/cu124 2>&1 | tail -3
pip install -r "$PROJECT_ROOT/requirements-heavy.txt" 2>&1 | tail -5
echo "    Python deps installed."

# =============================================================================
# Step 2: Build Python backend with PyInstaller --onedir
# =============================================================================
echo ""
echo ">>> Step 2/8: Building Python backend (PyInstaller --onedir)..."
cd "$PROJECT_ROOT/qubes-gui/src-tauri"
pyinstaller "$PROJECT_ROOT/qubes-gui/src-tauri/qubes-backend-heavy.spec" \
    --distpath "$BUILD_DIR/pyinstaller-out" \
    --workpath "$BUILD_DIR/pyinstaller-work" \
    --noconfirm 2>&1 | tail -5

# Copy --onedir output to bundle
cp -r "$BUILD_DIR/pyinstaller-out/qubes-backend" "$DIST_DIR/qubes-backend"
chmod +x "$DIST_DIR/qubes-backend/qubes-backend"

# Ensure numpy.libs/ is present (OpenBLAS, gfortran — required by numpy._core._multiarray_umath)
INTERNAL="$DIST_DIR/qubes-backend/_internal"
if [ ! -d "$INTERNAL/numpy.libs" ] || [ -z "$(ls -A "$INTERNAL/numpy.libs" 2>/dev/null)" ]; then
    echo "    Copying numpy.libs (OpenBLAS) into bundle..."
    NUMPY_LIBS="$HEAVY_VENV/lib/python3.*/site-packages/numpy.libs"
    NUMPY_LIBS_DIR=$(ls -d $NUMPY_LIBS 2>/dev/null | head -1)
    if [ -d "$NUMPY_LIBS_DIR" ]; then
        mkdir -p "$INTERNAL/numpy.libs"
        cp -v "$NUMPY_LIBS_DIR"/*.so* "$INTERNAL/numpy.libs/" 2>/dev/null || true
    fi
fi
echo "    numpy.libs: $(ls "$INTERNAL/numpy.libs/" 2>/dev/null | wc -l) files"
echo "    Backend built: $(du -sh "$DIST_DIR/qubes-backend" | cut -f1)"

# =============================================================================
# Step 3: Build Tauri frontend
# =============================================================================
if [ "$SKIP_TAURI" = false ]; then
    echo ""
    echo ">>> Step 3/8: Building Tauri frontend..."
    cd "$PROJECT_ROOT/qubes-gui"

    # Place dummy sidecar to satisfy Tauri's build check
    mkdir -p src-tauri/binaries
    cp "$DIST_DIR/qubes-backend/qubes-backend" \
       "src-tauri/binaries/qubes-backend-$TARGET_TRIPLE"

    npm ci 2>&1 | tail -1
    npm run tauri build -- --target "$TARGET_TRIPLE" 2>&1 | tail -5

    # Copy Tauri binary
    cp "src-tauri/target/$TARGET_TRIPLE/release/qubes-gui" "$DIST_DIR/Qubes"
    chmod +x "$DIST_DIR/Qubes"
    echo "    Tauri built."
else
    echo ""
    echo ">>> Step 3/8: Skipping Tauri build (--skip-tauri)"
    # Use existing Tauri binary if available
    EXISTING_TAURI="$PROJECT_ROOT/qubes-gui/src-tauri/target/$TARGET_TRIPLE/release/qubes-gui"
    if [ -f "$EXISTING_TAURI" ]; then
        cp "$EXISTING_TAURI" "$DIST_DIR/Qubes"
        chmod +x "$DIST_DIR/Qubes"
        echo "    Using existing Tauri binary."
    else
        echo "    WARNING: No Tauri binary found. Bundle will be incomplete."
        touch "$DIST_DIR/Qubes"
    fi
fi

# =============================================================================
# Step 4: Download and bundle Ollama binary
# =============================================================================
echo ""
echo ">>> Step 4/8: Downloading Ollama v${OLLAMA_VERSION}..."
mkdir -p "$DIST_DIR/ollama"
OLLAMA_TGZ="/tmp/ollama-${OLLAMA_VERSION}.tgz"

if [ ! -f "$OLLAMA_TGZ" ]; then
    curl -L --progress-bar \
        "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tgz" \
        -o "$OLLAMA_TGZ"
fi

# Extract Ollama binary
OLLAMA_TMP="/tmp/ollama-extract-$$"
mkdir -p "$OLLAMA_TMP"
tar -xzf "$OLLAMA_TGZ" -C "$OLLAMA_TMP"

# Handle both directory structures (bin/ or flat)
if [ -d "$OLLAMA_TMP/bin" ]; then
    cp "$OLLAMA_TMP/bin/"* "$DIST_DIR/ollama/"
else
    cp "$OLLAMA_TMP/ollama" "$DIST_DIR/ollama/"
fi
chmod +x "$DIST_DIR/ollama/"*
rm -rf "$OLLAMA_TMP"
echo "    Ollama bundled."

# =============================================================================
# Step 5: Pre-pull Ollama model
# =============================================================================
if [ "$SKIP_MODELS" = false ]; then
    echo ""
    echo ">>> Step 5/8: Pulling Ollama model: $OLLAMA_MODEL ..."
    export OLLAMA_MODELS="$DIST_DIR/models/ollama"
    mkdir -p "$OLLAMA_MODELS"

    # Start temporary Ollama instance
    "$DIST_DIR/ollama/ollama" serve &
    OLLAMA_PID=$!

    # Wait for Ollama to be ready
    for i in $(seq 1 30); do
        if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done

    # Pull the model
    "$DIST_DIR/ollama/ollama" pull "$OLLAMA_MODEL"

    # Stop Ollama
    kill $OLLAMA_PID 2>/dev/null || true
    wait $OLLAMA_PID 2>/dev/null || true
    echo "    Model pulled: $(du -sh "$OLLAMA_MODELS" | cut -f1)"
else
    echo ""
    echo ">>> Step 5/8: Skipping Ollama model download (--skip-models)"
    mkdir -p "$DIST_DIR/models/ollama"
fi

# =============================================================================
# Step 6: Pre-download HuggingFace models
# =============================================================================
if [ "$SKIP_MODELS" = false ]; then
    echo ""
    echo ">>> Step 6/8: Downloading HuggingFace models..."
    HF_MODELS_DIR="$DIST_DIR/models/huggingface"
    mkdir -p "$HF_MODELS_DIR"

    HF_HOME="$HF_MODELS_DIR" python3 -c "
from huggingface_hub import snapshot_download
import os
os.environ['HF_HOME'] = '$HF_MODELS_DIR'

print('  Downloading hexgrad/Kokoro-82M...')
snapshot_download('hexgrad/Kokoro-82M', cache_dir='$HF_MODELS_DIR/hub')

print('  Downloading sentence-transformers/all-MiniLM-L6-v2...')
snapshot_download('sentence-transformers/all-MiniLM-L6-v2', cache_dir='$HF_MODELS_DIR/hub')

print('  Done.')
"
    echo "    HF models downloaded: $(du -sh "$HF_MODELS_DIR" | cut -f1)"
else
    echo ""
    echo ">>> Step 6/8: Skipping HuggingFace model downloads (--skip-models)"
    mkdir -p "$DIST_DIR/models/huggingface"
fi

# =============================================================================
# Step 7: Generate launcher, installer, config, README
# =============================================================================
echo ""
echo ">>> Step 7/8: Generating bundle files..."

# Copy icon for desktop entry
mkdir -p "$DIST_DIR/resources"
if [ -f "$PROJECT_ROOT/qubes-gui/src-tauri/icons/128x128.png" ]; then
    cp "$PROJECT_ROOT/qubes-gui/src-tauri/icons/128x128.png" "$DIST_DIR/resources/icon.png"
fi

# launch.sh
cat > "$DIST_DIR/launch.sh" << 'LAUNCH_EOF'
#!/bin/bash
# Qubes Heavy Bundle Launcher
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Point HuggingFace to bundled models
if [ -d "$SCRIPT_DIR/models/huggingface" ]; then
    export HF_HOME="$SCRIPT_DIR/models/huggingface"
fi

# Point Ollama to bundled models
if [ -d "$SCRIPT_DIR/models/ollama" ]; then
    export OLLAMA_MODELS="$SCRIPT_DIR/models/ollama"
fi

# Add bundled CUDA libraries to LD_LIBRARY_PATH
INTERNAL_DIR="$SCRIPT_DIR/qubes-backend/_internal"
if [ -d "$INTERNAL_DIR" ]; then
    NVIDIA_PATHS=$(find "$INTERNAL_DIR" -path "*/nvidia/*/lib" -type d 2>/dev/null | tr '\n' ':')
    if [ -n "$NVIDIA_PATHS" ]; then
        export LD_LIBRARY_PATH="${NVIDIA_PATHS}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    fi
    export LD_LIBRARY_PATH="$INTERNAL_DIR:${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

exec "$SCRIPT_DIR/Qubes" "$@"
LAUNCH_EOF
chmod +x "$DIST_DIR/launch.sh"

# install.sh
cat > "$DIST_DIR/install.sh" << 'INSTALL_EOF'
#!/bin/bash
# Qubes Heavy Bundle Installer
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_FILE="$HOME/.local/share/applications/qubes.desktop"

echo "=== Qubes Installation ==="
echo "Location: $SCRIPT_DIR"
echo ""

# Create desktop entry
mkdir -p "$HOME/.local/share/applications"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Qubes
Comment=Sovereign AI Agents
Exec=$SCRIPT_DIR/launch.sh
Icon=$SCRIPT_DIR/resources/icon.png
Terminal=false
Type=Application
Categories=Utility;
StartupWMClass=qubes
EOF
echo "Desktop entry created: $DESKTOP_FILE"

# Offer PATH symlink
read -p "Add 'qubes' command to PATH (~/.local/bin)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    mkdir -p "$HOME/.local/bin"
    ln -sf "$SCRIPT_DIR/launch.sh" "$HOME/.local/bin/qubes"
    echo "Symlink: ~/.local/bin/qubes"
fi

echo ""
echo "Done! Launch from app menu or: $SCRIPT_DIR/launch.sh"
INSTALL_EOF
chmod +x "$DIST_DIR/install.sh"

# qubes-config.json
cat > "$DIST_DIR/qubes-config.json" << CONFIG_EOF
{
    "version": "1.0.0",
    "variant": "heavy",
    "bundled_models": {
        "ollama": ["$OLLAMA_MODEL"],
        "huggingface": ["hexgrad/Kokoro-82M", "sentence-transformers/all-MiniLM-L6-v2"]
    }
}
CONFIG_EOF

# README.txt
cat > "$DIST_DIR/README.txt" << README_EOF
Qubes - Sovereign AI Agents (Heavy Bundle)
===========================================

Everything included out of the box:
  - Kokoro TTS (82M param local text-to-speech, 54 voices)
  - Semantic search (all-MiniLM-L6-v2 embeddings)
  - DeepSeek R1 8B (local LLM via bundled Ollama)
  - PyTorch with CUDA support (NVIDIA GPU acceleration)

Getting Started:
  1. Extract: tar -xzf Qubes-Linux-Heavy.tar.gz
  2. Install: cd Qubes && ./install.sh
  3. Launch: ./launch.sh

Requirements:
  - Ubuntu 20.04+ / Debian 11+ / Fedora 35+
  - 16 GB RAM minimum (32 GB recommended for local LLM)
  - NVIDIA GPU with 8+ GB VRAM (optional, falls back to CPU)
  - ~15 GB disk space
README_EOF

echo "    Bundle files generated."

# =============================================================================
# Step 8: Package as tar.gz
# =============================================================================
echo ""
echo ">>> Step 8/8: Creating archive..."
cd "$BUILD_DIR"
tar -czf "$PROJECT_ROOT/Qubes-Linux-Heavy.tar.gz" Qubes/

deactivate 2>/dev/null || true

echo ""
echo "============================================="
echo " Build Complete!"
echo "============================================="
echo "Archive:      $PROJECT_ROOT/Qubes-Linux-Heavy.tar.gz"
echo "Size:         $(du -sh "$PROJECT_ROOT/Qubes-Linux-Heavy.tar.gz" | cut -f1)"
echo "Uncompressed: $(du -sh "$DIST_DIR" | cut -f1)"
echo ""
echo "To test: tar -xzf Qubes-Linux-Heavy.tar.gz && cd Qubes && ./launch.sh"
