"""
WSL2 TTS Provider

Connects to the Qwen3-TTS server running in WSL2 for near real-time
local TTS generation using torch.compile + Triton optimizations.

Server runs at http://localhost:19532 in WSL2 (QUBES on phone keypad).
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
WSL2_TTS_SERVER_URL = "http://localhost:19532"  # QUBES on phone keypad

# WSL2 distribution and server path
WSL2_DISTRO = "Ubuntu-22.04"
WSL2_SERVER_SCRIPT = "~/qubes-tts/start_server.sh"


async def start_wsl2_tts_server() -> bool:
    """
    Start the TTS server if not already running.

    First tries to start the Windows tts_server.py (preferred, uses local GPU directly).
    Falls back to WSL2 server if Windows server fails.

    Returns:
        True if server started or already running, False on error
    """
    try:
        import httpx
        import sys
        import platform

        # Check if already running
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{WSL2_TTS_SERVER_URL}/status", timeout=2.0)
                if response.json().get("model_loaded"):
                    logger.debug("tts_server_already_running")
                    return True
            except Exception:
                pass  # Server not running, we'll start it

        logger.info("tts_server_starting")

        # On Windows, prefer starting the Windows TTS server directly (faster, uses local GPU)
        if platform.system() == "Windows":
            try:
                # Start the Windows TTS server in background
                # Use pythonw to avoid console window, or python with CREATE_NO_WINDOW
                import subprocess

                # Get the path to tts_server.py
                from pathlib import Path
                server_script = Path(__file__).parent / "tts_server.py"

                if server_script.exists():
                    # Start server as a detached background process
                    # Use CREATE_NO_WINDOW flag to hide console
                    CREATE_NO_WINDOW = 0x08000000
                    process = subprocess.Popen(
                        [sys.executable, str(server_script), "start"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=CREATE_NO_WINDOW,
                    )
                    logger.info("windows_tts_server_starting", pid=process.pid)

                    # Wait for server to be ready
                    max_wait = 120  # 2 minutes max for model loading
                    check_interval = 3
                    waited = 0

                    async with httpx.AsyncClient() as client:
                        while waited < max_wait:
                            await asyncio.sleep(check_interval)
                            waited += check_interval

                            try:
                                response = await client.get(f"{WSL2_TTS_SERVER_URL}/status", timeout=2.0)
                                data = response.json()
                                if data.get("model_loaded"):
                                    logger.info("windows_tts_server_ready", warmup_seconds=waited)
                                    return True
                                elif data.get("running"):
                                    logger.debug("tts_server_loading_model", seconds=waited)
                            except Exception:
                                logger.debug("tts_server_waiting", seconds=waited)

                    logger.warning("windows_tts_server_timeout", waited=max_wait)
                    # Fall through to try WSL2
            except Exception as e:
                logger.warning("windows_tts_server_failed", error=str(e))
                # Fall through to try WSL2

        # Fall back to WSL2 server
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
                    response = await client.get(f"{WSL2_TTS_SERVER_URL}/status", timeout=2.0)
                    if response.json().get("model_loaded"):
                        logger.info("wsl2_tts_server_ready", warmup_seconds=waited)
                        return True
                except Exception:
                    logger.debug("wsl2_tts_server_waiting", seconds=waited)

        logger.error("tts_server_timeout")
        return False

    except Exception as e:
        logger.error("tts_server_start_failed", error=str(e))
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
            # Default timeout of 300s to support voice cloning (can take 2-3+ minutes)
            self._client = httpx.AsyncClient(timeout=300.0)
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
            response = await client.get(f"{self.server_url}/status", timeout=2.0)
            data = response.json()
            # Server is ready if running and has models (loaded or downloaded)
            # Models load on-demand when /generate is called
            if data.get("running"):
                models_downloaded = data.get("models_downloaded", [])
                if models_downloaded or data.get("model_loaded"):
                    logger.debug("wsl2_tts_server_ready", model_loaded=data.get("model_loaded"),
                                models_downloaded=models_downloaded)
                    return True
        except Exception as e:
            logger.debug("wsl2_tts_status_check_failed", error=str(e))

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
            response = await client.get(f"{self.server_url}/status", timeout=5.0)
            data = response.json()

            # Server is available if running and has models downloaded
            # Models load on-demand when /generate is called
            if data.get("running"):
                models_downloaded = data.get("models_downloaded", [])
                if models_downloaded or data.get("model_loaded"):
                    result["available"] = True
                    result["speakers"] = ["Vivian", "Dylan", "Ryan", "Serena", "Eric", "Aiden", "Uncle_Fu", "Ono_Anna", "Sohee"]
                    result["models_downloaded"] = models_downloaded
                else:
                    result["error"] = "Server running but no models downloaded"
            else:
                result["error"] = "Server not ready"

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
                        response = await client.get(f"{self.server_url}/status", timeout=5.0)
                        if response.json().get("model_loaded"):
                            result["available"] = True
                            result["speakers"] = ["Vivian", "Dylan", "Ryan", "Serena", "Eric", "Aiden", "Uncle_Fu", "Ono_Anna", "Sohee"]
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

        NOTE: Caller should check availability before calling this method.
        We skip the server startup check here to avoid redundant 2-3 minute waits.
        """
        import tempfile

        # Quick status check only - don't try to start server (caller already checked)
        # Models load on-demand, so just verify server is running
        try:
            client = await self._get_client()
            response = await client.get(f"{self.server_url}/status", timeout=5.0)
            data = response.json()
            if not data.get("running"):
                raise AIError("WSL2 TTS server is not running")
            # Model will load on-demand when we call /generate
        except AIError:
            raise
        except Exception as e:
            raise AIError(f"WSL2 TTS server is not responding: {e}")

        speaker = voice_config.voice_id or "Vivian"
        language = self.LANGUAGE_MAP.get(voice_config.language or "en", "English")
        instruct = voice_config.voice_design_prompt or ""

        # Determine mode based on voice_mode or presence of design prompt
        voice_mode = getattr(voice_config, 'voice_mode', None) or "preset"
        if voice_mode == "cloned":
            mode = "cloned"
        elif voice_mode == "designed" or (instruct and voice_mode != "preset"):
            mode = "designed"
        else:
            mode = "preset"

        import time
        start_time = time.time()
        logger.info("wsl2_tts_generating", text_length=len(text), speaker=speaker, mode=mode)

        try:
            client = await self._get_client()

            # Create temp output file
            temp_dir = Path(tempfile.gettempdir())
            output_path = temp_dir / f"wsl2_tts_output_{voice_config.language or 'en'}.wav"

            # Build request payload
            # Get model variant from voice config (default to 1.7B)
            model_variant = getattr(voice_config, 'model_variant', None) or "1.7B"

            payload = {
                "text": text,
                "voice_mode": mode,
                "voice_id": speaker,
                "language": language,
                "output_path": str(output_path),
                "model_variant": model_variant,
            }

            # Add clone parameters if in clone mode
            if mode == "cloned":
                clone_audio_path = getattr(voice_config, 'clone_audio_path', None)
                clone_audio_text = getattr(voice_config, 'clone_audio_text', None)

                if clone_audio_path:
                    # Convert Windows path to WSL path if needed
                    clone_path_str = str(clone_audio_path)
                    if clone_path_str[1:3] == ":\\" or clone_path_str[1:3] == ":/":
                        # Convert C:\path to /mnt/c/path for WSL
                        clone_path_str = "/mnt/" + clone_path_str[0].lower() + clone_path_str[2:].replace("\\", "/")
                    payload["clone_audio_path"] = clone_path_str
                    payload["clone_audio_text"] = clone_audio_text or ""
                    logger.info("wsl2_tts_clone_mode", clone_path=clone_path_str)
                else:
                    raise AIError("Voice cloning requires clone_audio_path")
            elif mode == "designed":
                payload["instruct"] = instruct

            response = await client.post(
                f"{self.server_url}/generate",
                json=payload,
                timeout=300.0,  # 5 minutes - voice cloning can take 2-3+ minutes
            )

            if response.status_code != 200:
                error = response.json().get("error", "Unknown error")
                raise AIError(f"WSL2 TTS generation failed: {error}")

            # Read the generated file
            result = response.json()
            audio_path = result.get("audio_path")
            if audio_path and Path(audio_path).exists():
                audio_bytes = Path(audio_path).read_bytes()
                elapsed = time.time() - start_time
                logger.info("wsl2_tts_generated", text_length=len(text), audio_size=len(audio_bytes),
                           elapsed_seconds=round(elapsed, 2), mode=mode, speaker=speaker)
                return audio_bytes
            else:
                raise AIError(f"Generated audio file not found: {audio_path}")

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
            clone_audio_path: Reference audio path (for clone mode)
            clone_audio_text: Reference audio transcript (for clone mode)
            language: Language code

        Returns:
            WAV audio bytes
        """
        import tempfile

        # Localized preview texts
        preview_texts = {
            "en": "Hello! This is a preview of how I will sound when speaking to you.",
            "zh": "你好！这是我说话声音的预览。",
            "ja": "こんにちは！これは私の声のプレビューです。",
            "ko": "안녕하세요! 이것은 제 목소리 미리보기입니다.",
            "de": "Hallo! Dies ist eine Vorschau meiner Stimme.",
            "fr": "Bonjour! Ceci est un aperçu de ma voix.",
            "ru": "Привет! Это предварительный просмотр моего голоса.",
            "pt": "Olá! Esta é uma prévia da minha voz.",
            "es": "¡Hola! Esta es una vista previa de mi voz.",
            "it": "Ciao! Questa è un'anteprima della mia voce.",
        }
        preview_text = preview_texts.get(language, preview_texts["en"])

        # Determine mode based on which parameters are provided
        if clone_audio_path and clone_audio_text:
            mode = "cloned"
            speaker_name = "Vivian"  # Not used in clone mode
            instruct = ""
        elif design_prompt:
            mode = "designed"
            instruct = design_prompt
            speaker_name = "Vivian"  # Not used in design mode
        else:
            mode = "preset"
            speaker_name = speaker or "Vivian"
            instruct = ""

        language_name = self.LANGUAGE_MAP.get(language, "English")

        logger.info("wsl2_tts_preview_start", mode=mode, speaker=speaker_name if mode == "preset" else None,
                    design_prompt=instruct[:50] if instruct else None,
                    clone_audio=str(clone_audio_path) if clone_audio_path else None)

        # Ensure server is running
        if not await self._ensure_server_running():
            raise AIError("WSL2 TTS server is not available and could not be started")

        try:
            client = await self._get_client()

            # Create temp output file
            temp_dir = Path(tempfile.gettempdir())
            output_path = temp_dir / f"wsl2_preview_{language}.wav"

            # Build request payload
            payload = {
                "text": preview_text,
                "voice_mode": mode,
                "voice_id": speaker_name,
                "language": language_name,
                "output_path": str(output_path),
                "instruct": instruct,  # Design prompt for voice design mode
            }

            # Add clone parameters if in clone mode
            if mode == "cloned":
                # Convert Windows path to WSL path if needed (any drive letter)
                clone_path_str = str(clone_audio_path)
                if len(clone_path_str) >= 2 and clone_path_str[1] == ':' and clone_path_str[0].isalpha():
                    # Convert X:\path to /mnt/x/path for WSL
                    clone_path_str = "/mnt/" + clone_path_str[0].lower() + clone_path_str[2:].replace("\\", "/")
                payload["clone_audio_path"] = clone_path_str
                payload["clone_audio_text"] = clone_audio_text
                logger.info("wsl2_tts_clone_path", original=str(clone_audio_path), converted=clone_path_str)

            logger.info("wsl2_tts_preview_sending", url=f"{self.server_url}/generate",
                        voice_mode=payload.get("voice_mode"), instruct=payload.get("instruct", "")[:50] if payload.get("instruct") else None)

            response = await client.post(
                f"{self.server_url}/generate",
                json=payload,
                timeout=300.0,  # 5 minutes - voice cloning can take 2-3+ minutes
            )

            if response.status_code != 200:
                error = response.json().get("error", "Unknown error")
                raise AIError(f"WSL2 TTS preview failed: {error}")

            # Read the generated file
            result = response.json()
            audio_path = result.get("audio_path")
            if audio_path and Path(audio_path).exists():
                return Path(audio_path).read_bytes()
            else:
                raise AIError(f"Generated audio file not found: {audio_path}")

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
