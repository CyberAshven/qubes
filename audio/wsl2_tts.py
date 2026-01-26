"""
WSL2 TTS Provider

Connects to the Qwen3-TTS server running in WSL2 for near real-time
local TTS generation using torch.compile + Triton optimizations.

Server runs at http://localhost:19533 in WSL2.
Auto-starts the server if not running.
"""

import asyncio
import subprocess
import io
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Optional

from audio.tts_engine import TTSProvider, VoiceConfig
from core.exceptions import AIError
from utils.logging import get_logger

logger = get_logger(__name__)

# WSL2 TTS Server URL
WSL2_TTS_SERVER_URL = "http://localhost:19533"

# WSL2 distribution and server path
WSL2_DISTRO = "Ubuntu-22.04"
WSL2_SERVER_SCRIPT = "~/qubes-tts/start_server.sh"


async def start_wsl2_tts_server() -> bool:
    """
    Start the WSL2 TTS server if not already running.

    Returns:
        True if server started or already running, False on error
    """
    try:
        import httpx

        # Check if already running
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{WSL2_TTS_SERVER_URL}/health", timeout=2.0)
                if response.json().get("ready"):
                    logger.debug("wsl2_tts_server_already_running")
                    return True
            except Exception:
                pass  # Server not running, we'll start it

        logger.info("wsl2_tts_server_starting")

        # Start the server in WSL2 (detached)
        cmd = f'wsl -d {WSL2_DISTRO} -- bash -c "cd ~/qubes-tts && source venv/bin/activate && nohup python3 tts_server.py > tts_server.log 2>&1 &"'

        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

        # Wait for server to be ready (warmup takes ~2 minutes)
        logger.info("wsl2_tts_server_warming_up", message="This takes ~2 minutes for first-time JIT compilation")

        max_wait = 180  # 3 minutes max
        check_interval = 5
        waited = 0

        async with httpx.AsyncClient() as client:
            while waited < max_wait:
                await asyncio.sleep(check_interval)
                waited += check_interval

                try:
                    response = await client.get(f"{WSL2_TTS_SERVER_URL}/health", timeout=2.0)
                    if response.json().get("ready"):
                        logger.info("wsl2_tts_server_ready", warmup_seconds=waited)
                        return True
                except Exception:
                    logger.debug("wsl2_tts_server_waiting", seconds=waited)

        logger.error("wsl2_tts_server_timeout")
        return False

    except Exception as e:
        logger.error("wsl2_tts_server_start_failed", error=str(e))
        return False


async def stop_wsl2_tts_server() -> bool:
    """
    Stop the WSL2 TTS server.

    Returns:
        True if stopped successfully
    """
    try:
        cmd = f'wsl -d {WSL2_DISTRO} -- pkill -f "tts_server.py"'
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()
        logger.info("wsl2_tts_server_stopped")
        return True
    except Exception as e:
        logger.error("wsl2_tts_server_stop_failed", error=str(e))
        return False


