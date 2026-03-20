"""
Audio Manager

Unified interface for TTS and STT with multi-provider fallback support.
From docs/27_Audio_TTS_STT_Integration.md Section 5.1
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
import asyncio

from audio.tts_engine import TTSProvider, OpenAITTS, ElevenLabsTTS, GeminiTTS, GoogleTTS, PiperTTS, VoiceConfig
from audio.wsl2_tts import WSL2TTSProvider
from audio.kokoro_tts import KokoroTTSProvider
from audio.stt_engine import STTProvider, OpenAIWhisper, DeepGramSTT, WhisperCppSTT
from audio.playback import AudioPlayer
from audio.recorder import AudioRecorder
from audio.hallucination_filter import HallucinationFilter
from audio.cache import AudioCache
from audio.rate_limiter import AudioRateLimiter
from core.exceptions import AIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)




def clean_text_for_speech(text: str) -> str:
    """
    Clean text for TTS by removing non-speakable elements.

    Removes:
    - Asterisk actions (*waves hello*, *sighs deeply*)
    - Markdown formatting (**, __, `, #)
    - URLs
    - Code blocks
    - Emoji shortcodes (:smile:)
    - Multiple spaces/newlines

    Args:
        text: Raw text that may contain markdown/actions

    Returns:
        Cleaned text suitable for speech synthesis
    """
    import re

    if not text:
        return text

    # Remove code blocks first (```...```)
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Remove inline code (`code`)
    text = re.sub(r'`[^`]+`', '', text)

    # Remove markdown headers (# Header)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Handle markdown formatting BEFORE action asterisks
    # Order matters: double markers first, then single
    text = re.sub(r'\*\*\*([^*]+)\*\*\*', r'\1', text)  # ***bold italic*** -> text
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)      # **bold** -> bold
    text = re.sub(r'__([^_]+)__', r'\1', text)          # __bold__ -> bold

    # Remove asterisk CHARACTERS but keep the content inside, add comma for natural pause
    # *waves hello* becomes "waves hello," (speaks action with brief pause after)
    # Must come after bold removal to avoid matching **bold** incorrectly
    text = re.sub(r'\*([^*]+)\*', r'\1,', text)

    # Remove underscore italic (but keep content)
    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', text)  # _italic_ -> italic

    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)

    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Remove emoji shortcodes :emoji_name:
    text = re.sub(r':[a-zA-Z0-9_+-]+:', '', text)

    # Remove bullet points and list markers
    text = re.sub(r'^[\s]*[-*•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Normalize whitespace (multiple spaces/newlines -> single space)
    text = re.sub(r'\s+', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def chunk_text_for_tts(text: str, max_chars: int = 4000) -> list[str]:
    """
    Split text into chunks at sentence boundaries for TTS generation.

    Keeps each chunk under max_chars while respecting sentence boundaries.

    Args:
        text: Text to split
        max_chars: Maximum characters per chunk (default: 4000 for OpenAI)

    Returns:
        List of text chunks
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current_chunk = ""

    # Split on sentence boundaries (., !, ?, followed by space or newline)
    import re
    sentences = re.split(r'([.!?]+[\s\n]+)', text)

    # Recombine punctuation with sentences
    combined_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        combined_sentences.append(sentences[i] + (sentences[i+1] if i+1 < len(sentences) else ''))

    # Handle last sentence if no trailing punctuation
    if len(sentences) % 2 == 1:
        combined_sentences.append(sentences[-1])

    for sentence in combined_sentences:
        # If a single sentence is too long, split it at word boundaries
        if len(sentence) > max_chars:
            words = sentence.split()
            temp_chunk = ""
            for word in words:
                if len(temp_chunk) + len(word) + 1 <= max_chars:
                    temp_chunk += word + " "
                else:
                    if temp_chunk:
                        chunks.append(temp_chunk.strip())
                    temp_chunk = word + " "
            if temp_chunk:
                current_chunk = temp_chunk.strip()
        # If adding sentence would exceed limit, start new chunk
        elif len(current_chunk) + len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
        else:
            current_chunk += sentence

    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [text]


class AudioManager:
    """Unified audio manager with TTS/STT and fallback handling"""

    def __init__(self, config: Optional[Dict[str, Any]] = None, qube_data_dir: Optional[Path] = None):
        """
        Initialize audio manager

        Args:
            config: Configuration dict with API keys and settings
            qube_data_dir: Qube-specific data directory for audio storage
        """
        if config is None:
            config = self._load_config_from_env()

        self.config = config
        self.qube_data_dir = qube_data_dir

        # Initialize TTS providers
        self.tts_providers = {}
        self._init_tts_providers()

        # Initialize STT providers
        self.stt_providers = {}
        self._init_stt_providers()

        # Initialize utilities
        self.cache = AudioCache(
            qube_data_dir=qube_data_dir,
            max_size_mb=config.get("audio_cache_size_mb", 500)
        )
        self.rate_limiter = AudioRateLimiter()
        self.hallucination_filter = HallucinationFilter()

        # STT name aliases for common misrecognitions
        # Keys are what STT might hear, values are correct spelling
        # Case-insensitive matching, preserves original case pattern
        self.stt_aliases = config.get("stt_aliases", {
            "Alf": "Alph",
        })

        logger.info(
            "audio_manager_initialized",
            tts_providers=list(self.tts_providers.keys()),
            stt_providers=list(self.stt_providers.keys()),
            stt_aliases=len(self.stt_aliases)
        )

    def _load_config_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        # Resolve base models dir: QUBES_MODELS_DIR env var or platform default
        _models_base = Path(os.getenv("QUBES_MODELS_DIR", "~/.qubes/models")).expanduser()
        return {
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY"),
            "google_api_key": os.getenv("GOOGLE_API_KEY"),  # For Gemini TTS
            "google_tts_credentials_path": os.getenv("GOOGLE_TTS_CREDENTIALS_PATH"),  # For Cloud TTS
            "deepgram_api_key": os.getenv("DEEPGRAM_API_KEY"),
            "piper_model_path": Path(
                os.getenv(
                    "PIPER_MODEL_PATH",
                    str(_models_base / "piper" / "en_US-lessac-medium.onnx")
                )
            ),
            "whisper_cpp_model_path": Path(
                os.getenv(
                    "WHISPER_MODEL_PATH",
                    str(_models_base / "whisper" / "ggml-base.en.bin")
                )
            ),
            "qwen3_models_dir": _models_base / "qwen3-tts",
        }

    def _init_tts_providers(self):
        """Initialize available TTS providers"""
        # OpenAI TTS
        if self.config.get("openai_api_key"):
            try:
                self.tts_providers["openai"] = OpenAITTS(
                    api_key=self.config["openai_api_key"]
                )
                logger.info("tts_provider_initialized", provider="openai")
            except Exception as e:
                logger.warning("tts_provider_init_failed", provider="openai", error=str(e))

        # ElevenLabs TTS
        if self.config.get("elevenlabs_api_key"):
            try:
                self.tts_providers["elevenlabs"] = ElevenLabsTTS(
                    api_key=self.config["elevenlabs_api_key"]
                )
                logger.info("tts_provider_initialized", provider="elevenlabs")
            except Exception as e:
                logger.warning("tts_provider_init_failed", provider="elevenlabs", error=str(e))

        # Gemini TTS (NEW 2025 - uses simple API key!)
        if self.config.get("google_api_key"):
            try:
                self.tts_providers["gemini"] = GeminiTTS(
                    api_key=self.config["google_api_key"]
                )
                logger.info("tts_provider_initialized", provider="gemini")
            except Exception as e:
                logger.warning("tts_provider_init_failed", provider="gemini", error=str(e))

        # Google Cloud TTS (requires service account JSON)
        google_creds = self.config.get("google_tts_credentials_path")
        if google_creds or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                self.tts_providers["google"] = GoogleTTS(
                    credentials_path=google_creds
                )
                logger.info("tts_provider_initialized", provider="google")
            except Exception as e:
                logger.warning("tts_provider_init_failed", provider="google", error=str(e))

        # Piper TTS (local)
        piper_model = self.config.get("piper_model_path")
        if piper_model:
            try:
                self.tts_providers["piper"] = PiperTTS(model_path=piper_model)
                logger.info("tts_provider_initialized", provider="piper")
            except Exception as e:
                logger.warning("tts_provider_init_failed", provider="piper", error=str(e))

        # Qwen3-TTS (local GPU) - uses global singleton that persists across calls
        if self._check_gpu_available():
            self.tts_providers["qwen3"] = None  # Lazy load marker
            logger.info("tts_provider_registered", provider="qwen3", status="lazy")

        # WSL2 TTS (Qwen3 via WSL2 server) - Windows only
        if sys.platform == "win32":
            try:
                self.tts_providers["wsl2"] = WSL2TTSProvider()
                logger.info("tts_provider_registered", provider="wsl2")
            except Exception as e:
                logger.debug("wsl2_tts_not_available", error=str(e))

        # Kokoro TTS (local, no GPU required) - fast 82M param model
        # Supports 54 voices across 8 languages, runs on CPU or GPU
        try:
            self.tts_providers["kokoro"] = KokoroTTSProvider()
            logger.info("tts_provider_initialized", provider="kokoro")
        except ImportError as e:
            logger.debug("kokoro_tts_not_available", error=str(e))
        except Exception as e:
            logger.warning("kokoro_tts_init_failed", error=str(e))

    def _init_stt_providers(self):
        """Initialize available STT providers"""
        # OpenAI Whisper
        if self.config.get("openai_api_key"):
            try:
                self.stt_providers["openai"] = OpenAIWhisper(
                    api_key=self.config["openai_api_key"]
                )
                logger.info("stt_provider_initialized", provider="openai")
            except Exception as e:
                logger.warning("stt_provider_init_failed", provider="openai", error=str(e))

        # DeepGram STT
        if self.config.get("deepgram_api_key"):
            try:
                self.stt_providers["deepgram"] = DeepGramSTT(
                    api_key=self.config["deepgram_api_key"]
                )
                logger.info("stt_provider_initialized", provider="deepgram")
            except Exception as e:
                logger.warning("stt_provider_init_failed", provider="deepgram", error=str(e))

        # Whisper.cpp (local)
        whisper_model = self.config.get("whisper_cpp_model_path")
        if whisper_model:
            try:
                self.stt_providers["whisper_cpp"] = WhisperCppSTT(
                    model_path=whisper_model
                )
                logger.info("stt_provider_initialized", provider="whisper_cpp")
            except Exception as e:
                logger.warning("stt_provider_init_failed", provider="whisper_cpp", error=str(e))

    def _check_gpu_available(self) -> bool:
        """Check if a suitable GPU is available for Qwen3-TTS"""
        try:
            import torch
            if not torch.cuda.is_available():
                return False
            # Check if any GPU has enough VRAM (minimum 2.5GB for 0.6B model)
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                vram_gb = props.total_memory / (1024**3)
                if vram_gb >= 2.5:
                    return True
            return False
        except ImportError:
            # PyTorch not installed
            return False
        except Exception as e:
            logger.debug("gpu_check_failed", error=str(e))
            return False

    def _get_qwen3_provider(self) -> Optional[TTSProvider]:
        """Get Qwen3 provider, initializing lazily if needed"""
        if "qwen3" not in self.tts_providers:
            return None

        provider = self.tts_providers.get("qwen3")
        if provider is not None:
            return provider

        # Lazy initialization
        try:
            from audio.qwen_tts import Qwen3TTSProvider

            # Use defaults for Qwen3 preferences (1.7B with flash attention)
            # These can be overridden per-user via the Settings UI
            model_variant = "1.7B"
            use_flash_attention = True

            # Try to load user preferences if we have user context
            if hasattr(self, 'user_data_dir') and self.user_data_dir:
                try:
                    from config.user_preferences import UserPreferencesManager
                    prefs_manager = UserPreferencesManager(self.user_data_dir)
                    qwen3_prefs = prefs_manager.get_qwen3_preferences()
                    model_variant = qwen3_prefs.model_variant
                    use_flash_attention = qwen3_prefs.use_flash_attention
                except Exception:
                    pass  # Use defaults

            # Use QUBES_MODELS_DIR if set, otherwise platform default
            qwen3_models_dir = self.config.get("qwen3_models_dir")

            # Auto-download model if not present
            if qwen3_models_dir is not None:
                try:
                    from audio.model_downloader import Qwen3ModelDownloader
                    _dl = Qwen3ModelDownloader(models_dir=qwen3_models_dir)
                    _variant_key = f"{model_variant}-Base"
                    if not _dl.is_model_downloaded(_variant_key):
                        logger.info("qwen3_auto_download_triggered", variant=_variant_key)
                        _dl.start_download(_variant_key)
                        # Also download tokenizer
                        if not _dl.is_model_downloaded("Tokenizer"):
                            _dl.start_download("Tokenizer")
                except Exception as _dl_err:
                    logger.warning("qwen3_auto_download_failed", error=str(_dl_err))

            provider = Qwen3TTSProvider(
                model_variant=model_variant,
                use_flash_attention=use_flash_attention,
                **({"models_dir": qwen3_models_dir} if qwen3_models_dir else {})
            )
            self.tts_providers["qwen3"] = provider
            logger.info("tts_provider_initialized", provider="qwen3")
            return provider

        except Exception as e:
            logger.warning("tts_provider_init_failed", provider="qwen3", error=str(e))
            # Remove from providers so we don't keep trying
            self.tts_providers.pop("qwen3", None)
            return None

    def start_qwen3_background_load(self, voice_config: Optional[VoiceConfig] = None) -> bool:
        """
        Start loading Qwen3 model in the background.

        Called when user sends a message to a TTS-enabled qube, allowing model
        to load while AI generates its response.

        Args:
            voice_config: Optional voice config to determine which model variant to load

        Returns:
            True if background load started, False if already loading or unavailable
        """
        if "qwen3" not in self.tts_providers:
            return False

        # Check if global model is already loaded
        try:
            from audio.qwen_tts import Qwen3TTSProvider
            if Qwen3TTSProvider._global_model is not None:
                logger.debug("qwen3_model_already_loaded_global")
                return False  # Already loaded globally
        except ImportError:
            return False

        async def _background_load():
            try:
                provider = self._get_qwen3_provider()
                if provider:
                    # Pre-load the specific model variant needed
                    voice_mode = voice_config.voice_mode if voice_config else "preset"
                    await provider.ensure_ready(voice_mode=voice_mode or "preset")
                logger.info("qwen3_background_load_complete")
            except Exception as e:
                logger.warning("qwen3_background_load_failed", error=str(e))

        # Start background task
        asyncio.create_task(_background_load())
        logger.info("qwen3_background_load_started")
        return True

    def check_qwen3_status(self) -> Dict[str, Any]:
        """
        Get Qwen3-TTS availability and GPU status.

        Returns:
            Dict with status info:
            - available: bool - Whether Qwen3 can be used
            - gpu_name: str | None - GPU name if available
            - vram_total_gb: float | None - Total VRAM
            - vram_available_gb: float | None - Available VRAM
            - recommended_variant: str | None - "1.7B" or "0.6B" based on VRAM
            - models_downloaded: list[str] - Downloaded model names
            - is_loaded: bool - Whether model is currently loaded
            - fallback_provider: str - Provider to use if Qwen3 unavailable
        """
        result = {
            "available": False,
            "gpu_name": None,
            "vram_total_gb": None,
            "vram_available_gb": None,
            "recommended_variant": None,
            "models_downloaded": [],
            "is_loaded": False,
            "fallback_provider": self._get_fallback_provider(),
        }

        try:
            import torch
            if not torch.cuda.is_available():
                return result

            # Get GPU info
            device = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(device)
            result["gpu_name"] = props.name
            result["vram_total_gb"] = round(props.total_memory / (1024**3), 1)

            # Get available VRAM
            free_memory = torch.cuda.mem_get_info(device)[0]
            result["vram_available_gb"] = round(free_memory / (1024**3), 1)

            # Recommend variant based on VRAM
            if result["vram_total_gb"] >= 5:
                result["recommended_variant"] = "1.7B"
            elif result["vram_total_gb"] >= 2.5:
                result["recommended_variant"] = "0.6B"

            result["available"] = result["recommended_variant"] is not None

            # Check downloaded models
            _models_base = Path(os.getenv("QUBES_MODELS_DIR", str(Path.home() / ".qubes" / "models")))
            models_dir = _models_base / "qwen3-tts"
            if models_dir.exists():
                for model_dir in models_dir.iterdir():
                    if model_dir.is_dir():
                        result["models_downloaded"].append(model_dir.name)

            # Check if model is loaded (global singleton)
            try:
                from audio.qwen_tts import Qwen3TTSProvider
                result["is_loaded"] = Qwen3TTSProvider._global_model is not None
            except ImportError:
                result["is_loaded"] = False

        except ImportError:
            pass
        except Exception as e:
            logger.debug("qwen3_status_check_failed", error=str(e))

        return result

    def check_kokoro_status(self) -> Dict[str, Any]:
        """
        Get Kokoro TTS availability status.

        Returns:
            Dict with status info:
            - available: bool - Whether Kokoro can be used
            - voices_count: int - Number of available voices
            - languages_count: int - Number of supported languages
            - version: str | None - Kokoro version if installed
            - error: str | None - Error message if not available
        """
        try:
            return KokoroTTSProvider.check_availability()
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "voices_count": 0,
                "languages_count": 0,
            }

    def _get_fallback_provider(self) -> str:
        """Get the best available fallback TTS provider"""
        # Prefer kokoro (local, fast) over cloud providers
        for provider in ["kokoro", "gemini", "openai", "piper"]:
            if provider in self.tts_providers and self.tts_providers[provider] is not None:
                return provider
        return "piper"

    def _apply_stt_aliases(self, text: str) -> str:
        """
        Apply STT name aliases to fix common misrecognitions.

        Performs case-insensitive word boundary matching and preserves
        the original case pattern when possible.

        Args:
            text: Transcribed text

        Returns:
            Text with aliases applied
        """
        import re

        if not self.stt_aliases or not text:
            return text

        result = text
        for wrong, correct in self.stt_aliases.items():
            # Case-insensitive word boundary match
            pattern = rf'\b{re.escape(wrong)}\b'
            matches = list(re.finditer(pattern, result, re.IGNORECASE))

            # Replace from end to preserve indices
            for match in reversed(matches):
                original = match.group()
                # Preserve case pattern: if original was all caps, make replacement all caps
                if original.isupper():
                    replacement = correct.upper()
                elif original.islower():
                    replacement = correct.lower()
                elif original[0].isupper():
                    replacement = correct.capitalize()
                else:
                    replacement = correct
                result = result[:match.start()] + replacement + result[match.end():]

        if result != text:
            logger.debug("stt_aliases_applied", original=text, corrected=result)

        return result

    def set_stt_aliases(self, aliases: Dict[str, str]) -> None:
        """
        Update STT aliases (e.g., from qube settings).

        Args:
            aliases: Dict mapping misrecognitions to correct spellings
        """
        self.stt_aliases.update(aliases)
        logger.info("stt_aliases_updated", count=len(self.stt_aliases))

    async def speak(
        self,
        text: str,
        voice_config: VoiceConfig,
        user_id: str = "default",
        use_cache: bool = True
    ) -> None:
        """
        Speak text with fallback handling

        Args:
            text: Text to speak
            voice_config: Voice configuration
            user_id: User ID for quota tracking
            use_cache: Whether to use audio cache

        Raises:
            AIError: If all TTS providers fail
        """
        logger.info(
            "tts_request",
            text_length=len(text),
            provider=voice_config.provider,
            voice=voice_config.voice_id
        )

        # Check cache first
        if use_cache:
            cached_file = self.cache.get(text, voice_config)
            if cached_file:
                player = AudioPlayer()
                await player.play_file(cached_file)
                logger.info("tts_played_from_cache")
                return

        # Check quota
        if not self.rate_limiter.check_tts_quota(user_id, text, voice_config.provider):
            logger.warning("tts_quota_exceeded", user_id=user_id)
            # Fall back to local provider
            voice_config.provider = "piper"

        # Try providers in order (with local and cloud fallbacks)
        # Use dict.fromkeys to deduplicate while preserving order
        providers = list(dict.fromkeys([voice_config.provider, "kokoro", "gemini", "google", "openai", "piper"]))

        for provider_name in providers:
            if provider_name not in self.tts_providers:
                logger.debug("tts_provider_not_available", provider=provider_name)
                continue

            try:
                # Handle lazy-loaded Qwen3 provider
                if provider_name == "qwen3":
                    provider = self._get_qwen3_provider()
                    if provider is None:
                        logger.debug("qwen3_lazy_init_failed")
                        continue
                    # Ensure model is ready for this voice config
                    await provider.ensure_ready(voice_mode=voice_config.voice_mode or "preset")
                else:
                    provider = self.tts_providers[provider_name]

                audio_stream = provider.synthesize_stream(text, voice_config)

                # Play audio
                player = AudioPlayer()
                await player.play_stream(audio_stream)

                logger.info("tts_success", provider=provider_name)

                # Cache audio (generate file for caching)
                if use_cache and provider_name != "piper":  # Don't cache local TTS
                    try:
                        import tempfile
                        temp_path = Path(tempfile.gettempdir()) / f"tts_{hash(text)}.mp3"
                        await provider.synthesize_file(text, voice_config, temp_path)
                        self.cache.set(text, voice_config, temp_path)
                        temp_path.unlink()  # Clean up temp file
                    except Exception as e:
                        logger.warning("tts_caching_failed", error=str(e))

                return  # Success

            except Exception as e:
                logger.warning(
                    "tts_provider_failed",
                    provider=provider_name,
                    error=str(e)
                )
                continue

        # All providers failed
        raise AIError("All TTS providers failed")

    async def generate_speech_file(
        self,
        text: str,
        voice_model: str = "alloy",
        provider: str = "openai",
        block_number: Optional[int] = None
    ) -> tuple[Path, int]:
        """
        Generate speech audio and save to file(s) in qube's audio directory.

        For long text (>4000 chars), automatically chunks at sentence boundaries
        and generates multiple audio files.

        Args:
            text: Text to convert to speech
            voice_model: Voice model to use (e.g., "alloy", "echo", "fable")
            provider: TTS provider to use (default: "openai")
            block_number: Optional session block number for file naming

        Returns:
            Tuple of (primary_audio_path, total_chunks)
            - primary_audio_path: Path to first/primary audio file
            - total_chunks: Number of chunks generated (1 for single file, >1 for chunked)

        Raises:
            AIError: If TTS generation fails
        """
        logger.info(
            "generating_speech_file",
            text_length=len(text),
            provider=provider,
            voice=voice_model,
            block_number=block_number
        )

        # Clean text for speech (remove asterisks, markdown, etc.)
        original_length = len(text)
        text = clean_text_for_speech(text)
        if len(text) != original_length:
            logger.info(
                "tts_text_cleaned",
                original_length=original_length,
                cleaned_length=len(text)
            )

        # Handle empty text after cleaning
        if not text.strip():
            logger.warning("tts_text_empty_after_cleaning")
            raise AIError("No speakable text after cleaning (text may have been all actions/markdown)")

        # Handle custom voices - look up from voice library and use WSL2/Qwen3
        custom_voice_config = None
        if provider == "custom":
            try:
                from config.user_preferences import UserPreferencesManager
                from utils.paths import get_user_data_dir
                if self.qube_data_dir:
                    # Extract user_id from qube path: data/users/{user_id}/qubes/{qube_id}/
                    # qube_data_dir.parent = qubes/, qube_data_dir.parent.parent = {user_id}/
                    user_id = self.qube_data_dir.parent.parent.name
                    user_data_dir = get_user_data_dir(user_id)
                    logger.info("custom_voice_lookup", user_id=user_id, user_data_dir=str(user_data_dir))
                    prefs_manager = UserPreferencesManager(user_data_dir)
                    voice_library = prefs_manager.get_voice_library()

                    # voice_model is the voice ID (e.g., "Optimus_prime")
                    if voice_model in voice_library:
                        voice_entry = voice_library[voice_model]
                        logger.info("custom_voice_found", voice_id=voice_model, voice_type=voice_entry.voice_type)

                        # Build custom voice config for Qwen3/WSL2
                        custom_voice_config = {
                            "voice_mode": "cloned" if voice_entry.voice_type == "cloned" else "designed",
                            "clone_audio_path": voice_entry.clone_audio_path,
                            "clone_audio_text": voice_entry.clone_audio_text,
                            "design_prompt": voice_entry.design_prompt,
                            "language": voice_entry.language,
                        }
                        # Use WSL2/Qwen3 as the actual provider
                        provider = "wsl2"
                    else:
                        logger.warning("custom_voice_not_found", voice_id=voice_model)
                        raise AIError(f"Custom voice '{voice_model}' not found in voice library")
            except ImportError:
                raise AIError("Voice library not available")

        # Determine output directory (qube's audio folder)
        if self.qube_data_dir:
            audio_dir = self.qube_data_dir / "audio"
        else:
            from utils.paths import get_app_data_dir
            audio_dir = get_app_data_dir() / "audio"

        audio_dir.mkdir(parents=True, exist_ok=True)

        # Use correct extension based on provider (Gemini/WSL2/Qwen3/Kokoro use WAV, others use MP3)
        extension = "wav" if provider in ("gemini", "wsl2", "qwen3", "kokoro") else "mp3"

        # Get model_variant from user preferences (default to 1.7B)
        model_variant = "1.7B"
        if self.qube_data_dir:
            try:
                from config.user_preferences import UserPreferencesManager
                from utils.paths import get_user_data_dir
                user_id = self.qube_data_dir.parent.parent.name
                user_data_dir = get_user_data_dir(user_id)
                prefs_manager = UserPreferencesManager(user_data_dir)
                prefs = prefs_manager.load_preferences()
                model_variant = prefs.qwen3.model_variant
                logger.info("qwen3_model_variant", variant=model_variant)
            except Exception as e:
                logger.warning("failed_to_get_model_variant", error=str(e))

        # Create voice config
        if custom_voice_config:
            # Custom voice with cloning/design settings
            voice_config = VoiceConfig(
                provider=provider,
                voice_id=voice_model,
                voice_mode=custom_voice_config.get("voice_mode", "cloned"),
                clone_audio_path=custom_voice_config.get("clone_audio_path"),
                clone_audio_text=custom_voice_config.get("clone_audio_text"),
                voice_design_prompt=custom_voice_config.get("design_prompt"),
                language=custom_voice_config.get("language", "en"),
                model_variant=model_variant,
            )
        else:
            voice_config = VoiceConfig(
                provider=provider,
                voice_id=voice_model,
                model_variant=model_variant,
            )

        # Check if provider is available (handle lazy-loaded Qwen3)
        # "qwen" and "Qwen" are aliases for local TTS (routed to wsl2/qwen3)
        provider_lower = provider.lower()
        is_local_tts = provider_lower in ("qwen", "qwen3", "wsl2")
        if not is_local_tts and provider not in self.tts_providers:
            raise AIError(
                f"TTS provider '{provider}' not available. Available: {list(self.tts_providers.keys())}",
                context={"provider": provider}
            )

        # For Qwen3/WSL2, prefer WSL2 server (much faster - model stays loaded with torch.compile)
        # Handle various provider name formats: qwen, qwen3, Qwen, wsl2, WSL2, etc.
        if is_local_tts:
            wsl2_error = None  # Track WSL2 errors for better error reporting
            logger.info("tts_using_local_provider", provider=provider, voice=voice_model,
                       has_wsl2="wsl2" in self.tts_providers, providers=list(self.tts_providers.keys()))
            # Try WSL2 provider (server is started by Tauri app on launch via wsl2_server_manager)
            if "wsl2" in self.tts_providers:
                wsl2_provider = self.tts_providers["wsl2"]
                logger.info("trying_wsl2_tts", voice=voice_model, server_url=wsl2_provider.server_url)

                # Just check availability - don't try to start (managed server handles that)
                availability = await wsl2_provider.check_availability(try_auto_start=False)
                logger.info("wsl2_availability_result", available=availability.get("available"),
                           error=availability.get("error"))

                if availability["available"]:
                    if availability.get("auto_started"):
                        logger.info("wsl2_tts_auto_started")

                    # Generate single output file path (WSL2 outputs WAV)
                    if block_number is not None:
                        filename = f"audio_block_{block_number}.wav"
                    else:
                        filename = "latest_response.wav"
                    output_path = audio_dir / filename

                    try:
                        logger.info("wsl2_tts_synthesizing", text_len=len(text), output=str(output_path),
                                    voice_mode=getattr(voice_config, 'voice_mode', None))
                        await wsl2_provider.synthesize_file(text, voice_config, output_path)
                        logger.info("wsl2_tts_success", audio_path=str(output_path))
                        return output_path.resolve(), 1
                    except Exception as e:
                        wsl2_error = e  # Store the error for reporting
                        logger.warning("wsl2_tts_failed", error=str(e))
                        # Fall through to fallback providers
                else:
                    wsl2_error = AIError(f"WSL2 server not available: {availability.get('error')}")
                    logger.debug("wsl2_tts_not_available", error=availability.get("error"))

            # WSL2 not available or failed — report the error clearly.
            # Policy: never silently substitute a different voice/provider.
            # Try to find an available local provider and tell the user which one is being used.
            local_fallback_provider = None
            local_fallback_name = None
            for local_fallback in ("kokoro", "qwen3"):
                if local_fallback not in self.tts_providers:
                    continue
                if local_fallback == "qwen3":
                    qwen3 = self._get_qwen3_provider()
                    if qwen3 is None:
                        continue
                    local_fallback_provider = qwen3
                else:
                    local_fallback_provider = self.tts_providers[local_fallback]
                local_fallback_name = local_fallback
                break

            if local_fallback_provider is None:
                error_msg = str(wsl2_error) if wsl2_error else "No local TTS providers available"
                logger.error("local_tts_failed", provider=provider, error=error_msg)
                raise AIError(
                    f"Local TTS failed: {error_msg}",
                    context={"provider": provider, "voice": voice_model}
                )

            # Log the fallback clearly so it's visible in diagnostics
            logger.warning("local_tts_provider_fallback",
                          requested=provider, using=local_fallback_name,
                          reason=str(wsl2_error) if wsl2_error else "WSL2 not available")
            provider = local_fallback_name
            extension = "wav"
            tts_provider = local_fallback_provider
        else:
            # Non-local provider (openai, gemini, etc.) - use directly
            tts_provider = self.tts_providers[provider]

        # Chunk text if needed (OpenAI has 4096 char limit, keep safe at 4000)
        # Qwen3 can handle longer text, but chunking still improves streaming latency
        text_chunks = chunk_text_for_tts(text, max_chars=4000)
        num_chunks = len(text_chunks)

        logger.info(
            "tts_chunking",
            total_chunks=num_chunks,
            block_number=block_number
        )

        # Generate audio for each chunk
        generated_paths = []

        try:
            for chunk_index, chunk_text in enumerate(text_chunks):
                # Generate filename
                if block_number is not None:
                    # Session-based naming: audio_block_-5.mp3 or audio_block_-5_chunk_2.mp3
                    if num_chunks > 1:
                        filename = f"audio_block_{block_number}_chunk_{chunk_index + 1}.{extension}"
                    else:
                        filename = f"audio_block_{block_number}.{extension}"
                else:
                    # Legacy naming for backward compatibility
                    if num_chunks > 1:
                        filename = f"latest_response_chunk_{chunk_index + 1}.{extension}"
                    else:
                        filename = f"latest_response.{extension}"

                output_path = audio_dir / filename

                # Generate audio file for this chunk
                await tts_provider.synthesize_file(chunk_text, voice_config, output_path)

                # Convert to absolute path
                absolute_path = output_path.resolve()
                generated_paths.append(absolute_path)

                logger.info(
                    "tts_chunk_generated",
                    chunk_index=chunk_index + 1,
                    total_chunks=num_chunks,
                    output_path=str(absolute_path),
                    file_size=absolute_path.stat().st_size
                )

            # Log summary
            logger.info(
                "speech_file_generated",
                total_files=len(generated_paths),
                total_size=sum(p.stat().st_size for p in generated_paths),
                block_number=block_number
            )

            # Return first/primary file path and total chunk count
            # Frontend uses chunk count to know how many sequential files to play
            return (generated_paths[0], num_chunks)

        except Exception as e:
            logger.error("speech_file_generation_failed", error=str(e), exc_info=True)
            # Clean up any partially generated files
            for path in generated_paths:
                if path.exists():
                    path.unlink()
            raise AIError(
                f"Failed to generate speech file: {str(e)}",
                context={"text_length": len(text), "provider": provider, "num_chunks": num_chunks},
                cause=e
            )

    async def listen(
        self,
        mode: str = "ptt",
        language: str = "en",
        user_id: str = "default"
    ) -> str:
        """
        Record and transcribe speech with fallback handling

        Args:
            mode: Recording mode ("ptt" or "vad")
            language: Language code (e.g., "en", "es")
            user_id: User ID for quota tracking

        Returns:
            Transcribed text

        Raises:
            AIError: If all STT providers fail
        """
        logger.info("stt_request", mode=mode, language=language)

        # Record audio
        import tempfile
        recorder = AudioRecorder()
        audio_path = Path(tempfile.gettempdir()) / "qubes_voice_input.wav"

        try:
            if mode == "ptt":
                await recorder.record_ptt(audio_path)
            elif mode == "vad":
                await recorder.record_vad(audio_path)
            else:
                raise ValueError(f"Invalid mode: {mode}")

        except Exception as e:
            logger.error("audio_recording_failed", error=str(e), exc_info=True)
            raise AIError(f"Audio recording failed: {e}", cause=e)

        # Transcribe with fallback
        providers = ["openai", "deepgram", "whisper_cpp"]

        for provider_name in providers:
            if provider_name not in self.stt_providers:
                logger.debug("stt_provider_not_available", provider=provider_name)
                continue

            try:
                provider = self.stt_providers[provider_name]
                result = await provider.transcribe(audio_path, language)

                # Check for hallucinations
                if self.hallucination_filter.is_likely_hallucination(
                    result["text"],
                    result.get("confidence", 1.0)
                ):
                    logger.warning("stt_hallucination_detected", text=result["text"])
                    continue  # Try next provider

                # Check quota (for cloud providers)
                if provider_name in ["openai", "deepgram"]:
                    duration = result.get("duration", 0)
                    if not self.rate_limiter.check_stt_quota(user_id, duration):
                        logger.warning("stt_quota_exceeded", user_id=user_id)
                        continue  # Fall back to local provider

                # Success
                audio_path.unlink()  # Clean up
                text = self._apply_stt_aliases(result["text"])
                logger.info("stt_success", provider=provider_name, text_length=len(text))
                return text

            except Exception as e:
                logger.warning(
                    "stt_provider_failed",
                    provider=provider_name,
                    error=str(e)
                )
                continue

        # Clean up audio file
        if audio_path.exists():
            audio_path.unlink()

        # All providers failed
        raise AIError("All STT providers failed")

    async def listen_from_file(self, audio_path: Path, language: str = "en") -> str:
        """
        Transcribe audio from file (for testing)

        Args:
            audio_path: Path to audio file
            language: Language code

        Returns:
            Transcribed text
        """
        providers = ["openai", "deepgram", "whisper_cpp"]

        for provider_name in providers:
            if provider_name not in self.stt_providers:
                continue

            try:
                provider = self.stt_providers[provider_name]
                result = await provider.transcribe(audio_path, language)

                # Check for hallucinations
                if not self.hallucination_filter.is_likely_hallucination(
                    result["text"],
                    result.get("confidence", 1.0)
                ):
                    return self._apply_stt_aliases(result["text"])

            except Exception as e:
                logger.warning(f"STT provider {provider_name} failed: {e}")
                continue

        raise AIError("All STT providers failed")

    def get_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for a user

        Args:
            user_id: User identifier

        Returns:
            Usage statistics dict
        """
        return self.rate_limiter.get_usage_stats(user_id)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get audio cache statistics

        Returns:
            Cache statistics dict
        """
        return self.cache.get_stats()

    def clear_cache(self) -> int:
        """
        Clear audio cache

        Returns:
            Number of files deleted
        """
        return self.cache.clear()

    def clear_session_audio(self) -> int:
        """
        Clear all session audio files (audio_block_*.mp3/wav and latest_response*.mp3/wav)

        Called on anchor or discard to clean up temporary TTS files.

        Returns:
            Number of files deleted
        """
        if not self.qube_data_dir:
            return 0

        audio_dir = self.qube_data_dir / "audio"
        if not audio_dir.exists():
            return 0

        deleted_count = 0

        # Patterns to match session audio files
        patterns = [
            "audio_block_*.mp3",
            "audio_block_*.wav",
            "latest_response*.mp3",
            "latest_response*.wav"
        ]

        import glob
        for pattern in patterns:
            for file_path in glob.glob(str(audio_dir / pattern)):
                try:
                    Path(file_path).unlink()
                    deleted_count += 1
                    logger.debug("deleted_session_audio", path=file_path)
                except Exception as e:
                    logger.warning("failed_to_delete_audio", path=file_path, error=str(e))

        if deleted_count > 0:
            logger.info("session_audio_cleared", files_deleted=deleted_count)

        return deleted_count
