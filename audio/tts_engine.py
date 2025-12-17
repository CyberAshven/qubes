"""
TTS (Text-to-Speech) Engine

Multi-provider TTS implementation with OpenAI, ElevenLabs, and Piper (local).
From docs/27_Audio_TTS_STT_Integration.md Section 3
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any
from pathlib import Path
import subprocess
import asyncio

from core.exceptions import AIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class VoiceConfig:
    """Voice configuration for TTS"""

    def __init__(
        self,
        provider: str = "openai",
        voice_id: str = "alloy",
        speed: float = 1.0,
        pitch: float | None = None,
        stability: float | None = None
    ):
        self.provider = provider
        self.voice_id = voice_id
        self.speed = max(0.5, min(2.0, speed))  # Clamp to [0.5, 2.0]
        self.pitch = pitch  # ElevenLabs only
        self.stability = stability  # ElevenLabs only


class TTSProvider(ABC):
    """Abstract base class for TTS providers"""

    @abstractmethod
    async def synthesize_stream(
        self, text: str, voice_config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """Stream audio chunks for low-latency playback"""
        pass

    @abstractmethod
    async def synthesize_file(
        self, text: str, voice_config: VoiceConfig, output_path: Path
    ) -> Path:
        """Generate complete audio file (for history/download)"""
        pass


class OpenAITTS(TTSProvider):
    """OpenAI TTS provider"""

    # Pricing per 1M characters (as of 2025)
    PRICING = {
        "tts-1": 15.00,      # Standard quality
        "tts-1-hd": 30.00,   # HD quality
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        logger.info("openai_tts_initialized")

    async def synthesize_stream(
        self, text: str, voice_config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """Stream audio from OpenAI TTS"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            logger.debug(
                "tts_synthesizing",
                provider="openai",
                voice=voice_config.voice_id,
                length=len(text)
            )

            # Record start
            MetricsRecorder.record_ai_api_call("openai_tts", "tts-1", "started")

            response = await client.audio.speech.create(
                model="tts-1",  # Standard quality for streaming
                voice=voice_config.voice_id,
                input=text,
                speed=voice_config.speed,
                response_format="mp3",
            )

            # Stream chunks
            # Note: response.iter_bytes() is a sync generator, not async
            for chunk in response.iter_bytes(chunk_size=4096):
                yield chunk

            # Record success
            MetricsRecorder.record_ai_api_call("openai_tts", "tts-1", "success")

            # Estimate cost
            chars = len(text)
            cost = (chars / 1_000_000) * self.PRICING["tts-1"]
            MetricsRecorder.record_ai_cost(cost, "openai", "tts-1")

            logger.info(
                "tts_completed",
                provider="openai",
                chars=chars,
                cost_usd=round(cost, 4)
            )

        except Exception as e:
            MetricsRecorder.record_ai_api_call("openai_tts", "tts-1", "error")
            logger.error("openai_tts_failed", error=str(e), exc_info=True)
            raise AIError(f"OpenAI TTS failed: {e}", cause=e)

    async def synthesize_file(
        self, text: str, voice_config: VoiceConfig, output_path: Path
    ) -> Path:
        """Generate complete audio file"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            response = await client.audio.speech.create(
                model="tts-1-hd",  # HD quality for saved files
                voice=voice_config.voice_id,
                input=text,
                speed=voice_config.speed,
                response_format="mp3",
            )

            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info("tts_file_saved", path=str(output_path), size_bytes=output_path.stat().st_size)

            return output_path

        except Exception as e:
            logger.error("openai_tts_file_failed", error=str(e), exc_info=True)
            raise AIError(f"OpenAI TTS file generation failed: {e}", cause=e)


class ElevenLabsTTS(TTSProvider):
    """ElevenLabs TTS provider (premium quality)"""

    # Pricing (as of 2025)
    PRICING = {
        "free": {"chars_per_month": 30_000, "cost": 0.00},
        "starter": {"chars_per_month": 100_000, "cost": 5.00},
        "creator": {"chars_per_month": 500_000, "cost": 22.00},
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        logger.info("elevenlabs_tts_initialized")

    async def synthesize_stream(
        self, text: str, voice_config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """Stream audio from ElevenLabs"""
        try:
            from elevenlabs import generate, set_api_key

            set_api_key(self.api_key)

            logger.debug(
                "tts_synthesizing",
                provider="elevenlabs",
                voice=voice_config.voice_id,
                length=len(text)
            )

            # v3 model (v1 deprecated Dec 15, 2025)
            audio_stream = generate(
                text=text,
                voice=voice_config.voice_id,
                model="eleven_turbo_v2_5",  # v3 model
                stream=True,
                voice_settings={
                    "stability": voice_config.stability or 0.5,
                    "similarity_boost": 0.75,
                }
            )

            for chunk in audio_stream:
                yield chunk

            logger.info(
                "tts_completed",
                provider="elevenlabs",
                chars=len(text)
            )

        except Exception as e:
            logger.error("elevenlabs_tts_failed", error=str(e), exc_info=True)
            raise AIError(f"ElevenLabs TTS failed: {e}", cause=e)

    async def synthesize_file(
        self, text: str, voice_config: VoiceConfig, output_path: Path
    ) -> Path:
        """Generate complete audio file"""
        try:
            from elevenlabs import generate, save, set_api_key

            set_api_key(self.api_key)

            # v3 model (v1 deprecated Dec 15, 2025)
            audio = generate(
                text=text,
                voice=voice_config.voice_id,
                model="eleven_turbo_v2_5",  # v3 model
                voice_settings={
                    "stability": voice_config.stability or 0.5,
                    "similarity_boost": 0.75,
                }
            )

            save(audio, str(output_path))

            logger.info("tts_file_saved", path=str(output_path))

            return output_path

        except Exception as e:
            logger.error("elevenlabs_tts_file_failed", error=str(e), exc_info=True)
            raise AIError(f"ElevenLabs TTS file generation failed: {e}", cause=e)


class GeminiTTS(TTSProvider):
    """Google Gemini TTS provider (uses simple API key - NEW 2025!)"""

    # Pricing TBD (Preview tier)
    # Model: gemini-2.5-flash-preview-tts

    # 30 available voices with different characteristics
    AVAILABLE_VOICES = [
        "Puck",      # Upbeat
        "Charon",    # Informative
        "Kore",      # Calm
        "Fenrir",    # Authoritative
        "Aoede",     # Expressive
        "Zephyr",    # Bright
    ]

    def __init__(self, api_key: str):
        """
        Initialize Gemini TTS provider.

        Args:
            api_key: Google AI Studio API key (same as for Gemini models)
        """
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        logger.info("gemini_tts_initialized")

    async def synthesize_stream(
        self, text: str, voice_config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """Stream audio from Gemini TTS API"""
        try:
            import aiohttp
            import json
            import base64

            logger.debug(
                "tts_synthesizing",
                provider="gemini",
                voice=voice_config.voice_id,
                length=len(text)
            )

            # Record start
            MetricsRecorder.record_ai_api_call("gemini_tts", "gemini-2.5-flash-preview-tts", "started")

            # Build request
            url = f"{self.base_url}/models/gemini-2.5-flash-preview-tts:generateContent"

            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }

            # Voice name (use PrebuiltVoiceConfig)
            voice_name = voice_config.voice_id if voice_config.voice_id else "Puck"

            payload = {
                "contents": [{
                    "parts": [{
                        "text": text
                    }]
                }],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": voice_name
                            }
                        }
                    }
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Gemini TTS API error {response.status}: {error_text}")

                    result = await response.json()

                    # Extract audio data from response
                    # Response format: candidates[0].content.parts[0].inlineData.data (base64)
                    if "candidates" in result and len(result["candidates"]) > 0:
                        parts = result["candidates"][0].get("content", {}).get("parts", [])

                        for part in parts:
                            if "inlineData" in part:
                                # Decode base64 audio
                                audio_b64 = part["inlineData"]["data"]
                                audio_bytes = base64.b64decode(audio_b64)

                                # Yield in chunks
                                chunk_size = 4096
                                for i in range(0, len(audio_bytes), chunk_size):
                                    yield audio_bytes[i:i + chunk_size]

            # Record success
            MetricsRecorder.record_ai_api_call("gemini_tts", "gemini-2.5-flash-preview-tts", "success")

            logger.info(
                "tts_completed",
                provider="gemini",
                voice=voice_name,
                chars=len(text)
            )

        except Exception as e:
            MetricsRecorder.record_ai_api_call("gemini_tts", "gemini-2.5-flash-preview-tts", "error")
            logger.error("gemini_tts_failed", error=str(e), exc_info=True)
            raise AIError(f"Gemini TTS failed: {e}", cause=e)

    async def synthesize_file(
        self, text: str, voice_config: VoiceConfig, output_path: Path
    ) -> Path:
        """Generate complete audio file"""
        try:
            # Collect all chunks
            audio_data = b""
            async for chunk in self.synthesize_stream(text, voice_config):
                audio_data += chunk

            # Gemini returns raw linear16 PCM audio without headers
            # We need to add WAV headers for browser playback
            wav_data = self._create_wav_file(audio_data)

            with open(output_path, "wb") as f:
                f.write(wav_data)

            logger.info(
                "tts_file_saved",
                path=str(output_path),
                size_bytes=len(wav_data),
                format="wav",
                pcm_size=len(audio_data)
            )

            return output_path

        except Exception as e:
            logger.error("gemini_tts_file_failed", error=str(e), exc_info=True)
            raise AIError(f"Gemini TTS file generation failed: {e}", cause=e)

    def _create_wav_file(self, pcm_data: bytes) -> bytes:
        """
        Create WAV file from raw PCM data.

        Gemini TTS returns linear16 PCM at 24kHz sample rate, mono.
        WAV format: RIFF header + fmt chunk + data chunk
        """
        import struct

        # WAV file parameters (based on Gemini TTS output)
        sample_rate = 24000  # 24kHz
        bits_per_sample = 16  # 16-bit
        channels = 1  # Mono

        # Calculate sizes
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = len(pcm_data)
        file_size = 36 + data_size  # 44 byte header - 8 bytes

        # Build WAV header
        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',           # ChunkID
            file_size,         # ChunkSize
            b'WAVE',           # Format
            b'fmt ',           # Subchunk1ID
            16,                # Subchunk1Size (16 for PCM)
            1,                 # AudioFormat (1 = PCM)
            channels,          # NumChannels
            sample_rate,       # SampleRate
            byte_rate,         # ByteRate
            block_align,       # BlockAlign
            bits_per_sample,   # BitsPerSample
            b'data',           # Subchunk2ID
            data_size          # Subchunk2Size
        )

        return wav_header + pcm_data


class GoogleTTS(TTSProvider):
    """Google Cloud Text-to-Speech provider (380+ voices)"""

    # Pricing per 1M characters (as of 2025)
    PRICING = {
        "standard": 4.00,      # Standard voices
        "wavenet": 16.00,      # WaveNet voices
        "neural2": 16.00,      # Neural2 voices
        "studio": 160.00,      # Studio voices (premium)
        "chirp3": 16.00,       # Chirp3-HD voices
    }

    # Free tier
    FREE_TIER = {
        "standard": 4_000_000,  # 4M chars/month
        "wavenet": 1_000_000,   # 1M chars/month
    }

    def __init__(self, credentials_path: str | None = None):
        """
        Initialize Google TTS provider.

        Args:
            credentials_path: Path to Google Cloud service account JSON.
                            If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        self.credentials_path = credentials_path

        # Set credentials if provided
        if credentials_path:
            import os
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        logger.info("google_tts_initialized", credentials=bool(credentials_path))

    async def synthesize_stream(
        self, text: str, voice_config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """Stream audio from Google Cloud TTS"""
        try:
            from google.cloud import texttospeech

            # Create client
            client = texttospeech.TextToSpeechClient()

            logger.debug(
                "tts_synthesizing",
                provider="google",
                voice=voice_config.voice_id,
                length=len(text)
            )

            # Record start
            MetricsRecorder.record_ai_api_call("google_tts", voice_config.voice_id, "started")

            # Parse voice_id format: "en-US-Neural2-A" or just "Neural2-A"
            voice_parts = voice_config.voice_id.split("-")
            if len(voice_parts) >= 4:
                # Full format: en-US-Neural2-A
                language_code = f"{voice_parts[0]}-{voice_parts[1]}"
                voice_name = voice_config.voice_id
            else:
                # Short format: Neural2-A (default to en-US)
                language_code = "en-US"
                voice_name = f"en-US-{voice_config.voice_id}"

            # Build synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Configure voice
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
            )

            # Configure audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=voice_config.speed,
                pitch=voice_config.pitch or 0.0,  # Google uses pitch in semitones
            )

            # Synthesize speech
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Yield audio content in chunks
            audio_content = response.audio_content
            chunk_size = 4096
            for i in range(0, len(audio_content), chunk_size):
                yield audio_content[i:i + chunk_size]

            # Record success
            MetricsRecorder.record_ai_api_call("google_tts", voice_config.voice_id, "success")

            # Estimate cost (determine voice type from name)
            chars = len(text)
            voice_type = self._get_voice_type(voice_name)
            cost = (chars / 1_000_000) * self.PRICING.get(voice_type, 16.00)
            MetricsRecorder.record_ai_cost(cost, "google", voice_name)

            logger.info(
                "tts_completed",
                provider="google",
                voice=voice_name,
                chars=chars,
                cost_usd=round(cost, 4)
            )

        except Exception as e:
            MetricsRecorder.record_ai_api_call("google_tts", voice_config.voice_id, "error")
            logger.error("google_tts_failed", error=str(e), exc_info=True)
            raise AIError(f"Google TTS failed: {e}", cause=e)

    async def synthesize_file(
        self, text: str, voice_config: VoiceConfig, output_path: Path
    ) -> Path:
        """Generate complete audio file"""
        try:
            from google.cloud import texttospeech

            # Create client
            client = texttospeech.TextToSpeechClient()

            # Parse voice_id format
            voice_parts = voice_config.voice_id.split("-")
            if len(voice_parts) >= 4:
                language_code = f"{voice_parts[0]}-{voice_parts[1]}"
                voice_name = voice_config.voice_id
            else:
                language_code = "en-US"
                voice_name = f"en-US-{voice_config.voice_id}"

            # Build synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Configure voice
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
            )

            # Configure audio (use higher quality for file)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=voice_config.speed,
                pitch=voice_config.pitch or 0.0,
            )

            # Synthesize speech
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Write to file
            with open(output_path, "wb") as f:
                f.write(response.audio_content)

            logger.info(
                "tts_file_saved",
                path=str(output_path),
                size_bytes=output_path.stat().st_size
            )

            return output_path

        except Exception as e:
            logger.error("google_tts_file_failed", error=str(e), exc_info=True)
            raise AIError(f"Google TTS file generation failed: {e}", cause=e)

    def _get_voice_type(self, voice_name: str) -> str:
        """Determine voice type from voice name for pricing"""
        voice_lower = voice_name.lower()
        if "studio" in voice_lower:
            return "studio"
        elif "neural2" in voice_lower:
            return "neural2"
        elif "wavenet" in voice_lower:
            return "wavenet"
        elif "chirp3" in voice_lower or "chirp" in voice_lower:
            return "chirp3"
        else:
            return "standard"


class PiperTTS(TTSProvider):
    """Local TTS using Piper (for sovereign mode)"""

    def __init__(self, model_path: Path):
        self.model_path = Path(model_path).expanduser()

        if not self.model_path.exists():
            logger.warning(
                "piper_model_not_found",
                path=str(self.model_path),
                message="Piper model not installed. Download from https://github.com/rhasspy/piper"
            )

        logger.info("piper_tts_initialized", model=str(self.model_path))

    async def synthesize_stream(
        self, text: str, voice_config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """Stream audio from Piper (local)"""
        try:
            logger.debug("tts_synthesizing", provider="piper", length=len(text))

            # Run Piper CLI (pipes to stdout)
            process = await asyncio.create_subprocess_exec(
                "piper",
                "--model", str(self.model_path),
                "--output-raw",  # Raw PCM audio
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Send text to stdin
            process.stdin.write(text.encode())
            await process.stdin.drain()
            process.stdin.close()

            # Stream PCM chunks
            while True:
                chunk = await process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk

            await process.wait()

            logger.info("tts_completed", provider="piper", chars=len(text))

        except FileNotFoundError:
            logger.error("piper_not_found", message="Piper binary not found in PATH")
            raise AIError("Piper TTS not installed. Install from https://github.com/rhasspy/piper")
        except Exception as e:
            logger.error("piper_tts_failed", error=str(e), exc_info=True)
            raise AIError(f"Piper TTS failed: {e}", cause=e)

    async def synthesize_file(
        self, text: str, voice_config: VoiceConfig, output_path: Path
    ) -> Path:
        """Generate complete audio file with Piper"""
        try:
            process = await asyncio.create_subprocess_exec(
                "piper",
                "--model", str(self.model_path),
                "--output_file", str(output_path),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            await process.communicate(input=text.encode())

            if process.returncode != 0:
                raise AIError(f"Piper process failed with code {process.returncode}")

            logger.info("tts_file_saved", path=str(output_path))

            return output_path

        except Exception as e:
            logger.error("piper_tts_file_failed", error=str(e), exc_info=True)
            raise AIError(f"Piper TTS file generation failed: {e}", cause=e)