class WSL2TTSProvider(TTSProvider):
    """
    TTS provider that connects to Qwen3-TTS server running in WSL2.

    Provides near real-time TTS (RTF ~1.0) using:
    - Qwen3-TTS 1.7B model
    - torch.compile with Triton backend
    - Dynamic shape compilation for variable text lengths

    Preset speakers: Vivian, Serena, Uncle_Fu, Dylan, Eric, Ryan, Aiden, Ono_Anna, Sohee
    """

    PRESET_SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]

    LANGUAGE_MAP = {
        "en": "English",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "de": "German",
        "fr": "French",
        "ru": "Russian",
        "pt": "Portuguese",
        "es": "Spanish",
        "it": "Italian",
    }

    def __init__(self, server_url: str = WSL2_TTS_SERVER_URL, auto_start: bool = True):
        """
        Initialize WSL2 TTS provider.

        Args:
            server_url: URL of the WSL2 TTS server
            auto_start: Whether to auto-start the server if not running
        """
        self.server_url = server_url
        self.auto_start = auto_start
        self._client = None
        self._server_started = False  # Track if we've attempted to start this session
        logger.info("wsl2_tts_provider_initialized", server_url=server_url, auto_start=auto_start)

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def _ensure_server_running(self) -> bool:
        """
        Ensure the WSL2 TTS server is running.

        Returns:
            True if server is available, False otherwise
        """
        # Check if server is already available
        try:
            client = await self._get_client()
            response = await client.get(f"{self.server_url}/health", timeout=2.0)
            if response.json().get("ready"):
                return True
        except Exception:
            pass  # Server not responding

        # If auto-start is disabled or we've already tried, return False
        if not self.auto_start:
            logger.debug("wsl2_tts_auto_start_disabled")
            return False

        if self._server_started:
            logger.debug("wsl2_tts_already_attempted_start")
            return False

        # Try to start the server
        self._server_started = True
        logger.info("wsl2_tts_auto_starting_server")
        return await start_wsl2_tts_server()

    async def check_availability(self, try_auto_start: bool = False) -> Dict[str, Any]:
        """
        Check if WSL2 TTS server is available.

        Args:
            try_auto_start: If True and server not running, attempt to start it

        Returns:
            Dict with availability information
        """
        result = {
            "available": False,
            "server_url": self.server_url,
            "speakers": [],
            "error": None,
            "auto_started": False,
        }

        try:
            client = await self._get_client()
            response = await client.get(f"{self.server_url}/health", timeout=5.0)
            data = response.json()

            if data.get("ready"):
                result["available"] = True

                # Get speakers
                speakers_response = await client.get(f"{self.server_url}/speakers")
                result["speakers"] = speakers_response.json().get("speakers", [])
            else:
                result["error"] = "Server not ready (model still loading)"

        except Exception as e:
            result["error"] = f"Cannot connect to WSL2 TTS server: {e}"
            logger.debug("wsl2_tts_not_available", error=str(e))

            # Try to auto-start if requested
            if try_auto_start and self.auto_start and not self._server_started:
                logger.info("wsl2_tts_attempting_auto_start_on_check")
                if await self._ensure_server_running():
                    # Re-check availability after starting
                    result["auto_started"] = True
                    result["error"] = None
                    try:
                        response = await client.get(f"{self.server_url}/health", timeout=5.0)
                        if response.json().get("ready"):
                            result["available"] = True
                            speakers_response = await client.get(f"{self.server_url}/speakers")
                            result["speakers"] = speakers_response.json().get("speakers", [])
                    except Exception as e2:
                        result["error"] = f"Server started but not responding: {e2}"

        return result

    async def synthesize_stream(
        self, text: str, voice_config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """
        Stream audio chunks for playback.

        Note: Currently generates full audio then streams chunks.
        True streaming could be implemented with server-sent events.
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
        Generate audio and save to file.
        """
        audio_bytes = await self._generate(text, voice_config)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        logger.info("wsl2_tts_file_saved", path=str(output_path), size=len(audio_bytes))
        return output_path

    async def _generate(self, text: str, voice_config: VoiceConfig) -> bytes:
        """
        Generate audio via WSL2 TTS server.

        Auto-starts the server if not running and auto_start is enabled.
        """
        # Ensure server is running (auto-starts if needed)
        if not await self._ensure_server_running():
            raise AIError("WSL2 TTS server is not available and could not be started")

        speaker = voice_config.voice_id or "Vivian"
        language = self.LANGUAGE_MAP.get(voice_config.language or "en", "English")
        instruct = voice_config.voice_design_prompt or ""

        # Determine mode based on voice_mode or presence of design prompt
        voice_mode = getattr(voice_config, 'voice_mode', None) or "preset"
        if voice_mode == "designed" or (instruct and voice_mode != "preset"):
            mode = "design"
        else:
            mode = "preset"

        logger.debug("wsl2_tts_generating", text_length=len(text), speaker=speaker, mode=mode)

        try:
            client = await self._get_client()

            response = await client.post(
                f"{self.server_url}/generate",
                json={
                    "text": text,
                    "mode": mode,
                    "speaker": speaker,
                    "language": language,
                    "instruct": instruct,
                },
            )

            if response.status_code != 200:
                error = response.json().get("error", "Unknown error")
                raise AIError(f"WSL2 TTS generation failed: {error}")

            audio_bytes = response.content
            logger.info("wsl2_tts_generated", text_length=len(text), audio_size=len(audio_bytes))

            return audio_bytes

        except AIError:
            raise
        except Exception as e:
            logger.error("wsl2_tts_error", error=str(e))
            raise AIError(f"WSL2 TTS generation failed: {e}", cause=e)

    async def generate_preview(
        self,
        speaker: Optional[str] = None,
        design_prompt: Optional[str] = None,
        clone_audio_path: Optional[Path] = None,
        clone_audio_text: Optional[str] = None,
        language: str = "en",
    ) -> bytes:
        """
        Generate a preview audio for voice settings.

        Args:
            speaker: Preset speaker name (for preset mode)
            design_prompt: Voice description (for design mode)
            clone_audio_path: Reference audio path (for clone mode - not yet supported)
            clone_audio_text: Reference audio transcript (for clone mode - not yet supported)
            language: Language code

        Returns:
            WAV audio bytes
        """
        preview_text = "Hello! This is a preview of how I will sound when speaking to you."

        # Determine mode based on which parameters are provided
        if design_prompt:
            mode = "design"
            instruct = design_prompt
            speaker_name = "Vivian"  # Not used in design mode
        else:
            mode = "preset"
            speaker_name = speaker or "Vivian"
            instruct = ""

        language_name = self.LANGUAGE_MAP.get(language, "English")

        logger.info("wsl2_tts_preview", mode=mode, speaker=speaker_name if mode == "preset" else None)

        # Ensure server is running
        if not await self._ensure_server_running():
            raise AIError("WSL2 TTS server is not available and could not be started")

        try:
            client = await self._get_client()

            response = await client.post(
                f"{self.server_url}/generate",
                json={
                    "text": preview_text,
                    "mode": mode,
                    "speaker": speaker_name,
                    "language": language_name,
                    "instruct": instruct,
                },
            )

            if response.status_code != 200:
                error = response.json().get("error", "Unknown error")
                raise AIError(f"WSL2 TTS preview failed: {error}")

            return response.content

        except AIError:
            raise
        except Exception as e:
            logger.error("wsl2_tts_preview_error", error=str(e))
            raise AIError(f"WSL2 TTS preview failed: {e}", cause=e)

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


async def check_wsl2_tts_available() -> Dict[str, Any]:
    """
    Standalone function to check WSL2 TTS availability.
    """
    provider = WSL2TTSProvider()
    try:
        return await provider.check_availability()
    finally:
        await provider.close()
