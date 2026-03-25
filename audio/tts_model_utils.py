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

    # Check HF_HOME first, then fall back to default HuggingFace cache location
    hf_cache_dirs = []
    if hf_home:
        hf_cache_dirs.append(Path(hf_home) / "hub")
    # Default HuggingFace cache location
    default_hf = Path.home() / ".cache" / "huggingface" / "hub"
    if default_hf.exists() and default_hf not in [Path(hf_home) / "hub" if hf_home else None]:
        hf_cache_dirs.append(default_hf)

    for hf_hub in hf_cache_dirs:
        if not kokoro_installed:
            kokoro_installed = (hf_hub / "models--hexgrad--Kokoro-82M").exists()
        if not st_installed:
            st_installed = (hf_hub / "models--sentence-transformers--all-MiniLM-L6-v2").exists()

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
        import sys
        from huggingface_hub import snapshot_download

        hf_home = os.environ.get("HF_HOME", None)
        dl_kwargs: Dict[str, Any] = {}
        if hf_home:
            dl_kwargs["cache_dir"] = str(Path(hf_home) / "hub")
        # Windows: disable symlinks to avoid WinError 1314 (requires admin/dev mode)
        if sys.platform == "win32":
            dl_kwargs["local_dir_use_symlinks"] = False

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
