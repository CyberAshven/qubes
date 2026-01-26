"""
TTS Server - Persistent background service for fast TTS generation.

Keeps the Qwen3-TTS model loaded in memory to avoid reloading on each request.
Communicates via HTTP on localhost:19532 (QUBES on phone keypad).

Usage:
    python -m audio.tts_server start   # Start server in background
    python -m audio.tts_server stop    # Stop running server
    python -m audio.tts_server status  # Check if server is running
"""

import asyncio
import json
import os
import sys
import signal
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Server configuration
TTS_SERVER_PORT = 19532  # QUBES on phone keypad
TTS_SERVER_HOST = "127.0.0.1"
PID_FILE = Path.home() / ".qubes" / "tts_server.pid"
LOG_FILE = Path.home() / ".qubes" / "tts_server.log"


class TTSServer:
    """Persistent TTS server that keeps model loaded."""

    def __init__(self):
        self.provider = None
        self.model_loaded = False
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start the TTS server."""
        from aiohttp import web

        # Initialize provider and pre-load model
        await self._init_provider()

        # Create web app
        app = web.Application()
        app.router.add_post("/generate", self.handle_generate)
        app.router.add_get("/status", self.handle_status)
        app.router.add_post("/shutdown", self.handle_shutdown)

        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, TTS_SERVER_HOST, TTS_SERVER_PORT)
        await site.start()

        self._log(f"TTS Server started on {TTS_SERVER_HOST}:{TTS_SERVER_PORT}")
        self._log(f"Model loaded: {self.model_loaded}")

        # Write PID file
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        # Cleanup
        await runner.cleanup()
        if PID_FILE.exists():
            PID_FILE.unlink()
        self._log("TTS Server stopped")

    async def _init_provider(self):
        """Initialize TTS provider and pre-load model."""
        try:
            from audio.qwen_tts import Qwen3TTSProvider

            self.provider = Qwen3TTSProvider()

            # Check if model is downloaded
            avail = self.provider.check_availability()
            if not avail.get("available"):
                self._log(f"Qwen3-TTS not available: {avail.get('error')}")
                return

            if not avail.get("models_downloaded"):
                self._log("No Qwen3-TTS models downloaded")
                return

            # Pre-load the CustomVoice model (most common)
            self._log("Loading Qwen3-TTS model...")
            await self.provider.ensure_ready(voice_mode="preset")
            self.model_loaded = True
            self._log("Model loaded successfully!")

        except Exception as e:
            self._log(f"Failed to initialize provider: {e}")

    async def handle_generate(self, request):
        """Handle TTS generation request."""
        from aiohttp import web
        from audio.tts_engine import VoiceConfig
        import time

        try:
            data = await request.json()
            text = data.get("text", "")
            voice_id = data.get("voice_id", "Vivian")
            voice_mode = data.get("voice_mode", "preset")
            language = data.get("language", "en")
            output_path = data.get("output_path")

            self._log(f"Generate request: voice={voice_id}, mode={voice_mode}, text_len={len(text)}")

            if not text:
                return web.json_response({"error": "No text provided"}, status=400)

            if not output_path:
                return web.json_response({"error": "No output_path provided"}, status=400)

            if not self.provider or not self.model_loaded:
                return web.json_response({"error": "Model not loaded"}, status=503)

            # Ensure correct model is loaded for voice mode
            start_time = time.time()
            await self.provider.ensure_ready(voice_mode=voice_mode)
            ready_time = time.time() - start_time
            if ready_time > 1:
                self._log(f"Model ensure_ready took {ready_time:.1f}s")

            # Create voice config
            config = VoiceConfig(
                provider="qwen3",
                voice_id=voice_id,
                voice_mode=voice_mode,
                language=language,
            )

            # Generate audio
            gen_start = time.time()
            result_path = await self.provider.synthesize_file(
                text=text,
                voice_config=config,
                output_path=Path(output_path),
            )
            gen_time = time.time() - gen_start
            self._log(f"Generation complete: {gen_time:.1f}s for {len(text)} chars")

            return web.json_response({
                "success": True,
                "audio_path": str(result_path),
            })

        except Exception as e:
            self._log(f"Generation error: {e}")
            import traceback
            self._log(traceback.format_exc())
            return web.json_response({"error": str(e)}, status=500)

    async def handle_status(self, request):
        """Handle status check request."""
        from aiohttp import web

        return web.json_response({
            "running": True,
            "model_loaded": self.model_loaded,
            "pid": os.getpid(),
        })

    async def handle_shutdown(self, request):
        """Handle shutdown request."""
        from aiohttp import web

        self._shutdown_event.set()
        return web.json_response({"message": "Shutting down"})

    def _log(self, message: str):
        """Log message to file and stdout."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a") as f:
                f.write(log_line + "\n")
        except Exception:
            pass


def is_server_running() -> bool:
    """Check if TTS server is already running."""
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process exists (cross-platform)
        import psutil
        return psutil.pid_exists(pid)
    except (ValueError, ImportError):
        # psutil not available, try HTTP check
        try:
            import httpx
            response = httpx.get(f"{get_server_url()}/status", timeout=1)
            return response.json().get("running", False)
        except Exception:
            pass
    except Exception:
        pass

    # Clean up stale PID file if we couldn't verify
    try:
        PID_FILE.unlink()
    except Exception:
        pass
    return False


def get_server_url() -> str:
    """Get the TTS server URL."""
    return f"http://{TTS_SERVER_HOST}:{TTS_SERVER_PORT}"


async def start_server():
    """Start the TTS server."""
    if is_server_running():
        print("TTS Server is already running")
        return

    server = TTSServer()
    await server.start()


def stop_server():
    """Stop the running TTS server."""
    import httpx

    if not is_server_running():
        print("TTS Server is not running")
        return

    try:
        response = httpx.post(f"{get_server_url()}/shutdown", timeout=5)
        print(f"Server shutdown: {response.json()}")
    except Exception as e:
        print(f"Failed to stop server gracefully: {e}")
        # Force kill
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to PID {pid}")
        except Exception:
            pass


def check_status():
    """Check TTS server status."""
    import httpx

    if not is_server_running():
        print("TTS Server is not running")
        return {"running": False}

    try:
        response = httpx.get(f"{get_server_url()}/status", timeout=2)
        status = response.json()
        print(f"TTS Server status: {status}")
        return status
    except Exception as e:
        print(f"Failed to get status: {e}")
        return {"running": False, "error": str(e)}


async def generate_via_server(
    text: str,
    output_path: str,
    voice_id: str = "Vivian",
    voice_mode: str = "preset",
    language: str = "en",
) -> dict:
    """Generate TTS via the server (client function)."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_server_url()}/generate",
            json={
                "text": text,
                "voice_id": voice_id,
                "voice_mode": voice_mode,
                "language": language,
                "output_path": output_path,
            },
            timeout=120,  # Allow up to 2 minutes for long text
        )
        return response.json()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m audio.tts_server [start|stop|status]")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "start":
        asyncio.run(start_server())
    elif command == "stop":
        stop_server()
    elif command == "status":
        check_status()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python -m audio.tts_server [start|stop|status]")
        sys.exit(1)
