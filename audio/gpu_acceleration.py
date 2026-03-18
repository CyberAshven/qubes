"""
GPU Acceleration Manager

Handles checking GPU status and installing CUDA PyTorch for GPU-accelerated TTS.
In bundled builds (PyInstaller --onedir), this downloads CUDA torch wheels and
extracts them into _internal/, replacing the CPU-only torch.
"""

import os
import sys
import json
import uuid
import shutil
import threading
import time
import platform as plat
import urllib.request
import urllib.error
import zipfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from utils.logging import get_logger
from utils.paths import get_cache_dir

logger = get_logger(__name__)

# Progress file for cross-process tracking
PROGRESS_DIR = get_cache_dir() / "gpu-acceleration"
PROGRESS_FILE = PROGRESS_DIR / ".install_progress.json"


@dataclass
class InstallProgress:
    """Tracks GPU acceleration install progress."""
    install_id: str
    status: str = "pending"  # pending, downloading, extracting, completed, failed
    phase: str = ""  # "torch", "torchaudio", "verifying"
    total_bytes: int = 0
    downloaded_bytes: int = 0
    speed_mbps: float = 0.0
    eta_seconds: float = 0.0
    error: Optional[str] = None


def _load_progress() -> Dict[str, Dict]:
    """Load progress from file."""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_progress(progress: InstallProgress) -> None:
    """Save progress to file."""
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    all_progress = _load_progress()
    all_progress[progress.install_id] = asdict(progress)
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(all_progress, f)
    except IOError as e:
        logger.warning(f"Could not save progress: {e}")


def _detect_nvidia_gpu() -> Dict[str, Any]:
    """Detect NVIDIA GPU via nvidia-smi (independent of PyTorch)."""
    result = {"detected": False, "name": None, "vram_gb": None, "driver_version": None}
    try:
        proc = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total,driver_version',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=10
        )
        if proc.returncode == 0 and proc.stdout.strip():
            parts = [p.strip() for p in proc.stdout.strip().split('\n')[0].split(',')]
            result["detected"] = True
            result["name"] = parts[0] if len(parts) > 0 else None
            result["vram_gb"] = round(int(parts[1]) / 1024, 1) if len(parts) > 1 and parts[1].strip().isdigit() else None
            result["driver_version"] = parts[2] if len(parts) > 2 else None
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return result


def check_gpu_acceleration() -> Dict[str, Any]:
    """
    Check GPU hardware presence and CUDA PyTorch status.

    Returns dict with:
    - gpu_detected: bool - NVIDIA GPU found via nvidia-smi
    - gpu_name: str | None
    - gpu_vram_gb: float | None
    - driver_version: str | None
    - cuda_available: bool - torch.cuda.is_available()
    - torch_version: str | None
    - torch_cuda_version: str | None - CUDA version torch was built with
    - torch_device: str - "cuda" or "cpu"
    - upgrade_available: bool - GPU present but no CUDA torch
    - is_frozen: bool - Running as PyInstaller bundle
    """
    result = {
        "success": True,
        "gpu_detected": False,
        "gpu_name": None,
        "gpu_vram_gb": None,
        "driver_version": None,
        "cuda_available": False,
        "torch_version": None,
        "torch_cuda_version": None,
        "torch_device": "cpu",
        "upgrade_available": False,
        "is_frozen": getattr(sys, 'frozen', False),
    }

    # Check GPU hardware (independent of torch)
    gpu_info = _detect_nvidia_gpu()
    result["gpu_detected"] = gpu_info["detected"]
    result["gpu_name"] = gpu_info["name"]
    result["gpu_vram_gb"] = gpu_info["vram_gb"]
    result["driver_version"] = gpu_info["driver_version"]

    # Check PyTorch CUDA status
    try:
        import torch
        result["torch_version"] = torch.__version__
        result["cuda_available"] = torch.cuda.is_available()
        if result["cuda_available"]:
            result["torch_cuda_version"] = torch.version.cuda
            result["torch_device"] = "cuda"
    except ImportError:
        pass

    # GPU present but torch doesn't have CUDA = upgrade available
    result["upgrade_available"] = result["gpu_detected"] and not result["cuda_available"]

    return result


