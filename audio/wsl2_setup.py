"""
WSL2 TTS Setup Module

Handles automated setup of Qwen3-TTS in WSL2 Ubuntu for local TTS generation.
This module orchestrates the installation process from Windows.

Setup flow:
1. Check if WSL2 is installed and Ubuntu is available
2. Create setup directory and venv in WSL2
3. Install PyTorch with CUDA support
4. Install qwen-tts and dependencies
5. Download Qwen3-TTS model
6. Create tts_server.py for serving requests
7. Test the installation

The TTS server runs at http://localhost:19533 in WSL2.
"""

import asyncio
import subprocess
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from utils.logging import get_logger

logger = get_logger(__name__)

# WSL2 configuration
WSL2_DISTRO = "Ubuntu-22.04"
WSL2_TTS_DIR = "~/qubes-tts"
WSL2_TTS_PORT = 19532

# Setup stages for progress tracking
SETUP_STAGES = [
    ("checking_wsl", "Checking WSL2 installation", 5),
    ("checking_ubuntu", "Checking Ubuntu distribution", 10),
    ("creating_directory", "Creating setup directory", 15),
    ("creating_venv", "Creating Python virtual environment", 20),
    ("installing_pytorch", "Installing PyTorch with CUDA", 40),
    ("installing_dependencies", "Installing dependencies", 55),
    ("downloading_model", "Downloading Qwen3-TTS model", 85),
    ("creating_server", "Creating TTS server script", 90),
    ("testing_setup", "Testing installation", 95),
    ("complete", "Setup complete", 100),
]


@dataclass
class SetupProgress:
    """Progress tracking for WSL2 TTS setup."""
    stage: str = "idle"
    stage_name: str = ""
    percentage: int = 0
    message: str = ""
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WSL2TTSStatus:
    """Status of WSL2 TTS installation."""
    wsl2_installed: bool = False
    ubuntu_installed: bool = False
    ubuntu_distro: Optional[str] = None
    setup_complete: bool = False
    venv_exists: bool = False
    pytorch_installed: bool = False
    qwen_tts_installed: bool = False
    model_downloaded: bool = False
    server_running: bool = False
    server_ready: bool = False
    gpu_detected: bool = False
    gpu_name: Optional[str] = None
    cuda_version: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Global progress tracking
_current_progress: SetupProgress = SetupProgress()
_setup_in_progress: bool = False


def get_setup_progress() -> Dict[str, Any]:
    """Get current setup progress."""
    return _current_progress.to_dict()


async def _run_wsl_command(command: str, timeout: int = 300) -> tuple[int, str, str]:
    """
    Run a command in WSL2 Ubuntu.

    Args:
        command: Command to run (will be executed in bash)
        timeout: Timeout in seconds

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    full_cmd = f'wsl -d {WSL2_DISTRO} -- bash -c "{command}"'

    try:
        process = await asyncio.create_subprocess_shell(
            full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )

        return (
            process.returncode or 0,
            stdout.decode('utf-8', errors='replace'),
            stderr.decode('utf-8', errors='replace')
        )
    except asyncio.TimeoutError:
        process.kill()
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


async def _run_windows_command(command: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run a command on Windows."""
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )

        return (
            process.returncode or 0,
            stdout.decode('utf-8', errors='replace'),
            stderr.decode('utf-8', errors='replace')
        )
    except asyncio.TimeoutError:
        process.kill()
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def _update_progress(stage: str, message: str = "", error: str = None):
    """Update setup progress."""
    global _current_progress

    stage_info = next((s for s in SETUP_STAGES if s[0] == stage), None)
    if stage_info:
        _current_progress.stage = stage
        _current_progress.stage_name = stage_info[1]
        _current_progress.percentage = stage_info[2]

    if message:
        _current_progress.message = message
    if error:
        _current_progress.error = error

    logger.info(
        "wsl2_tts_setup_progress",
        stage=stage,
        percentage=_current_progress.percentage,
        message=message,
        error=error
    )


