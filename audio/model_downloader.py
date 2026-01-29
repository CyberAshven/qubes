"""
Qwen3-TTS Model Downloader

Handles downloading Qwen3-TTS models from HuggingFace with real progress tracking.
Uses file-based progress tracking to work across process boundaries.
"""

import os
import uuid
import json
import threading
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DownloadProgress:
    """Tracks download progress for a model."""
    download_id: str
    model_name: str
    status: str = "pending"  # pending, downloading, completed, failed, cancelled
    total_bytes: int = 0
    downloaded_bytes: int = 0
    current_file: str = ""
    files_completed: int = 0
    files_total: int = 0
    speed_bytes_per_sec: float = 0.0
    eta_seconds: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class Qwen3ModelDownloader:
    """
    Downloads Qwen3-TTS models from HuggingFace.

    Models are stored in ~/.qubes/models/qwen3-tts/
    Progress is tracked in a JSON file for cross-process access.
    """

    MODELS = {
        "1.7B-Base": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "1.7B-CustomVoice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "1.7B-VoiceDesign": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "0.6B-Base": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "0.6B-CustomVoice": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        "Tokenizer": "Qwen/Qwen3-TTS-Tokenizer-12Hz",
    }

    def __init__(self, models_dir: Optional[Path] = None):
        """
        Initialize the model downloader.

        Args:
            models_dir: Directory to store models (default: ~/.qubes/models/qwen3-tts/)
        """
        self.models_dir = models_dir or Path.home() / ".qubes" / "models" / "qwen3-tts"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.models_dir / ".download_progress.json"

    def get_model_path(self, model_name: str) -> Path:
        """Get the local path for a model."""
        return self.models_dir / model_name

    def is_model_downloaded(self, model_name: str) -> bool:
        """Check if a model is already downloaded."""
        model_path = self.get_model_path(model_name)
        # Check for model files (safetensors or bin)
        if model_path.exists():
            safetensors = list(model_path.glob("*.safetensors"))
            bins = list(model_path.glob("*.bin"))
            config = model_path / "config.json"
            return (len(safetensors) > 0 or len(bins) > 0) or config.exists()
        return False

    def list_downloaded_models(self) -> list[str]:
        """List all downloaded models."""
        downloaded = []
        for model_name in self.MODELS.keys():
            if self.is_model_downloaded(model_name):
                downloaded.append(model_name)
        return downloaded

    def _load_progress(self) -> Dict[str, Dict]:
        """Load progress from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_progress(self, progress: DownloadProgress) -> None:
        """Save progress to file."""
        all_progress = self._load_progress()
        all_progress[progress.download_id] = asdict(progress)
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(all_progress, f)
        except IOError as e:
            logger.warning(f"Could not save progress: {e}")

    def _get_directory_size(self, path: Path) -> int:
        """Get total size of all files in a directory."""
        total = 0
        if path.exists():
            for f in path.rglob("*"):
                if f.is_file():
                    try:
                        total += f.stat().st_size
                    except (OSError, IOError):
                        pass
        return total

    def start_download(self, model_name: str) -> str:
        """
        Start downloading a model in a background process.

        Args:
            model_name: Name of the model to download

        Returns:
            download_id for tracking progress
        """
        if model_name not in self.MODELS:
            raise ValueError(f"Unknown model: {model_name}. Available: {list(self.MODELS.keys())}")

        # Check if already downloading
        all_progress = self._load_progress()
        for download_id, prog in all_progress.items():
            if prog.get('model_name') == model_name and prog.get('status') == 'downloading':
                return download_id

        # Check if already downloaded
        if self.is_model_downloaded(model_name):
            download_id = str(uuid.uuid4())[:8]
            progress = DownloadProgress(
                download_id=download_id,
                model_name=model_name,
                status="completed",
                started_at=datetime.now().isoformat(),
                completed_at=datetime.now().isoformat()
            )
            self._save_progress(progress)
            return download_id

        # Create new download
        download_id = str(uuid.uuid4())[:8]
        progress = DownloadProgress(
            download_id=download_id,
            model_name=model_name,
            status="downloading",
            started_at=datetime.now().isoformat(),
            current_file="Starting download..."
        )
        self._save_progress(progress)

        logger.info(
            "model_download_started",
            download_id=download_id,
            model_name=model_name
        )

        # Start download in a separate Python process (not a thread)
        # This process will run independently and update the progress file
        script_path = Path(__file__).parent / "download_worker.py"

        # Use subprocess.Popen to start a detached process
        if sys.platform == 'win32':
            # Windows: use CREATE_NEW_PROCESS_GROUP, DETACHED_PROCESS, and CREATE_NO_WINDOW
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                [sys.executable, str(script_path), download_id, model_name, str(self.models_dir)],
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        else:
            # Unix: use nohup-style detachment
            subprocess.Popen(
                [sys.executable, str(script_path), download_id, model_name, str(self.models_dir)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

        return download_id

    def get_progress(self, download_id: str) -> Dict[str, Any]:
        """
        Get download progress.

        Args:
            download_id: Download ID from start_download

        Returns:
            Dict with progress info
        """
        all_progress = self._load_progress()

        if download_id not in all_progress:
            return {
                "status": "not_found",
                "error": f"Download {download_id} not found"
            }

        prog = all_progress[download_id]

        # Calculate percentage
        percentage = 0.0
        total_bytes = prog.get('total_bytes', 0)
        downloaded_bytes = prog.get('downloaded_bytes', 0)

        if prog.get('status') == "completed":
            percentage = 100.0
        elif total_bytes > 0:
            percentage = min(99.9, (downloaded_bytes / total_bytes) * 100)

        speed = prog.get('speed_bytes_per_sec', 0)

        return {
            "download_id": prog.get('download_id'),
            "model_name": prog.get('model_name'),
            "status": prog.get('status'),
            "percentage": round(percentage, 1),
            "current_file": prog.get('current_file', ''),
            "files_completed": prog.get('files_completed', 0),
            "files_total": prog.get('files_total', 0),
            "downloaded_bytes": downloaded_bytes,
            "total_bytes": total_bytes,
            "speed_mbps": round(speed / (1024 * 1024), 2) if speed else 0,
            "eta_seconds": round(prog.get('eta_seconds', 0), 0),
            "started_at": prog.get('started_at'),
            "completed_at": prog.get('completed_at'),
            "error": prog.get('error')
        }

    def cancel_download(self, download_id: str) -> bool:
        """
        Cancel an in-progress download.

        Args:
            download_id: Download ID to cancel

        Returns:
            True if cancelled, False if not found or already completed
        """
        all_progress = self._load_progress()

        if download_id not in all_progress:
            return False

        prog = all_progress[download_id]
        if prog.get('status') not in ["pending", "downloading"]:
            return False

        # Update status to cancelled - the worker process will check this
        prog['status'] = "cancelled"
        all_progress[download_id] = prog

        try:
            with open(self.progress_file, 'w') as f:
                json.dump(all_progress, f)
        except IOError:
            return False

        return True

    def delete_model(self, model_name: str) -> bool:
        """
        Delete a downloaded model.

        Args:
            model_name: Model to delete

        Returns:
            True if deleted, False if not found
        """
        model_path = self.get_model_path(model_name)
        if model_path.exists():
            import shutil
            shutil.rmtree(model_path)
            logger.info("model_deleted", model_name=model_name)
            return True
        return False

    def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage for downloaded models."""
        total_size = 0
        model_sizes = {}

        for model_name in self.MODELS.keys():
            model_path = self.get_model_path(model_name)
            if model_path.exists():
                size = sum(f.stat().st_size for f in model_path.rglob("*") if f.is_file())
                model_sizes[model_name] = size
                total_size += size

        return {
            "total_bytes": total_size,
            "total_gb": round(total_size / (1024**3), 2),
            "models": model_sizes
        }
