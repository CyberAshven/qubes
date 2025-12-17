"""
Qubes - Sovereign Multi-Agent AI Platform
Setup configuration for CLI installation
"""

from setuptools import setup, find_packages

setup(
    name="qubes",
    version="1.0.0-alpha",
    description="Sovereign Multi-Agent AI Platform",
    author="bit_faced",
    author_email="qubes@blockchain.com",
    packages=find_packages(),
    install_requires=[
        # Core dependencies
        "pydantic>=2.5.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",

        # Cryptography
        "cryptography>=41.0.0",
        "ecdsa>=0.18.0",

        # Storage
        "lmdb>=1.4.1",
        "msgpack>=1.0.7",

        # Logging & Observability
        "structlog>=24.1.0",
        "opentelemetry-api>=1.22.0",
        "opentelemetry-sdk>=1.22.0",
        "prometheus-client>=0.19.0",

        # Error Handling & Resilience
        "tenacity>=8.2.3",
        "pybreaker>=1.0.1",

        # System Monitoring
        "psutil>=5.9.6",

        # AI/LLM Integration
        "openai>=1.6.0",
        "anthropic>=0.8.0",
        "google-generativeai>=0.3.0",
        "faiss-cpu>=1.7.4",
        "sentence-transformers>=2.2.2",

        # P2P Networking
        "p2pclient>=0.1.1",
        "multiaddr>=0.0.9",

        # Blockchain
        "bitcash>=1.1.0",
        "ipfshttpclient>=0.7.0",
        "aiohttp>=3.8.0",

        # Health Checks & Orchestrator
        "fastapi>=0.115.0",
        "uvicorn>=0.32.0",

        # Audio Integration
        "sounddevice>=0.4.6",
        "pyaudio>=0.2.14",
        "pydub>=0.25.1",
        "elevenlabs>=0.2.27",
        "deepgram-sdk>=3.0.0",
        "webrtcvad>=2.0.10",

        # CLI & UI
        "typer>=0.9.0",
        "rich>=13.7.0",
        "click>=8.1.7",
    ],
    entry_points={
        "console_scripts": [
            "qubes=cli.main:app",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