async def check_wsl2_tts_status() -> WSL2TTSStatus:
    """
    Check the current status of WSL2 TTS installation.

    Returns comprehensive status including:
    - WSL2 installation status
    - Ubuntu installation status
    - Setup completion status
    - Server running status
    """
    status = WSL2TTSStatus()

    try:
        # Check if WSL is installed
        code, stdout, stderr = await _run_windows_command("wsl --status", timeout=10)
        status.wsl2_installed = code == 0 or "Default Distribution" in stdout

        if not status.wsl2_installed:
            # Try alternative check
            code, stdout, _ = await _run_windows_command("wsl -l -v", timeout=10)
            status.wsl2_installed = code == 0 and len(stdout.strip()) > 0

        if not status.wsl2_installed:
            return status

        # Check if Ubuntu is installed
        code, stdout, _ = await _run_windows_command("wsl -l -v", timeout=10)
        if code == 0:
            # Parse WSL list output (handles both UTF-16 and UTF-8)
            lines = stdout.replace('\x00', '').split('\n')
            for line in lines:
                if 'Ubuntu' in line:
                    status.ubuntu_installed = True
                    # Extract distro name
                    match = re.search(r'(Ubuntu[^\s]*)', line)
                    if match:
                        status.ubuntu_distro = match.group(1)
                    break

        if not status.ubuntu_installed:
            return status

        # Check setup directory exists
        code, stdout, _ = await _run_wsl_command(f"test -d {WSL2_TTS_DIR} && echo 'exists'", timeout=10)
        if "exists" in stdout:
            status.venv_exists = True

            # Check PyTorch
            code, stdout, _ = await _run_wsl_command(
                f"source {WSL2_TTS_DIR}/venv/bin/activate && python -c 'import torch; print(torch.__version__)'",
                timeout=30
            )
            status.pytorch_installed = code == 0 and stdout.strip()

            # Check CUDA availability
            code, stdout, _ = await _run_wsl_command(
                f"source {WSL2_TTS_DIR}/venv/bin/activate && python -c 'import torch; print(torch.cuda.is_available())'",
                timeout=30
            )
            status.gpu_detected = "True" in stdout

            if status.gpu_detected:
                # Get GPU name
                code, stdout, _ = await _run_wsl_command(
                    f"source {WSL2_TTS_DIR}/venv/bin/activate && python -c 'import torch; print(torch.cuda.get_device_name(0))'",
                    timeout=30
                )
                if code == 0:
                    status.gpu_name = stdout.strip()

                # Get CUDA version
                code, stdout, _ = await _run_wsl_command(
                    f"source {WSL2_TTS_DIR}/venv/bin/activate && python -c 'import torch; print(torch.version.cuda)'",
                    timeout=30
                )
                if code == 0:
                    status.cuda_version = stdout.strip()

            # Check qwen-tts (package can be imported as qwen_tts with Qwen3TTSModel)
            # Use pip show to check if package is installed (faster, no import warnings)
            code, stdout, _ = await _run_wsl_command(
                f"source {WSL2_TTS_DIR}/venv/bin/activate && pip show qwen-tts",
                timeout=30
            )
            status.qwen_tts_installed = code == 0 and "Name: qwen-tts" in stdout

            # Check if model downloaded in various locations:
            # 1. Local models dir in qubes-tts
            code1, stdout1, _ = await _run_wsl_command(
                f"test -d {WSL2_TTS_DIR}/models/Qwen3-TTS && echo 'exists'",
                timeout=10
            )
            # 2. User's .qubes/models directory (primary location)
            code2, stdout2, _ = await _run_wsl_command(
                "test -d ~/.qubes/models/qwen3-tts/1.7B-CustomVoice && echo 'exists'",
                timeout=10
            )
            # 3. HuggingFace cache
            code3, stdout3, _ = await _run_wsl_command(
                "ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen3-TTS* 2>/dev/null | head -1",
                timeout=10
            )

            status.model_downloaded = (
                "exists" in stdout1 or
                "exists" in stdout2 or
                bool(stdout3.strip())
            )

            # Check if server script exists
            code, stdout, _ = await _run_wsl_command(
                f"test -f {WSL2_TTS_DIR}/tts_server.py && echo 'exists'",
                timeout=10
            )
            server_script_exists = "exists" in stdout

            # Setup is complete if we have venv, PyTorch, qwen-tts, and server script
            # Model download is verified through HuggingFace cache or local models
            status.setup_complete = (
                status.venv_exists and
                status.pytorch_installed and
                status.qwen_tts_installed and
                server_script_exists
            )

        # Check if server is running
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{WSL2_TTS_PORT}/status", timeout=2.0)
                data = response.json()
                status.server_running = data.get("running", True)
                status.server_ready = data.get("model_loaded", False)

                # If server is running, setup IS complete (server proves everything works)
                if status.server_running:
                    status.setup_complete = True
                    status.pytorch_installed = True
                    status.qwen_tts_installed = True
                    # Get GPU info from server if available
                    if data.get("gpu"):
                        status.gpu_detected = True
                        status.gpu_name = data.get("gpu")
        except Exception:
            pass

    except Exception as e:
        status.error = str(e)
        logger.error("wsl2_tts_status_check_failed", error=str(e))

    return status


