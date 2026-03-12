"""
Kokoro TTS Provider

Fast, lightweight local TTS using Kokoro (82M params).
Supports 54 voices across 8 languages.
Runs on CPU or GPU without requiring WSL2 setup.

Apache 2.0 licensed - free for commercial and personal use.
"""

import asyncio
import io
from pathlib import Path
from typing import AsyncIterator, Dict, List, Any, Optional

from audio.tts_engine import TTSProvider, VoiceConfig
from utils.logging import get_logger

logger = get_logger(__name__)


class KokoroTTSProvider(TTSProvider):
    """
    Fast local TTS using Kokoro (82M params).

    - Runs on CPU or GPU
    - 54 voices across 8 languages
    - ~90-210x real-time speed on GPU
    - No model download required (auto-downloads on first use)
    - 24kHz audio output
    """

    # Language code mapping (our codes -> Kokoro codes)
    LANG_CODES = {
        'en': 'a',      # American English (default)
        'en-us': 'a',
        'en-gb': 'b',   # British English
        'ja': 'j',      # Japanese
        'zh': 'z',      # Mandarin Chinese
        'es': 'e',      # Spanish
        'fr': 'f',      # French
        'hi': 'h',      # Hindi
        'it': 'i',      # Italian
        'pt': 'p',      # Portuguese
    }

    # Default voices per language
    DEFAULT_VOICES = {
        'a': 'af_heart',    # American English
        'b': 'bf_emma',     # British English
        'j': 'jf_alpha',    # Japanese
        'z': 'zf_xiaoxiao', # Mandarin
        'e': 'ef_dora',     # Spanish
        'f': 'ff_siwis',    # French
        'h': 'hf_alpha',    # Hindi
        'i': 'if_sara',     # Italian
        'p': 'pf_dora',     # Portuguese
    }

    # All available voices grouped by language code
    VOICES = {
        'a': [  # American English (11F, 9M)
            'af_heart', 'af_alloy', 'af_aoede', 'af_bella', 'af_jessica',
            'af_kore', 'af_nicole', 'af_nova', 'af_river', 'af_sarah', 'af_sky',
            'am_adam', 'am_echo', 'am_eric', 'am_fenrir', 'am_liam',
            'am_michael', 'am_onyx', 'am_puck', 'am_santa'
        ],
        'b': [  # British English (4F, 4M)
            'bf_alice', 'bf_emma', 'bf_isabella', 'bf_lily',
            'bm_daniel', 'bm_fable', 'bm_george', 'bm_lewis'
        ],
        'j': [  # Japanese (4F, 1M)
            'jf_alpha', 'jf_gongitsune', 'jf_nezumi', 'jf_tebukuro', 'jm_kumo'
        ],
        'z': [  # Mandarin Chinese (4F, 4M)
            'zf_xiaobei', 'zf_xiaoni', 'zf_xiaoxiao', 'zf_xiaoyi',
            'zm_yunjian', 'zm_yunxi', 'zm_yunxia', 'zm_yunyang'
        ],
        'e': [  # Spanish (1F, 2M)
            'ef_dora', 'em_alex', 'em_santa'
        ],
        'f': [  # French (1F)
            'ff_siwis'
        ],
        'h': [  # Hindi (2F, 2M)
            'hf_alpha', 'hf_beta', 'hm_omega', 'hm_psi'
        ],
        'i': [  # Italian (1F, 1M)
            'if_sara', 'im_nicola'
        ],
        'p': [  # Portuguese (1F, 2M)
            'pf_dora', 'pm_alex', 'pm_santa'
        ],
    }

    # Human-readable language names
    LANGUAGE_NAMES = {
        'a': 'American English',
        'b': 'British English',
        'j': 'Japanese',
        'z': 'Mandarin Chinese',
        'e': 'Spanish',
        'f': 'French',
        'h': 'Hindi',
        'i': 'Italian',
        'p': 'Portuguese',
    }

    def __init__(self):
        """Initialize Kokoro TTS provider (lazy loads model on first use)."""
        self._pipeline = None
        self._current_lang = None
        self._async_lock = asyncio.Lock()
        import threading
        self._thread_lock = threading.Lock()  # Thread-safe lock for _generate_sync
        logger.info("kokoro_tts_provider_initialized")

    def _get_lang_code(self, voice_config: VoiceConfig) -> str:
        """Get Kokoro language code from voice config."""
        # First, check if voice_id specifies language (first char)
        voice_id = voice_config.voice_id or ""
        if voice_id and voice_id[0] in self.VOICES:
            return voice_id[0]

        # Then check language field
        if voice_config.language:
            lang = voice_config.language.lower()
            if lang in self.LANG_CODES:
                return self.LANG_CODES[lang]

        # Default to American English
        return 'a'

    def _get_voice(self, voice_config: VoiceConfig, lang_code: str) -> str:
        """Get voice ID, validating it exists for the language."""
        voice_id = voice_config.voice_id

        if not voice_id:
            raise ValueError("No voice_id specified in voice config")

        # Check if voice exists in specified language
        if voice_id in self.VOICES.get(lang_code, []):
            return voice_id
        # Check if voice exists in any language (use as-is)
        for voices in self.VOICES.values():
            if voice_id in voices:
                return voice_id

        raise ValueError(
            f"Kokoro voice '{voice_id}' not found. "
            f"Available for lang '{lang_code}': {self.VOICES.get(lang_code, [])}"
        )

    async def synthesize_stream(
        self, text: str, voice_config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """
        Stream audio chunks for low-latency playback.

        Args:
            text: Text to synthesize
            voice_config: Voice configuration

        Yields:
            Audio chunks (4096 bytes each)
        """
        audio_bytes = await self._generate(text, voice_config)

        # Stream in chunks
        chunk_size = 4096
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i:i + chunk_size]

    async def synthesize_file(
        self, text: str, voice_config: VoiceConfig, output_path: Path
    ) -> Path:
        """
        Generate complete audio file.

        Args:
            text: Text to synthesize
            voice_config: Voice configuration
            output_path: Path to save audio file

        Returns:
            Path to generated audio file
        """
        audio_bytes = await self._generate(text, voice_config)

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write audio file
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        logger.info(
            "kokoro_audio_file_saved",
            path=str(output_path),
            size=len(audio_bytes)
        )

        return output_path

    async def _generate(self, text: str, voice_config: VoiceConfig) -> bytes:
        """
        Generate audio using Kokoro pipeline.

        Args:
            text: Text to synthesize
            voice_config: Voice configuration

        Returns:
            WAV audio bytes
        """
        if not text.strip():
            return b''

        # Run synchronous generation in thread pool
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._generate_sync,
            text,
            voice_config
        )

    def _generate_sync(self, text: str, voice_config: VoiceConfig) -> bytes:
        """
        Synchronous audio generation (runs in thread pool).

        Args:
            text: Text to synthesize
            voice_config: Voice configuration

        Returns:
            WAV audio bytes
        """
        import time
        import numpy as np
        import soundfile as sf

        start_time = time.time()

        # Determine language and voice
        lang_code = self._get_lang_code(voice_config)
        voice = self._get_voice(voice_config, lang_code)
        speed = voice_config.speed if voice_config.speed else 1.0

        logger.info(
            "kokoro_generating",
            text_length=len(text),
            requested_voice=voice_config.voice_id,
            resolved_voice=voice,
            lang_code=lang_code,
            speed=speed
        )

        # Use thread lock to prevent concurrent access to shared pipeline
        with self._thread_lock:
            # Initialize or switch pipeline if language changed
            if self._pipeline is None or self._current_lang != lang_code:
                logger.info("kokoro_loading_pipeline", lang_code=lang_code)

                # Suppress stdout/stderr during Kokoro initialization
                # (it prints warnings and may run pip install on first use)
                import warnings
                from contextlib import redirect_stdout, redirect_stderr
                from io import StringIO

                # Acquire model_init_lock to prevent overlap with
                # SentenceTransformer loading, which uses accelerate's
                # init_empty_weights() — a process-global monkey-patch of
                # torch.nn.Module.__init__ that would make our tensors meta.
                from ai._model_init_lock import model_init_lock

                with model_init_lock:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        # Redirect stdout/stderr to suppress pip install output
                        devnull = StringIO()
                        with redirect_stdout(devnull), redirect_stderr(devnull):
                            from kokoro import KPipeline
                            # Use GPU if available, fall back to CPU
                            import torch
                            device = 'cuda' if torch.cuda.is_available() else 'cpu'
                            logger.info("kokoro_device", device=device)
                            self._pipeline = KPipeline(lang_code=lang_code, repo_id='hexgrad/Kokoro-82M', device=device)

                self._current_lang = lang_code
                logger.info("kokoro_pipeline_loaded", load_time_ms=int((time.time() - start_time) * 1000))

            # Generate audio
            gen_start = time.time()
            generator = self._pipeline(
                text,
                voice=voice,
                speed=speed,
            )

            # Collect all audio chunks
            audio_chunks = []
            for gs, ps, audio in generator:
                audio_chunks.append(audio)

        # Release lock before post-processing
        if not audio_chunks:
            logger.warning("kokoro_no_audio_generated")
            return b''

        # Concatenate audio chunks
        combined = np.concatenate(audio_chunks)

        # Convert to WAV bytes
        buffer = io.BytesIO()
        sf.write(buffer, combined, 24000, format='WAV')
        buffer.seek(0)
        audio_bytes = buffer.read()

        total_time = int((time.time() - start_time) * 1000)
        gen_time = int((time.time() - gen_start) * 1000)
        logger.info(
            "kokoro_audio_generated",
            text_length=len(text),
            audio_size=len(audio_bytes),
            voice=voice,
            gen_time_ms=gen_time,
            total_time_ms=total_time
        )

        return audio_bytes

    @classmethod
    def get_all_voices(cls) -> Dict[str, List[Dict[str, str]]]:
        """
        Get all available voices organized by language.

        Returns:
            Dict mapping language names to list of voice dicts
        """
        result = {}
        for lang_code, voices in cls.VOICES.items():
            lang_name = cls.LANGUAGE_NAMES.get(lang_code, lang_code)
            result[lang_name] = [
                {
                    'id': voice,
                    'name': cls._format_voice_name(voice),
                    'gender': 'female' if voice[1] == 'f' else 'male',
                }
                for voice in voices
            ]
        return result

    @staticmethod
    def _format_voice_name(voice_id: str) -> str:
        """Format voice ID into human-readable name."""
        # Extract name part after underscore
        if '_' in voice_id:
            name = voice_id.split('_', 1)[1]
            # Capitalize first letter
            name = name.capitalize()
            # Add gender indicator
            gender = '(Female)' if voice_id[1] == 'f' else '(Male)'
            return f"{name} {gender}"
        return voice_id

    @classmethod
    def get_voices_for_language(cls, language: str) -> List[str]:
        """
        Get available voices for a specific language.

        Args:
            language: Language code (e.g., 'en', 'ja') or Kokoro code (e.g., 'a', 'j')

        Returns:
            List of voice IDs
        """
        # Convert to Kokoro code if needed
        lang_code = cls.LANG_CODES.get(language.lower(), language)

        return cls.VOICES.get(lang_code, [])

    @classmethod
    def check_availability(cls) -> Dict[str, Any]:
        """
        Check if Kokoro TTS is available.

        Returns:
            Dict with availability info
        """
        result = {
            "available": False,
            "error": None,
            "voices_count": 54,
            "languages_count": 8,
        }

        try:
            # Check if kokoro is installed
            import kokoro  # noqa: F401
            result["available"] = True
            result["version"] = getattr(kokoro, '__version__', 'unknown')
        except ImportError:
            result["error"] = "Kokoro not installed. Run: pip install kokoro soundfile"

        try:
            # Check if soundfile is installed
            import soundfile  # noqa: F401
        except ImportError:
            result["available"] = False
            result["error"] = "soundfile not installed. Run: pip install soundfile"

        return result
