#!/usr/bin/env python
"""
Qwen3-TTS Model Download Worker

This script runs as a separate process to download models from HuggingFace.
It updates a progress file that can be read by other processes.
"""

import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime


def get_directory_size(path: Path) -> int:
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


def load_progress(progress_file: Path) -> dict:
    """Load progress from file."""
    if progress_file.exists():
        try:
            with open(progress_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_progress(progress_file: Path, download_id: str, progress: dict) -> None:
    """Save progress to file."""
    all_progress = load_progress(progress_file)
    all_progress[download_id] = progress
    try:
        with open(progress_file, 'w') as f:
            json.dump(all_progress, f)
    except IOError as e:
        print(f"Could not save progress: {e}", file=sys.stderr)


def update_progress(progress_file: Path, download_id: str, model_name: str = None, **kwargs) -> dict:
    """Update specific fields in progress."""
    all_progress = load_progress(progress_file)

    # Initialize if doesn't exist
    if download_id not in all_progress:
        all_progress[download_id] = {
            "download_id": download_id,
            "model_name": model_name or "",
            "status": "downloading",
            "total_bytes": 0,
            "downloaded_bytes": 0,
            "current_file": "",
            "files_completed": 0,
            "files_total": 0,
            "speed_bytes_per_sec": 0.0,
            "eta_seconds": 0.0,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "error": None
        }

    all_progress[download_id].update(kwargs)
    if model_name:
        all_progress[download_id]["model_name"] = model_name

    try:
        with open(progress_file, 'w') as f:
            json.dump(all_progress, f)
    except IOError as e:
        print(f"Failed to save progress: {e}", file=sys.stderr)

    return all_progress[download_id]


def check_cancelled(progress_file: Path, download_id: str) -> bool:
    """Check if download was cancelled."""
    all_progress = load_progress(progress_file)
    if download_id in all_progress:
        return all_progress[download_id].get('status') == 'cancelled'
    return False


def ensure_qwen_tts_installed() -> bool:
    """Ensure qwen-tts package is installed."""
    try:
        import qwen_tts  # noqa: F401
        return True
    except ImportError:
        print("Installing qwen-tts package...", file=sys.stderr)
        import subprocess
        run_kwargs = {
            "capture_output": True,
            "text": True
        }
        # Hide console window on Windows
        if sys.platform == "win32":
            run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "qwen-tts"],
            **run_kwargs
        )
        if result.returncode != 0:
            print(f"Failed to install qwen-tts: {result.stderr}", file=sys.stderr)
            return False
        print("qwen-tts installed successfully", file=sys.stderr)
        return True


