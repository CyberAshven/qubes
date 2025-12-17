"""
Audio Manager

Unified interface for TTS and STT with multi-provider fallback support.
From docs/27_Audio_TTS_STT_Integration.md Section 5.1
"""

import os
from pathlib import Path
from typing import Dict, Optional, Any
import asyncio

from audio.tts_engine import TTSProvider, OpenAITTS, ElevenLabsTTS, GeminiTTS, GoogleTTS, PiperTTS, VoiceConfig
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

        logger.info(
            "audio_manager_initialized",
            tts_providers=list(self.tts_providers.keys()),
            stt_providers=list(self.stt_providers.keys())
        )

    def _load_config_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY"),
            "google_api_key": os.getenv("GOOGLE_API_KEY"),  # For Gemini TTS
            "google_tts_credentials_path": os.getenv("GOOGLE_TTS_CREDENTIALS_PATH"),  # For Cloud TTS
            "deepgram_api_key": os.getenv("DEEPGRAM_API_KEY"),
            "piper_model_path": Path(
                os.getenv(
                    "PIPER_MODEL_PATH",
                    "~/.qubes/models/piper/en_US-lessac-medium.onnx"
                )
            ),
            "whisper_cpp_model_path": Path(
                os.getenv(
                    "WHISPER_MODEL_PATH",
                    "~/.qubes/models/whisper/ggml-base.en.bin"
                )
            ),
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

        # Try providers in order (with Gemini and Google as fallback options)
        providers = [voice_config.provider, "gemini", "google", "openai", "piper"]

        for provider_name in providers:
            if provider_name not in self.tts_providers:
                logger.debug("tts_provider_not_available", provider=provider_name)
                continue

            try:
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
        provider: str = "openai"
    ) -> Path:
        """
        Generate speech audio and save to file in qube's audio directory

        Args:
            text: Text to convert to speech
            voice_model: Voice model to use (e.g., "alloy", "echo", "fable")
            provider: TTS provider to use (default: "openai")

        Returns:
            Path to generated audio file

        Raises:
            AIError: If TTS generation fails
        """
        logger.info(
            "generating_speech_file",
            text_length=len(text),
            provider=provider,
            voice=voice_model
        )

        # Determine output directory (qube's audio folder)
        if self.qube_data_dir:
            audio_dir = self.qube_data_dir / "audio"
        else:
            audio_dir = Path("data/audio")

        audio_dir.mkdir(parents=True, exist_ok=True)

        # Use a simple filename that gets replaced each time
        # This prevents accumulation of TTS files
        # Use correct extension based on provider (Gemini uses WAV, others use MP3)
        extension = "wav" if provider == "gemini" else "mp3"
        filename = f"latest_response.{extension}"
        output_path = audio_dir / filename

        # Delete old files (both .mp3 and .wav) if they exist
        # This ensures we don't have conflicting formats
        old_mp3 = audio_dir / "latest_response.mp3"
        old_wav = audio_dir / "latest_response.wav"
        if old_mp3.exists():
            old_mp3.unlink()
            logger.debug("deleted_old_tts_file", path=str(old_mp3))
        if old_wav.exists():
            old_wav.unlink()
            logger.debug("deleted_old_tts_file", path=str(old_wav))

        # Create voice config
        voice_config = VoiceConfig(
            provider=provider,
            voice_id=voice_model
        )

        # Check if provider is available
        if provider not in self.tts_providers:
            raise AIError(
                f"TTS provider '{provider}' not available. Available: {list(self.tts_providers.keys())}",
                context={"provider": provider}
            )

        # Generate audio file
        try:
            tts_provider = self.tts_providers[provider]
            await tts_provider.synthesize_file(text, voice_config, output_path)

            logger.info(
                "speech_file_generated",
                output_path=str(output_path),
                file_size=output_path.stat().st_size
            )

            return output_path

        except Exception as e:
            logger.error("speech_file_generation_failed", error=str(e), exc_info=True)
            raise AIError(
                f"Failed to generate speech file: {str(e)}",
                context={"text_length": len(text), "provider": provider},
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
                logger.info("stt_success", provider=provider_name, text_length=len(result["text"]))
                return result["text"]

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
                    return result["text"]

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