def _get_internal_dir() -> Optional[Path]:
    """Get the _internal directory for a PyInstaller --onedir bundle."""
    if not getattr(sys, 'frozen', False):
        return None
    # In PyInstaller --onedir, executable is at qubes-backend/qubes-backend
    # and _internal is at qubes-backend/_internal/
    exe_dir = Path(sys.executable).parent
    internal = exe_dir / '_internal'
    if internal.exists():
        return internal
    return None


def _get_wheel_url(package: str, version: str, cuda_tag: str = "cu124") -> str:
    """Construct PyTorch wheel URL for the current platform."""
    py_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"

    if sys.platform == 'darwin':
        raise RuntimeError("GPU acceleration uses Metal (MPS) on macOS — CUDA wheel install is not needed")
    elif sys.platform == 'linux':
        plat_tag = "linux_x86_64"
    elif sys.platform == 'win32':
        plat_tag = "win_amd64"
    else:
        raise RuntimeError("GPU acceleration not available on this platform")

    # URL-encode the + as %2B
    wheel_name = f"{package}-{version}%2B{cuda_tag}-{py_tag}-{py_tag}-{plat_tag}.whl"
    return f"https://download.pytorch.org/whl/{cuda_tag}/{wheel_name}"


def _download_with_progress(url: str, dest: Path, progress: InstallProgress) -> None:
    """Download a file with progress tracking."""
    response = urllib.request.urlopen(url)
    total = int(response.headers.get('Content-Length', 0))
    progress.total_bytes = total
    _save_progress(progress)

    chunk_size = 1024 * 1024  # 1MB chunks
    downloaded = 0
    start_time = time.time()

    with open(dest, 'wb') as f:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            progress.downloaded_bytes = downloaded

            elapsed = time.time() - start_time
            if elapsed > 0:
                speed = downloaded / elapsed
                progress.speed_mbps = round(speed / (1024 * 1024), 1)
                if speed > 0 and total > 0:
                    remaining = total - downloaded
                    progress.eta_seconds = round(remaining / speed)

            _save_progress(progress)


def start_install(install_id: Optional[str] = None) -> str:
    """
    Start installing CUDA PyTorch in a background thread.
    Returns install_id for progress tracking.
    """
    if install_id is None:
        install_id = str(uuid.uuid4())[:8]

    progress = InstallProgress(install_id=install_id, status="pending")
    _save_progress(progress)

    thread = threading.Thread(target=_install_worker, args=(install_id,), daemon=True)
    thread.start()

    return install_id


def _install_worker(install_id: str) -> None:
    """Background worker that downloads and installs CUDA torch."""
    progress = InstallProgress(install_id=install_id, status="downloading", phase="torch")
    _save_progress(progress)

    try:
        # Determine torch version
        import torch
        torch_version = torch.__version__.split('+')[0]

        is_frozen = getattr(sys, 'frozen', False)

        if is_frozen:
            _install_frozen(install_id, torch_version, progress)
        else:
            _install_dev(install_id, torch_version, progress)

    except Exception as e:
        logger.error(f"GPU acceleration install failed: {e}", exc_info=True)
        progress.status = "failed"
        progress.error = str(e)
        _save_progress(progress)


