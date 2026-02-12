# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\..\\gui_bridge.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