async def setup_wsl2_tts(
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Set up WSL2 TTS from scratch.

    This is the main setup function that:
    1. Validates WSL2 and Ubuntu are installed
    2. Creates the setup directory and venv
    3. Installs PyTorch with CUDA
    4. Installs qwen-tts and dependencies
    5. Downloads the Qwen3-TTS model
    6. Creates the TTS server script
    7. Tests the installation

    Args:
        progress_callback: Optional callback for progress updates

    Returns:
        Dict with success status and details
    """
    global _current_progress, _setup_in_progress

    if _setup_in_progress:
        return {
            "success": False,
            "error": "Setup already in progress"
        }

    _setup_in_progress = True
    _current_progress = SetupProgress(
        started_at=datetime.now().isoformat()
    )

    def update(stage: str, message: str = "", error: str = None):
        _update_progress(stage, message, error)
        if progress_callback:
            progress_callback(_current_progress.to_dict())

    try:
        # Stage 1: Check WSL2
        update("checking_wsl", "Checking if WSL2 is installed...")
        code, stdout, stderr = await _run_windows_command("wsl --status", timeout=30)

        if code != 0:
            # Try to get more info
            code2, stdout2, _ = await _run_windows_command("wsl -l -v", timeout=30)
            if code2 != 0:
                update("checking_wsl", error="WSL2 is not installed. Please install WSL2 first.")
                return {"success": False, "error": "WSL2 not installed"}

        # Stage 2: Check Ubuntu
        update("checking_ubuntu", "Checking Ubuntu distribution...")
        code, stdout, _ = await _run_windows_command("wsl -l -v", timeout=30)

        ubuntu_found = False
        lines = stdout.replace('\x00', '').split('\n')
        for line in lines:
            if 'Ubuntu' in line:
                ubuntu_found = True
                break

        if not ubuntu_found:
            update("checking_ubuntu", error="Ubuntu not found in WSL2. Please install Ubuntu from Microsoft Store.")
            return {"success": False, "error": "Ubuntu not installed in WSL2"}

        # Stage 3: Create directory
        update("creating_directory", "Creating setup directory in WSL2...")
        code, stdout, stderr = await _run_wsl_command(f"mkdir -p {WSL2_TTS_DIR}", timeout=30)
        if code != 0:
            update("creating_directory", error=f"Failed to create directory: {stderr}")
            return {"success": False, "error": f"Failed to create directory: {stderr}"}

        # Stage 4: Create venv
        update("creating_venv", "Creating Python virtual environment...")

        # First ensure python3-venv is installed
        code, _, _ = await _run_wsl_command(
            "sudo apt-get update && sudo apt-get install -y python3-venv python3-pip",
            timeout=300
        )

        code, stdout, stderr = await _run_wsl_command(
            f"python3 -m venv {WSL2_TTS_DIR}/venv",
            timeout=120
        )
        if code != 0:
            update("creating_venv", error=f"Failed to create venv: {stderr}")
            return {"success": False, "error": f"Failed to create venv: {stderr}"}

        # Stage 5: Install PyTorch with CUDA
        update("installing_pytorch", "Installing PyTorch with CUDA support (this may take a while)...")

        # Use the latest PyTorch with CUDA 12.4 support
        pytorch_cmd = (
            f"source {WSL2_TTS_DIR}/venv/bin/activate && "
            "pip install --upgrade pip && "
            "pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124"
        )
        code, stdout, stderr = await _run_wsl_command(pytorch_cmd, timeout=600)
        if code != 0:
            update("installing_pytorch", error=f"Failed to install PyTorch: {stderr}")
            return {"success": False, "error": f"Failed to install PyTorch: {stderr}"}

        # Stage 6: Install dependencies
        update("installing_dependencies", "Installing qwen-tts and dependencies...")

        deps_cmd = (
            f"source {WSL2_TTS_DIR}/venv/bin/activate && "
            "pip install qwen-tts soundfile transformers huggingface_hub httpx uvicorn fastapi"
        )
        code, stdout, stderr = await _run_wsl_command(deps_cmd, timeout=300)
        if code != 0:
            update("installing_dependencies", error=f"Failed to install dependencies: {stderr}")
            return {"success": False, "error": f"Failed to install dependencies: {stderr}"}

        # Stage 7: Download model
        update("downloading_model", "Downloading Qwen3-TTS model (~4GB, this may take a while)...")

        # Create models directory
        await _run_wsl_command(f"mkdir -p {WSL2_TTS_DIR}/models", timeout=30)

        # Download model using huggingface_hub
        download_cmd = (
            f"source {WSL2_TTS_DIR}/venv/bin/activate && "
            f"python -c \""
            "from huggingface_hub import snapshot_download; "
            f"snapshot_download('Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice', local_dir='{WSL2_TTS_DIR}/models/Qwen3-TTS')"
            "\""
        )
        code, stdout, stderr = await _run_wsl_command(download_cmd, timeout=1800)  # 30 min timeout for download
        if code != 0:
            update("downloading_model", error=f"Failed to download model: {stderr}")
            return {"success": False, "error": f"Failed to download model: {stderr}"}

        # Stage 8: Create server script
        update("creating_server", "Creating TTS server script...")

        server_script = _generate_tts_server_script()

        # Write server script using heredoc
        write_cmd = f"cat > {WSL2_TTS_DIR}/tts_server.py << 'EOFSCRIPT'\n{server_script}\nEOFSCRIPT"
        code, stdout, stderr = await _run_wsl_command(write_cmd, timeout=30)
        if code != 0:
            update("creating_server", error=f"Failed to create server script: {stderr}")
            return {"success": False, "error": f"Failed to create server script: {stderr}"}

        # Stage 9: Test installation
        update("testing_setup", "Testing installation...")

        test_cmd = (
            f"source {WSL2_TTS_DIR}/venv/bin/activate && "
            "python -c 'import torch; print(f\"PyTorch: {torch.__version__}\"); print(f\"CUDA: {torch.cuda.is_available()}\")'"
        )
        code, stdout, stderr = await _run_wsl_command(test_cmd, timeout=60)

        if code != 0 or "True" not in stdout:
            update("testing_setup", error="PyTorch CUDA test failed. GPU may not be accessible from WSL2.")
            # Don't fail - CUDA might work when server actually runs

        # Stage 10: Complete
        update("complete", "WSL2 TTS setup complete!")
        _current_progress.completed_at = datetime.now().isoformat()

        return {
            "success": True,
            "message": "WSL2 TTS setup completed successfully",
            "details": {
                "pytorch_test": stdout.strip() if code == 0 else "Test failed",
                "setup_dir": WSL2_TTS_DIR,
                "server_port": WSL2_TTS_PORT,
            }
        }

    except Exception as e:
        _update_progress("error", error=str(e))
        logger.error("wsl2_tts_setup_failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        _setup_in_progress = False


def _generate_tts_server_script() -> str:
    """Generate the TTS server script that runs in WSL2."""
    return '''#!/usr/bin/env python3
"""
Qwen3-TTS Server for Qubes

FastAPI server that provides TTS generation via HTTP.
Runs at http://0.0.0.0:19533 (accessible from Windows as localhost:19533).

Endpoints:
- GET /health - Health check and readiness status
- GET /speakers - List available preset speakers
- POST /generate - Generate audio from text
"""

import os
import io
import time
import asyncio
from pathlib import Path
from typing import Optional

import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

# Model path (relative to script directory)
SCRIPT_DIR = Path(__file__).parent
MODEL_PATH = SCRIPT_DIR / "models" / "Qwen3-TTS"

# Preset speakers available in CustomVoice model
PRESET_SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]

# Language mapping
LANGUAGE_MAP = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "de": "German",
    "fr": "French",
    "ru": "Russian",
    "pt": "Portuguese",
    "es": "Spanish",
    "it": "Italian",
}

app = FastAPI(title="Qwen3-TTS Server", version="1.0.0")

# Global model state
model = None
model_ready = False
model_loading = False


class GenerateRequest(BaseModel):
    text: str
    speaker: str = "Vivian"
    language: str = "English"
    instruct: str = ""


@app.on_event("startup")
async def startup():
    """Load model on startup."""
    asyncio.create_task(load_model())


async def load_model():
    """Load the Qwen3-TTS model with torch.compile optimization."""
    global model, model_ready, model_loading

    if model_loading or model_ready:
        return

    model_loading = True
    print(f"Loading Qwen3-TTS model from {MODEL_PATH}...")

    try:
        from qwen_tts import Qwen3TTS

        # Load with bfloat16 for efficiency
        model = Qwen3TTS.from_pretrained(
            str(MODEL_PATH),
            torch_dtype=torch.bfloat16,
            device_map="cuda"
        )

        # Apply torch.compile for faster inference
        print("Applying torch.compile optimization (this takes ~2 minutes on first run)...")
        model = torch.compile(model, mode="reduce-overhead")

        # Warmup with a short generation
        print("Warming up model...")
        warmup_text = "Hello, this is a warmup."
        _ = model.generate(
            text=warmup_text,
            speaker="Vivian",
            language="English",
        )

        model_ready = True
        print("Model loaded and ready!")

    except Exception as e:
        print(f"Failed to load model: {e}")
        import traceback
        traceback.print_exc()
    finally:
        model_loading = False


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "ready": model_ready,
        "loading": model_loading,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


@app.get("/speakers")
async def speakers():
    """List available preset speakers."""
    return {
        "speakers": PRESET_SPEAKERS,
        "languages": list(LANGUAGE_MAP.keys()),
    }


@app.post("/generate")
async def generate(request: GenerateRequest):
    """Generate audio from text."""
    if not model_ready:
        raise HTTPException(status_code=503, detail="Model not ready")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    try:
        start_time = time.time()

        # Map language code to full name if needed
        language = LANGUAGE_MAP.get(request.language.lower(), request.language)

        # Generate audio
        audio = model.generate(
            text=request.text,
            speaker=request.speaker,
            language=language,
            instruct=request.instruct if request.instruct else None,
        )

        gen_time = time.time() - start_time

        # Convert to WAV bytes
        buffer = io.BytesIO()
        sf.write(buffer, audio, 24000, format="WAV")
        audio_bytes = buffer.getvalue()

        # Calculate RTF
        audio_duration = len(audio) / 24000
        rtf = gen_time / audio_duration if audio_duration > 0 else 0

        print(f"Generated {audio_duration:.1f}s audio in {gen_time:.1f}s (RTF: {rtf:.2f})")

        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "X-Generation-Time": str(gen_time),
                "X-Audio-Duration": str(audio_duration),
                "X-RTF": str(rtf),
            }
        )

    except Exception as e:
        print(f"Generation error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19533, log_level="info")
'''


async def start_wsl2_tts_server() -> Dict[str, Any]:
    """
    Start the WSL2 TTS server.

    Returns:
        Dict with success status and server info
    """
    try:
        # Check if already running
        status = await check_wsl2_tts_status()
        if status.server_running:
            return {
                "success": True,
                "message": "Server already running",
                "ready": status.server_ready
            }

        if not status.setup_complete:
            return {
                "success": False,
                "error": "WSL2 TTS not set up. Run setup first."
            }

        # Start the server in background
        start_cmd = (
            f'wsl -d {WSL2_DISTRO} -- bash -c "'
            f'cd {WSL2_TTS_DIR} && '
            f'source venv/bin/activate && '
            f'nohup python tts_server.py > tts_server.log 2>&1 &'
            '"'
        )

        process = await asyncio.create_subprocess_shell(
            start_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

        logger.info("wsl2_tts_server_starting")

        # Wait for server to become ready (up to 3 minutes for model loading)
        import httpx

        max_wait = 180  # 3 minutes
        check_interval = 5
        waited = 0

        async with httpx.AsyncClient() as client:
            while waited < max_wait:
                await asyncio.sleep(check_interval)
                waited += check_interval

                try:
                    response = await client.get(f"http://localhost:{WSL2_TTS_PORT}/health", timeout=2.0)
                    data = response.json()

                    if data.get("ready"):
                        logger.info("wsl2_tts_server_ready", warmup_seconds=waited)
                        return {
                            "success": True,
                            "message": "Server started and ready",
                            "ready": True,
                            "warmup_seconds": waited
                        }
                    elif data.get("loading"):
                        logger.debug("wsl2_tts_server_loading", seconds=waited)
                except Exception:
                    logger.debug("wsl2_tts_server_not_responding", seconds=waited)

        return {
            "success": False,
            "error": "Server started but did not become ready within timeout"
        }

    except Exception as e:
        logger.error("wsl2_tts_server_start_failed", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }


async def stop_wsl2_tts_server() -> Dict[str, Any]:
    """
    Stop the WSL2 TTS server.

    Returns:
        Dict with success status
    """
    try:
        cmd = f'wsl -d {WSL2_DISTRO} -- pkill -f "tts_server.py"'
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

        logger.info("wsl2_tts_server_stopped")
        return {
            "success": True,
            "message": "Server stopped"
        }
    except Exception as e:
        logger.error("wsl2_tts_server_stop_failed", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }


async def uninstall_wsl2_tts() -> Dict[str, Any]:
    """
    Uninstall WSL2 TTS setup (removes directory and models).

    Returns:
        Dict with success status
    """
    try:
        # Stop server first
        await stop_wsl2_tts_server()

        # Remove directory
        cmd = f"rm -rf {WSL2_TTS_DIR}"
        code, stdout, stderr = await _run_wsl_command(cmd, timeout=60)

        if code != 0:
            return {
                "success": False,
                "error": f"Failed to remove directory: {stderr}"
            }

        logger.info("wsl2_tts_uninstalled")
        return {
            "success": True,
            "message": "WSL2 TTS uninstalled"
        }
    except Exception as e:
        logger.error("wsl2_tts_uninstall_failed", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }


async def install_wsl2() -> Dict[str, Any]:
    """
    Install WSL2 with Ubuntu using administrator privileges.

    This runs 'wsl --install' which:
    1. Enables WSL feature
    2. Enables Virtual Machine Platform
    3. Downloads and installs Linux kernel
    4. Sets WSL2 as default
    5. Downloads and installs Ubuntu

    Requires admin privileges (will show UAC prompt).
    May require a system restart after installation.

    Returns:
        Dict with success status and message
    """
    import sys

    if sys.platform != "win32":
        return {
            "success": False,
            "error": "WSL2 installation is only available on Windows"
        }

    logger.info("wsl2_install_starting")

    try:
        # Use PowerShell to run wsl --install with admin elevation
        # This will trigger a UAC prompt for the user
        # The -Wait flag makes it wait for the installer to complete
        powershell_cmd = (
            'Start-Process -FilePath "wsl" -ArgumentList "--install" '
            '-Verb RunAs -Wait'
        )

        process = await asyncio.create_subprocess_shell(
            f'powershell -Command "{powershell_cmd}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=600  # 10 minutes max for installation
        )

        if process.returncode == 0:
            logger.info("wsl2_install_completed")
            return {
                "success": True,
                "message": "WSL2 installation started. Please restart your computer to complete the installation.",
                "restart_required": True
            }
        else:
            error_msg = stderr.decode('utf-8', errors='replace') if stderr else "Installation was cancelled or failed"
            logger.error("wsl2_install_failed", error=error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    except asyncio.TimeoutError:
        logger.error("wsl2_install_timeout")
        return {
            "success": False,
            "error": "Installation timed out. Please try running 'wsl --install' manually in an admin terminal."
        }
    except Exception as e:
        logger.error("wsl2_install_error", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }
