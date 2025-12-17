"""
STT (Speech-to-Text) Engine

Multi-provider STT implementation with OpenAI Whisper, DeepGram, and Whisper.cpp (local).
From docs/27_Audio_TTS_STT_Integration.md Section 4
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any
from pathlib import Path
import wave
import asyncio
import json
import subprocess

from core.exceptions import AIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class STTProvider(ABC):
    """Abstract base class for STT providers"""

    @abstractmethod
    async def transcribe(
        self, audio_path: Path, language: str = "en"
    ) -> Dict[str, Any]:
        """Transcribe audio file to text"""
        pass

    @abstractmethod
    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes], language: str = "en"
    ) -> Dict[str, Any]:
        """Transcribe audio stream (real-time)"""
        pass


class OpenAIWhisper(STTProvider):
    """OpenAI Whisper STT provider"""

    # Pricing: $0.006 per minute
    PRICING_PER_MINUTE = 0.006

    def __init__(self, api_key: str):
        self.api_key = api_key
        logger.info("openai_whisper_initialized")

    async def transcribe(
        self, audio_path: Path, language: str = "en", model: str = "whisper-1"
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using Whisper API

        Models:
        - whisper-1 (legacy, still supported)
        - whisper-large-v3-turbo (6x faster, recommended as of 2025)
        """
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            logger.debug(
                "stt_transcribing",
                provider="openai_whisper",
                file=str(audio_path),
                language=language
            )

            # Record start
            MetricsRecorder.record_ai_api_call("openai_whisper", model, "started")

            with open(audio_path, "rb") as audio_file:
                response = await client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",  # Includes timestamps
                )

            # Record success
            MetricsRecorder.record_ai_api_call("openai_whisper", model, "success")

            # Estimate cost (based on duration)
            duration_minutes = response.duration / 60.0
            cost = duration_minutes * self.PRICING_PER_MINUTE
            MetricsRecorder.record_ai_cost("openai", cost)

            result = {
                "text": response.text,
                "language": response.language,
                "duration": response.duration,
                "segments": response.segments if hasattr(response, 'segments') else [],
                "confidence": 0.95,  # OpenAI doesn't provide confidence
            }

            logger.info(
                "stt_completed",
                provider="openai_whisper",
                text_length=len(result["text"]),
                duration=response.duration,
                cost_usd=round(cost, 4)
            )

            return result

        except Exception as e:
            MetricsRecorder.record_ai_api_call("openai_whisper", model, "error")
            logger.error("openai_whisper_failed", error=str(e), exc_info=True)
            raise AIError(f"OpenAI Whisper failed: {e}", cause=e)

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes], language: str = "en"
    ) -> Dict[str, Any]:
        """OpenAI Whisper doesn't support streaming - save to file first"""
        try:
            # Buffer stream to temporary file
            import tempfile
            temp_path = Path(tempfile.gettempdir()) / "qubes_stt_buffer.wav"

            with wave.open(str(temp_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(16000)

                async for chunk in audio_stream:
                    wf.writeframes(chunk)

            # Transcribe file
            result = await self.transcribe(temp_path, language)

            # Cleanup
            temp_path.unlink()

            return result

        except Exception as e:
            logger.error("openai_whisper_stream_failed", error=str(e), exc_info=True)
            raise AIError(f"OpenAI Whisper streaming failed: {e}", cause=e)


class DeepGramSTT(STTProvider):
    """DeepGram STT provider (supports true streaming)"""

    # Pricing: $0.0043 per minute
    PRICING_PER_MINUTE = 0.0043

    def __init__(self, api_key: str):
        self.api_key = api_key
        logger.info("deepgram_stt_initialized")

    async def transcribe(
        self, audio_path: Path, language: str = "en"
    ) -> Dict[str, Any]:
        """Transcribe audio file using DeepGram"""
        try:
            from deepgram import Deepgram

            client = Deepgram(self.api_key)

            logger.debug(
                "stt_transcribing",
                provider="deepgram",
                file=str(audio_path),
                language=language
            )

            with open(audio_path, "rb") as audio_file:
                source = {"buffer": audio_file.read(), "mimetype": "audio/wav"}

                response = await client.transcription.prerecorded(
                    source,
                    {
                        "language": language,
                        "punctuate": True,
                        "model": "nova-2",  # Latest model
                    }
                )

            result = {
                "text": response["results"]["channels"][0]["alternatives"][0]["transcript"],
                "confidence": response["results"]["channels"][0]["alternatives"][0]["confidence"],
                "language": language,
                "duration": response["metadata"]["duration"],
            }

            logger.info(
                "stt_completed",
                provider="deepgram",
                text_length=len(result["text"]),
                confidence=result["confidence"]
            )

            return result

        except Exception as e:
            logger.error("deepgram_failed", error=str(e), exc_info=True)
            raise AIError(f"DeepGram STT failed: {e}", cause=e)

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes], language: str = "en"
    ) -> Dict[str, Any]:
        """True streaming transcription with DeepGram"""
        try:
            from deepgram import Deepgram

            client = Deepgram(self.api_key)
            transcripts = []

            async def audio_sender(socket):
                async for chunk in audio_stream:
                    await socket.send(chunk)

            async def transcript_receiver(socket):
                async for message in socket:
                    if message.get("is_final"):
                        transcripts.append(
                            message["channel"]["alternatives"][0]["transcript"]
                        )

            # WebSocket connection
            socket = await client.transcription.live({
                "language": language,
                "punctuate": True,
                "interim_results": False,  # Only final results
            })

            # Run sender/receiver concurrently
            await asyncio.gather(
                audio_sender(socket),
                transcript_receiver(socket),
            )

            result = {
                "text": " ".join(transcripts),
                "confidence": 0.95,  # Average (would need to track per-segment)
                "language": language,
            }

            logger.info(
                "stt_stream_completed",
                provider="deepgram",
                text_length=len(result["text"])
            )

            return result

        except Exception as e:
            logger.error("deepgram_stream_failed", error=str(e), exc_info=True)
            raise AIError(f"DeepGram streaming failed: {e}", cause=e)


class WhisperCppSTT(STTProvider):
    """Local STT using Whisper.cpp (for sovereign mode)"""

    def __init__(self, model_path: Path):
        self.model_path = Path(model_path).expanduser()

        if not self.model_path.exists():
            logger.warning(
                "whisper_cpp_model_not_found",
                path=str(self.model_path),
                message="Whisper.cpp model not installed. Download from https://github.com/ggerganov/whisper.cpp"
            )

        logger.info("whisper_cpp_stt_initialized", model=str(self.model_path))

    async def transcribe(
        self, audio_path: Path, language: str = "en"
    ) -> Dict[str, Any]:
        """Transcribe audio file using Whisper.cpp"""
        try:
            logger.debug(
                "stt_transcribing",
                provider="whisper_cpp",
                file=str(audio_path),
                language=language
            )

            # Run Whisper.cpp CLI
            process = await asyncio.create_subprocess_exec(
                "whisper-cpp",
                "--model", str(self.model_path),
                "--language", language,
                "--output-json",
                str(audio_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise AIError(f"Whisper.cpp failed: {stderr.decode()}")

            # Parse JSON output
            data = json.loads(stdout.decode())

            result = {
                "text": data.get("text", ""),
                "language": data.get("language", language),
                "segments": data.get("segments", []),
                "confidence": 0.90,  # Whisper.cpp doesn't provide confidence
            }

            logger.info(
                "stt_completed",
                provider="whisper_cpp",
                text_length=len(result["text"])
            )

            return result

        except FileNotFoundError:
            logger.error("whisper_cpp_not_found", message="Whisper.cpp binary not found in PATH")
            raise AIError("Whisper.cpp not installed. Install from https://github.com/ggerganov/whisper.cpp")
        except Exception as e:
            logger.error("whisper_cpp_failed", error=str(e), exc_info=True)
            raise AIError(f"Whisper.cpp failed: {e}", cause=e)

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes], language: str = "en"
    ) -> Dict[str, Any]:
        """Whisper.cpp doesn't support streaming - buffer to file"""
        try:
            import tempfile
            temp_path = Path(tempfile.gettempdir()) / "qubes_stt_whisper.wav"

            # Save stream to file
            with wave.open(str(temp_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)

                async for chunk in audio_stream:
                    wf.writeframes(chunk)

            result = await self.transcribe(temp_path, language)

            # Cleanup
            temp_path.unlink()

            return result

        except Exception as e:
            logger.error("whisper_cpp_stream_failed", error=str(e), exc_info=True)
            raise AIError(f"Whisper.cpp streaming failed: {e}", cause=e)
