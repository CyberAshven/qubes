# -*- mode: python ; coding: utf-8 -*-

import os
import sys

extra_binaries = []

# numpy.libs: OpenBLAS, gfortran, quadmath shared libraries required by
# numpy._core._multiarray_umath.so. Without these, numpy.__config__ import
# fails with misleading "import from source directory" error.
site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages') if sys.platform == 'win32' \
    else os.path.join(sys.prefix, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
numpy_libs_dir = os.path.join(site_packages, 'numpy.libs')
if os.path.isdir(numpy_libs_dir):
    for lib_file in os.listdir(numpy_libs_dir):
        lib_path = os.path.join(numpy_libs_dir, lib_file)
        if os.path.isfile(lib_path) and ('.so' in lib_file or '.dll' in lib_file):
            extra_binaries.append((lib_path, 'numpy.libs'))


a = Analysis(
    ['../../gui_bridge.py'],
    pathex=[],
    binaries=extra_binaries,
    datas=[],
    hiddenimports=[
        # Sidecar server
        'sidecar_server',
        # Games
        'chess',
        # Crypto & Blockchain
        'bitcash', 'bitcash._ripemd160',
        'coincurve', 'coincurve._cffi_backend',
        'cffi', '_cffi_backend',
        'cryptography', 'ecdsa', 'base58',
        # Networking
        'requests', 'websockets', 'httpx', 'aiohttp',
        # Data & Serialization (numpy 2.x needs explicit _core imports)
        'numpy', 'numpy.__config__', 'numpy._core', 'numpy._core._multiarray_umath',
        'PIL', 'fitz', 'pydantic', 'yaml',
        # Audio/TTS
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
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