def _install_frozen(install_id: str, torch_version: str, progress: InstallProgress) -> None:
    """Install CUDA torch into PyInstaller _internal/ directory."""
    internal_dir = _get_internal_dir()
    if not internal_dir:
        raise RuntimeError("Cannot find _internal directory. Is this a PyInstaller build?")

    cache_dir = get_cache_dir() / "gpu-acceleration" / "downloads"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1: Download CUDA torch wheel
    progress.phase = "torch"
    progress.status = "downloading"
    _save_progress(progress)

    torch_url = _get_wheel_url("torch", torch_version)
    torch_whl = cache_dir / f"torch-{torch_version}-cuda.whl"

    logger.info("Downloading CUDA PyTorch", url=torch_url)
    try:
        _download_with_progress(torch_url, torch_whl, progress)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(
                f"CUDA PyTorch {torch_version} not found. "
                f"This torch version may not have a CUDA build available."
            )
        raise

    # Phase 2: Download CUDA torchaudio wheel
    progress.phase = "torchaudio"
    progress.downloaded_bytes = 0
    progress.total_bytes = 0
    _save_progress(progress)

    torchaudio_url = _get_wheel_url("torchaudio", torch_version)
    torchaudio_whl = cache_dir / f"torchaudio-{torch_version}-cuda.whl"

    logger.info("Downloading CUDA torchaudio", url=torchaudio_url)
    try:
        _download_with_progress(torchaudio_url, torchaudio_whl, progress)
    except urllib.error.HTTPError:
        # torchaudio CUDA is optional, continue without it
        torchaudio_whl = None
        logger.warning("CUDA torchaudio not available, skipping")

    # Phase 3: Extract into _internal/
    progress.phase = "extracting"
    progress.status = "extracting"
    progress.downloaded_bytes = 0
    progress.total_bytes = 0
    _save_progress(progress)

    # Back up existing torch
    torch_dir = internal_dir / 'torch'
    torch_backup = internal_dir / 'torch.cpu_backup'
    if torch_dir.exists() and not torch_backup.exists():
        logger.info("Backing up CPU torch")
        shutil.copytree(torch_dir, torch_backup, dirs_exist_ok=True)

    # Extract CUDA torch (overwrites CPU torch)
    logger.info("Extracting CUDA torch to _internal/")
    with zipfile.ZipFile(torch_whl) as zf:
        zf.extractall(str(internal_dir))

    # Extract torchaudio if available
    if torchaudio_whl and torchaudio_whl.exists():
        logger.info("Extracting CUDA torchaudio to _internal/")
        with zipfile.ZipFile(torchaudio_whl) as zf:
            zf.extractall(str(internal_dir))

    # Phase 4: Verify (can't fully verify until restart, but check files exist)
    progress.phase = "verifying"
    _save_progress(progress)

    cuda_libs = list((internal_dir / 'torch' / 'lib').glob('*cuda*'))
    if not cuda_libs:
        raise RuntimeError("CUDA libraries not found after extraction. Installation may have failed.")

    # Clean up downloads
    try:
        shutil.rmtree(cache_dir)
    except Exception:
        pass

    progress.status = "completed"
    progress.phase = "done"
    _save_progress(progress)
    logger.info("GPU acceleration installed successfully")


def _install_dev(install_id: str, torch_version: str, progress: InstallProgress) -> None:
    """Install CUDA torch in dev mode using pip."""
    progress.phase = "pip install"
    progress.status = "downloading"
    _save_progress(progress)

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install',
             'torch', 'torchaudio',
             '--index-url', 'https://download.pytorch.org/whl/cu124',
             '--upgrade'],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            raise RuntimeError(f"pip install failed: {result.stderr[-500:]}")

        progress.status = "completed"
        progress.phase = "done"
        _save_progress(progress)
    except subprocess.TimeoutExpired:
        raise RuntimeError("pip install timed out after 10 minutes")


def get_install_progress(install_id: str) -> Dict[str, Any]:
    """Get install progress by ID."""
    all_progress = _load_progress()
    if install_id in all_progress:
        return all_progress[install_id]
    return {"status": "unknown", "error": "Install ID not found"}


def uninstall_gpu_acceleration() -> Dict[str, Any]:
    """Revert to CPU-only torch by restoring backup."""
    internal_dir = _get_internal_dir()
    if not internal_dir:
        return {"success": False, "error": "Not a bundled build"}

    torch_backup = internal_dir / 'torch.cpu_backup'
    torch_dir = internal_dir / 'torch'

    if not torch_backup.exists():
        return {"success": False, "error": "No CPU backup found. Cannot revert."}

    try:
        # Remove CUDA torch
        if torch_dir.exists():
            shutil.rmtree(torch_dir)
        # Restore CPU torch
        shutil.copytree(torch_backup, torch_dir)
        # Remove backup
        shutil.rmtree(torch_backup)

        return {"success": True, "message": "Reverted to CPU-only PyTorch. Restart required."}
    except Exception as e:
        return {"success": False, "error": f"Failed to revert: {e}"}
