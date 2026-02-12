# -*- mode: python ; coding: utf-8 -*-
# Heavy build spec: PyInstaller --onedir with torch, kokoro, sentence-transformers
# Used by: scripts/build-heavy-linux.sh, .github/workflows/build-heavy.yml

import os
import sys

# Find site-packages for data collection
site_packages = None
for p in sys.path:
    if 'site-packages' in p and os.path.isdir(p):
        site_packages = p
        break

# Collect data directories that PyInstaller misses
datas = []
if site_packages:
    # espeakng_loader: bundled espeak-ng for Kokoro phonemizer
    espeak_dir = os.path.join(site_packages, 'espeakng_loader')
    if os.path.isdir(espeak_dir):
        datas.append((espeak_dir, 'espeakng_loader'))

    # unidic_lite: Japanese morphological dictionary for Kokoro
    unidic_dir = os.path.join(site_packages, 'unidic_lite')
    if os.path.isdir(unidic_dir):
        datas.append((unidic_dir, 'unidic_lite'))

    # pypinyin_dict: Chinese pinyin data for Kokoro
    pypinyin_dir = os.path.join(site_packages, 'pypinyin_dict')
    if os.path.isdir(pypinyin_dir):
        datas.append((pypinyin_dir, 'pypinyin_dict'))

    # misaki: phonemizer data files
    misaki_dir = os.path.join(site_packages, 'misaki')
    if os.path.isdir(misaki_dir):
        datas.append((misaki_dir, 'misaki'))


a = Analysis(
    ['../../gui_bridge.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Games
        'chess',
        # Crypto & Blockchain
        'bitcash', 'bitcash._ripemd160',
        'coincurve', 'coincurve._cffi_backend',
        'cffi', '_cffi_backend',
        'cryptography', 'ecdsa', 'base58',
        # Networking
        'requests', 'websockets', 'httpx', 'aiohttp',
        # Data & Serialization
        'numpy', 'PIL', 'fitz', 'pydantic', 'yaml',
        # Audio/TTS (light)
        'pyaudio', 'sounddevice', 'pydub', 'soundfile',
        'elevenlabs', 'huggingface_hub',
        # AI Providers
        'openai', 'anthropic', 'google.genai', 'google.cloud.texttospeech',
        # System & Logging
        'pytz', 'colorama', 'bs4', 'structlog', 'dotenv', 'psutil',
        # Resilience & Monitoring
        'tenacity', 'prometheus_client', 'pybreaker',
        # Server
        'fastapi', 'uvicorn',
        # === HEAVY-ONLY HIDDEN IMPORTS ===
        # PyTorch
        'torch', 'torch._C', 'torch.cuda', 'torch.backends',
        'torch.backends.cudnn', 'torch.nn', 'torch.nn.functional',
        'torch.utils', 'torch.utils.data',
        'torchaudio',
        # Kokoro TTS
        'kokoro', 'kokoro.pipeline', 'kokoro.model',
        'kokoro.istftnet', 'kokoro.modules', 'kokoro.custom_stft',
        # Misaki phonemizer
        'misaki', 'misaki.en', 'misaki.espeak',
        # Sentence Transformers & FAISS
        'sentence_transformers', 'faiss',
        # Transformers ecosystem
        'transformers', 'transformers.models',
        'accelerate', 'safetensors', 'tokenizers',
        # Qwen3-TTS (voice design + cloning; models download on demand via UI)
        'qwen_tts',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim torch bloat (~500MB savings) - we only need inference, not training/compiling
        'torch.testing',
        'torch._inductor',
        'torch._dynamo',
        'torch._functorch',
        'torch.distributed',
        'torch._export',
        'torch.ao',
        'torch.profiler',
        'torch.onnx',
        'torch.optim',
        'torch.autograd.profiler',
        'torch.futures',
        'torch.contrib',
        'torch.multiprocessing',
        # Trim transformers bloat - we only need the models we use
        'transformers.models.whisper',
        'transformers.models.llama',
        'transformers.models.gpt2',
        'transformers.models.t5',
        'transformers.models.bart',
        'transformers.models.roberta',
        'transformers.models.wav2vec2',
        'transformers.models.vit',
        'transformers.models.clip',
        'transformers.models.stable_diffusion',
        # Large unused packages
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
        'notebook',
        'pytest',
        'unittest',
        'tkinter',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # --onedir: binaries go to COLLECT, not EXE
    name='qubes-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='qubes-backend',
)
