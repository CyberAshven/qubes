"""
Shared utilities for local TTS/embedding model management.

Used by both gui_bridge.py (CLI mode) and sidecar_server.py (server mode)
to avoid duplicating model-check and model-update logic.
"""

import os
from pathlib import Path
from typing import Any, Dict, List


def check_local_tts_models() -> Dict[str, Any]:
    """
    Return which local TTS and embedding models are installed.

    Checks HF_HOME for Kokoro-82M and sentence-transformers, and
    QUBES_MODELS_DIR for whisper binary models.
    """
    hf_home = os.environ.get("HF_HOME", "")
    models_dir = os.environ.get("QUBES_MODELS_DIR", "")

    kokoro_installed = False
    st_installed = False
    whisper_installed = False

    if hf_home:
        hf_path = Path(hf_home)
        kokoro_path = hf_path / "hub" / "models--hexgrad--Kokoro-82M"
        st_path = hf_path / "hub" / "models--sentence-transformers--all-MiniLM-L6-v2"
        kokoro_installed = kokoro_path.exists()
        st_installed = st_path.exists()

    if models_dir:
        whisper_path = Path(models_dir) / "whisper"
        whisper_installed = any(whisper_path.glob("*.bin")) if whisper_path.exists() else False

    return {
        "kokoro_installed": kokoro_installed,
        "sentence_transformers_installed": st_installed,
        "whisper_installed": whisper_installed,
        "hf_home": hf_home,
        "models_dir": str(models_dir or hf_home),
    }


def update_local_tts_models() -> Dict[str, Any]:
    """
    Re-download/update local TTS and embedding models from HuggingFace.

    Returns dict with keys: success (bool), updated (list), errors (list).
    """
    updated: List[str] = []
    errors: List[str] = []

    try:
        from huggingface_hub import snapshot_download

        hf_home = os.environ.get("HF_HOME", None)
        dl_kwargs: Dict[str, Any] = {}
        if hf_home:
            dl_kwargs["cache_dir"] = str(Path(hf_home) / "hub")

        try:
            snapshot_download("hexgrad/Kokoro-82M", local_files_only=False, **dl_kwargs)
            updated.append("kokoro-82m")
        except Exception as e:
            errors.append(f"Kokoro: {str(e)}")

        try:
            snapshot_download(
                "sentence-transformers/all-MiniLM-L6-v2",
                local_files_only=False,
                **dl_kwargs,
            )
            updated.append("sentence-transformers")
        except Exception as e:
            errors.append(f"sentence-transformers: {str(e)}")

    except ImportError as e:
        errors.append(f"huggingface_hub not available: {str(e)}")

    return {
        "success": len(errors) == 0,
        "updated": updated,
        "errors": errors,
    }
