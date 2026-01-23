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

        # Determine output directory (qube's audio folder)
        if self.qube_data_dir:
            audio_dir = self.qube_data_dir / "audio"
        else:
            audio_dir = Path("data/audio")

        audio_dir.mkdir(parents=True, exist_ok=True)

        # Use correct extension based on provider (Gemini uses WAV, others use MP3)
        extension = "wav" if provider == "gemini" else "mp3"

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

        # Chunk text if needed (OpenAI has 4096 char limit, keep safe at 4000)
        text_chunks = chunk_text_for_tts(text, max_chars=4000)
        num_chunks = len(text_chunks)

        logger.info(
            "tts_chunking",
            total_chunks=num_chunks,
            block_number=block_number
        )

        # Generate audio for each chunk
        generated_paths = []
        tts_provider = self.tts_providers[provider]

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