def download_model(download_id: str, model_name: str, models_dir: Path) -> None:
    """Download a model and update progress."""
    progress_file = models_dir / ".download_progress.json"
    local_dir = models_dir / model_name

    MODELS = {
        "1.7B-Base": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "1.7B-CustomVoice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "1.7B-VoiceDesign": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "0.6B-Base": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "0.6B-CustomVoice": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        "Tokenizer": "Qwen/Qwen3-TTS-Tokenizer-12Hz",
    }

    if model_name not in MODELS:
        update_progress(progress_file, download_id, model_name, status="failed", error=f"Unknown model: {model_name}")
        return

    # Ensure qwen-tts package is installed (needed to use the models)
    if not ensure_qwen_tts_installed():
        update_progress(progress_file, download_id, model_name, status="failed", error="Failed to install qwen-tts package")
        return

    repo_id = MODELS[model_name]

    try:
        from huggingface_hub import snapshot_download, HfApi

        # Step 1: Get total size
        update_progress(progress_file, download_id, model_name, current_file="Fetching model info...")
        api = HfApi()

        try:
            repo_info = api.repo_info(repo_id=repo_id, files_metadata=True)
            total_size = sum(s.size or 0 for s in repo_info.siblings)
            file_count = len(repo_info.siblings)

            update_progress(
                progress_file, download_id, model_name,
                total_bytes=total_size,
                files_total=file_count,
                current_file="Starting download..."
            )
        except Exception as e:
            print(f"Could not get repo info: {e}", file=sys.stderr)
            update_progress(progress_file, download_id, model_name, total_bytes=0, files_total=0)

        if check_cancelled(progress_file, download_id):
            return

        # Step 2: Start progress monitor
        monitor_stop = threading.Event()
        last_bytes = 0
        last_time = time.time()
        smoothed_speed = 0.0  # Exponentially smoothed speed

        def monitor_progress():
            nonlocal last_bytes, last_time, smoothed_speed
            while not monitor_stop.is_set():
                try:
                    if check_cancelled(progress_file, download_id):
                        monitor_stop.set()
                        return

                    current_size = get_directory_size(local_dir)

                    # Calculate speed with smoothing
                    now = time.time()
                    time_delta = now - last_time
                    if time_delta >= 0.5:
                        bytes_delta = current_size - last_bytes
                        instant_speed = bytes_delta / time_delta if time_delta > 0 else 0

                        # Exponential smoothing: new = alpha * instant + (1-alpha) * old
                        # Use alpha=0.3 for smoothing, but if instant > 0, bias towards it
                        if instant_speed > 0:
                            smoothed_speed = 0.4 * instant_speed + 0.6 * smoothed_speed
                        else:
                            # Decay slowly when no new bytes
                            smoothed_speed = 0.9 * smoothed_speed

                        # Get total bytes from progress file
                        all_prog = load_progress(progress_file)
                        total = all_prog.get(download_id, {}).get('total_bytes', 0)

                        # Calculate ETA using smoothed speed
                        eta = 0
                        if smoothed_speed > 0 and total > 0:
                            remaining = total - current_size
                            eta = remaining / smoothed_speed

                        update_progress(
                            progress_file, download_id, model_name,
                            downloaded_bytes=current_size,
                            speed_bytes_per_sec=smoothed_speed,
                            eta_seconds=eta,
                            current_file="Downloading..."
                        )

                        last_bytes = current_size
                        last_time = now

                except Exception as e:
                    print(f"Monitor error: {e}", file=sys.stderr)

                monitor_stop.wait(0.5)

        monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
        monitor_thread.start()

        # Step 3: Download
        try:
            snapshot_download(
                repo_id=repo_id,
                local_dir=str(local_dir),
                local_dir_use_symlinks=False,
                resume_download=True,
            )
        finally:
            monitor_stop.set()
            monitor_thread.join(timeout=2)

        if check_cancelled(progress_file, download_id):
            return

        # Step 4: Download tokenizer if needed
        if model_name != "Tokenizer":
            tokenizer_dir = models_dir / "Tokenizer"
            tokenizer_config = tokenizer_dir / "config.json"
            if not tokenizer_config.exists():
                update_progress(progress_file, download_id, model_name, current_file="Downloading tokenizer...")
                snapshot_download(
                    repo_id=MODELS["Tokenizer"],
                    local_dir=str(tokenizer_dir),
                    local_dir_use_symlinks=False,
                    resume_download=True,
                )

        # Step 5: Mark complete
        all_prog = load_progress(progress_file)
        total = all_prog.get(download_id, {}).get('total_bytes', 0)
        update_progress(
            progress_file, download_id, model_name,
            status="completed",
            completed_at=datetime.now().isoformat(),
            downloaded_bytes=total,
            current_file="",
            speed_bytes_per_sec=0,
            eta_seconds=0
        )

        print(f"Download completed: {model_name}", file=sys.stderr)

    except Exception as e:
        update_progress(
            progress_file, download_id, model_name,
            status="failed",
            error=str(e),
            current_file=""
        )
        print(f"Download failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: download_worker.py <download_id> <model_name> <models_dir>", file=sys.stderr)
        sys.exit(1)

    download_id = sys.argv[1]
    model_name = sys.argv[2]
    models_dir = Path(sys.argv[3])

    print(f"Starting download worker: {download_id} {model_name} {models_dir}", file=sys.stderr)
    download_model(download_id, model_name, models_dir)
