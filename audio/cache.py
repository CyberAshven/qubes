"""
Audio Cache

Caches TTS audio files to reduce API costs.
From docs/27_Audio_TTS_STT_Integration.md Section 9.3
"""

import hashlib
from pathlib import Path
from typing import Optional
import shutil

from audio.tts_engine import VoiceConfig
from utils.logging import get_logger

logger = get_logger(__name__)


class AudioCache:
    """Cache for TTS audio files"""

    def __init__(self, cache_dir: Path = None, max_size_mb: int = 500, qube_data_dir: Path = None):
        """
        Initialize audio cache

        Args:
            cache_dir: Directory to store cached audio files (legacy)
            max_size_mb: Maximum cache size in megabytes
            qube_data_dir: Qube-specific data directory (preferred - uses {qube_dir}/audio/)
        """
        if qube_data_dir:
            # Qube-specific audio dir (flat structure, no nesting)
            cache_dir = qube_data_dir / "audio"
        elif cache_dir is None:
            # Global fallback (legacy)
            cache_dir = Path.home() / ".qubes" / "audio_cache"

        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024

        logger.info(
            "audio_cache_initialized",
            cache_dir=str(self.cache_dir),
            max_size_mb=max_size_mb
        )

    def get_cache_key(self, text: str, voice_config: VoiceConfig) -> str:
        """
        Generate cache key from text + voice config

        Args:
            text: Text to synthesize
            voice_config: Voice configuration

        Returns:
            SHA256 hash as cache key
        """
        cache_input = (
            f"{text}|{voice_config.provider}|{voice_config.voice_id}|{voice_config.speed}"
        )
        return hashlib.sha256(cache_input.encode()).hexdigest()

    def get(self, text: str, voice_config: VoiceConfig) -> Optional[Path]:
        """
        Get cached audio file if exists

        Args:
            text: Text to synthesize
            voice_config: Voice configuration

        Returns:
            Path to cached audio file, or None if not found
        """
        key = self.get_cache_key(text, voice_config)
        cache_file = self.cache_dir / f"{key}.mp3"

        if cache_file.exists():
            logger.info("audio_cache_hit", text=text[:30], key=key[:16])
            return cache_file

        logger.debug("audio_cache_miss", text=text[:30], key=key[:16])
        return None

    def set(self, text: str, voice_config: VoiceConfig, audio_path: Path) -> Path:
        """
        Save audio to cache

        Args:
            text: Text that was synthesized
            voice_config: Voice configuration
            audio_path: Path to audio file

        Returns:
            Path to cached file
        """
        key = self.get_cache_key(text, voice_config)
        cache_file = self.cache_dir / f"{key}.mp3"

        try:
            # Copy to cache
            shutil.copy(audio_path, cache_file)

            logger.info(
                "audio_cached",
                text=text[:30],
                key=key[:16],
                size_bytes=cache_file.stat().st_size
            )

            # Check cache size
            self._enforce_size_limit()

            return cache_file

        except Exception as e:
            logger.error("audio_cache_write_failed", error=str(e), exc_info=True)
            return audio_path  # Return original path if caching fails

    def _enforce_size_limit(self):
        """Enforce maximum cache size by removing oldest files"""
        try:
            # Get all cache files sorted by modification time
            cache_files = sorted(
                self.cache_dir.glob("*.mp3"),
                key=lambda p: p.stat().st_mtime
            )

            # Calculate total size
            total_size = sum(f.stat().st_size for f in cache_files)

            # Remove oldest files until under limit
            while total_size > self.max_size_bytes and cache_files:
                oldest_file = cache_files.pop(0)
                file_size = oldest_file.stat().st_size
                oldest_file.unlink()
                total_size -= file_size

                logger.debug(
                    "audio_cache_file_removed",
                    file=oldest_file.name,
                    size_bytes=file_size
                )

            if total_size > self.max_size_bytes:
                logger.warning(
                    "audio_cache_size_limit_exceeded",
                    total_size_mb=total_size / (1024 * 1024),
                    max_size_mb=self.max_size_bytes / (1024 * 1024)
                )

        except Exception as e:
            logger.error("cache_size_enforcement_failed", error=str(e), exc_info=True)

    def clear(self) -> int:
        """
        Clear entire cache

        Returns:
            Number of files deleted
        """
        try:
            files_deleted = 0
            for cache_file in self.cache_dir.glob("*.mp3"):
                cache_file.unlink()
                files_deleted += 1

            logger.info("audio_cache_cleared", files_deleted=files_deleted)
            return files_deleted

        except Exception as e:
            logger.error("cache_clear_failed", error=str(e), exc_info=True)
            return 0

    def get_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dict with cache stats (file_count, total_size_mb)
        """
        try:
            cache_files = list(self.cache_dir.glob("*.mp3"))
            total_size = sum(f.stat().st_size for f in cache_files)

            stats = {
                "file_count": len(cache_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
                "utilization_percent": round(
                    (total_size / self.max_size_bytes) * 100, 1
                ) if self.max_size_bytes > 0 else 0,
            }

            logger.debug("cache_stats_retrieved", **stats)
            return stats

        except Exception as e:
            logger.error("cache_stats_failed", error=str(e), exc_info=True)
            return {"file_count": 0, "total_size_mb": 0, "max_size_mb": 0}
