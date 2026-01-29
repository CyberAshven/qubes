"""
WSL2 TTS Server Manager

Manages the lifecycle of the WSL2 TTS server:
- Starts server as hidden background process when app starts
- Health monitoring with automatic restart on crash
- Warmup request after startup for fast first response
- Clean shutdown when app closes

Server runs at http://localhost:19532 (QUBES on phone keypad).
"""

import asyncio
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import threading

from utils.logging import get_logger

logger = get_logger(__name__)

# Server configuration
WSL2_TTS_SERVER_URL = "http://localhost:19532"
WSL2_DISTRO = "Ubuntu-22.04"
WSL2_SERVER_PATH = "~/qubes-tts/tts_server.py"
WSL2_VENV_PATH = "~/qubes-tts/venv"

# Health check interval
HEALTH_CHECK_INTERVAL = 30  # seconds
MAX_RESTART_ATTEMPTS = 3
RESTART_COOLDOWN = 60  # seconds between restart attempts


class ServerState(Enum):
    """Current state of the WSL2 TTS server."""
    STOPPED = "stopped"
    STARTING = "starting"
    LOADING_MODEL = "loading_model"
    WARMING_UP = "warming_up"
    READY = "ready"
    ERROR = "error"


@dataclass
class ServerStatus:
    """Status information for the WSL2 TTS server."""
    state: ServerState = ServerState.STOPPED
    message: str = ""
    progress: int = 0  # 0-100 for loading/warmup progress
    error: Optional[str] = None
    model_loaded: bool = False
    optimized: bool = False  # Triton optimization active
    gpu_name: Optional[str] = None
    started_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    restart_count: int = 0


# Global state
_server_process: Optional[subprocess.Popen] = None
_server_status: ServerStatus = ServerStatus()
_manually_stopped: bool = False
_health_check_task: Optional[asyncio.Task] = None
_status_callbacks: list[Callable[[ServerStatus], None]] = []
_lock = threading.Lock()


def get_server_status() -> Dict[str, Any]:
    """Get current server status as a dictionary for the UI.

    NOTE: Since each Tauri command spawns a new Python process, the in-memory
    state doesn't persist. We need to actually check the server via HTTP.
    """
    # Actually check the server instead of relying on in-memory state
    try:
        import httpx
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{WSL2_TTS_SERVER_URL}/status")
            if response.status_code == 200:
                health = response.json()
                model_loaded = health.get("model_loaded", False)
                return {
                    "state": "ready",
                    "message": "TTS server ready" + (" (model loads on first request)" if not model_loaded else ""),
                    "progress": 100,
                    "error": None,
                    "model_loaded": model_loaded,
                    "optimized": health.get("optimized", False),
                    "gpu_name": health.get("gpu"),
                    "started_at": None,
                    "ready_at": None,
                    "restart_count": 0,
                }
    except Exception:
        pass  # Server not responding

    # Server not responding - return stopped state
    return {
        "state": "stopped",
        "message": "Server not running",
        "progress": 0,
        "error": None,
        "model_loaded": False,
        "optimized": False,
        "gpu_name": None,
        "started_at": None,
        "ready_at": None,
        "restart_count": 0,
    }


def _update_status(
    state: Optional[ServerState] = None,
    message: Optional[str] = None,
    progress: Optional[int] = None,
    error: Optional[str] = None,
    **kwargs
):
    """Update server status and notify callbacks."""
    global _server_status

    with _lock:
        if state is not None:
            _server_status.state = state
        if message is not None:
            _server_status.message = message
        if progress is not None:
            _server_status.progress = progress
        if error is not None:
            _server_status.error = error
        for key, value in kwargs.items():
            if hasattr(_server_status, key):
                setattr(_server_status, key, value)

        status_copy = ServerStatus(
            state=_server_status.state,
            message=_server_status.message,
            progress=_server_status.progress,
            error=_server_status.error,
            model_loaded=_server_status.model_loaded,
            optimized=_server_status.optimized,
            gpu_name=_server_status.gpu_name,
            started_at=_server_status.started_at,
            ready_at=_server_status.ready_at,
            restart_count=_server_status.restart_count,
        )

    # Notify callbacks (outside lock to avoid deadlock)
    for callback in _status_callbacks:
        try:
            callback(status_copy)
        except Exception as e:
            logger.error("status_callback_error", error=str(e))


def register_status_callback(callback: Callable[[ServerStatus], None]):
    """Register a callback to be notified of status changes."""
    _status_callbacks.append(callback)


def unregister_status_callback(callback: Callable[[ServerStatus], None]):
    """Unregister a status callback."""
    if callback in _status_callbacks:
        _status_callbacks.remove(callback)


async def check_wsl2_available() -> bool:
    """Check if WSL2 with Ubuntu is available."""
    try:
        process = await asyncio.create_subprocess_exec(
            "wsl", "-l", "-v",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        output = stdout.decode('utf-8', errors='replace').replace('\x00', '')
        return "Ubuntu" in output and process.returncode == 0
    except Exception as e:
        logger.debug("wsl2_check_failed", error=str(e))
        return False


async def check_wsl2_tts_setup() -> bool:
    """Check if WSL2 TTS is set up (venv and dependencies exist)."""
    try:
        process = await asyncio.create_subprocess_exec(
            "wsl", "-d", WSL2_DISTRO, "--",
            "bash", "-c", f"test -f {WSL2_VENV_PATH}/bin/python && echo 'exists'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        return "exists" in stdout.decode()
    except Exception:
        return False


async def _check_server_health() -> Dict[str, Any]:
    """Check if the server is responding and get its status."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{WSL2_TTS_SERVER_URL}/status")
            return response.json()
    except Exception:
        return {}


async def start_server(force: bool = False) -> bool:
    """
    Start the WSL2 TTS server as a hidden background process.

    Args:
        force: If True, start even if manually stopped

    Returns:
        True if server started successfully
    """
    global _server_process, _manually_stopped, _health_check_task

    # Check if manually stopped
    if _manually_stopped and not force:
        logger.debug("server_start_blocked_manual_stop")
        return False

    # Check if already starting/loading - don't spawn multiple instances
    with _lock:
        current_state = _server_status.state
    if current_state in (ServerState.STARTING, ServerState.LOADING_MODEL, ServerState.WARMING_UP):
        logger.debug("server_start_blocked_already_starting", state=current_state.value)
        return True  # Return True - startup is in progress

    # Check if already running (server responds to /status, even if model still loading)
    health = await _check_server_health()
    if health.get("running"):
        # Server is responding - don't start another one!
        if health.get("model_loaded"):
            _update_status(
                state=ServerState.READY,
                message="Server already running",
                progress=100,
                model_loaded=True,
                optimized=health.get("optimized", False),
                gpu_name=health.get("gpu"),
            )
        else:
            _update_status(
                state=ServerState.LOADING_MODEL,
                message="Server starting, model loading...",
                progress=50,
                model_loaded=False,
            )
        logger.info("wsl2_server_already_running", model_loaded=health.get("model_loaded", False))

        # Start health check if not running
        if _health_check_task is None or _health_check_task.done():
            _health_check_task = asyncio.create_task(_health_check_loop())

        return True

    # Check if WSL2 TTS is set up
    if not await check_wsl2_available():
        _update_status(
            state=ServerState.ERROR,
            message="WSL2 not available",
            error="WSL2 with Ubuntu is not installed",
        )
        return False

    if not await check_wsl2_tts_setup():
        _update_status(
            state=ServerState.ERROR,
            message="WSL2 TTS not set up",
            error="Run the WSL2 TTS setup first",
        )
        return False

    # Reset manual stop flag
    _manually_stopped = False

    _update_status(
        state=ServerState.STARTING,
        message="Starting WSL2 TTS server...",
        progress=5,
        error=None,
        started_at=datetime.now(),
    )

    logger.info("wsl2_server_starting")

    try:
        # Kill any existing TTS server processes to prevent port conflicts
        if sys.platform == "win32":
            subprocess.run(
                ["wsl", "-d", WSL2_DISTRO, "pkill", "-9", "-f", "tts_server.py"],
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            await asyncio.sleep(2)  # Wait for processes to fully terminate

            # Start server in WSL2 as a hidden child process
            # CREATE_NO_WINDOW hides the console, while keeping it as a child
            # The server dies when the app closes (cleaned up by cleanup())
            start_cmd = (
                "cd /home/bit_faced/qubes-tts && "
                "exec /home/bit_faced/qubes-tts/venv/bin/python -u tts_server.py"
            )
            _server_process = subprocess.Popen(
                ["wsl", "-d", WSL2_DISTRO, "bash", "-c", start_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            # On Linux/Mac, just run directly
            cmd = ["bash", "-c", f"cd ~/qubes-tts && source venv/bin/activate && python -u tts_server.py"]
            _server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        logger.info("wsl2_server_process_started", pid=_server_process.pid)

        _update_status(
            state=ServerState.LOADING_MODEL,
            message="Loading TTS model...",
            progress=10,
        )

        # Wait for server to be ready
        max_wait = 180  # 3 minutes max for model loading + JIT
        check_interval = 3
        waited = 0

        while waited < max_wait:
            await asyncio.sleep(check_interval)
            waited += check_interval

            # Check if process died
            if _server_process.poll() is not None:
                _update_status(
                    state=ServerState.ERROR,
                    message="Server process died",
                    error="The TTS server process exited unexpectedly",
                )
                logger.error("wsl2_server_died_during_startup")
                return False

            health = await _check_server_health()

            # Server is ready when it responds, even if model isn't pre-loaded
            # (model loads on first TTS request based on user's variant preference)
            if health.get("running"):
                model_loaded = health.get("model_loaded", False)

                if model_loaded:
                    # Model already loaded - do warmup
                    _update_status(
                        state=ServerState.WARMING_UP,
                        message="Warming up (first request)...",
                        progress=80,
                        model_loaded=True,
                        optimized=health.get("optimized", False),
                        gpu_name=health.get("gpu"),
                    )
                    logger.info("wsl2_server_model_loaded", seconds=waited)
                    await _do_warmup()

                _update_status(
                    state=ServerState.READY,
                    message="TTS server ready" + (" (model loads on first request)" if not model_loaded else ""),
                    progress=100,
                    model_loaded=model_loaded,
                    ready_at=datetime.now(),
                    gpu_name=health.get("gpu"),
                )
                logger.info("wsl2_server_ready", total_seconds=waited, model_loaded=model_loaded)

                # Start health check loop
                if _health_check_task is None or _health_check_task.done():
                    _health_check_task = asyncio.create_task(_health_check_loop())

                return True

            else:
                # Not responding yet - still starting
                progress = min(10 + int((waited / 60) * 20), 29)
                _update_status(
                    message=f"Starting server... ({waited}s)",
                    progress=progress,
                )

        # Timeout
        _update_status(
            state=ServerState.ERROR,
            message="Server startup timeout",
            error=f"Server did not become ready within {max_wait} seconds",
        )
        logger.error("wsl2_server_startup_timeout")
        return False

    except Exception as e:
        _update_status(
            state=ServerState.ERROR,
            message="Failed to start server",
            error=str(e),
        )
        logger.error("wsl2_server_start_error", error=str(e))
        return False


async def _do_warmup():
    """Send a warmup request to trigger JIT compilation."""
    try:
        import httpx
        import tempfile
        import os

        _update_status(message="Warming up TTS (this may take a minute)...")

        warmup_text = "Hello, this is a warmup request to compile the model."

        # Create a temp file for warmup output
        warmup_output = os.path.join(tempfile.gettempdir(), "qubes_tts_warmup.wav")

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{WSL2_TTS_SERVER_URL}/generate",
                json={
                    "text": warmup_text,
                    "voice_mode": "preset",
                    "voice_id": "Vivian",
                    "language": "en",
                    "output_path": warmup_output,
                },
            )

            if response.status_code == 200:
                logger.info("wsl2_server_warmup_complete")
                # Clean up warmup file
                try:
                    if os.path.exists(warmup_output):
                        os.remove(warmup_output)
                except Exception:
                    pass
            else:
                logger.warning("wsl2_server_warmup_failed", status=response.status_code, body=response.text)

    except Exception as e:
        logger.warning("wsl2_server_warmup_error", error=str(e))


async def stop_server(manual: bool = True) -> bool:
    """
    Stop the WSL2 TTS server.

    Args:
        manual: If True, marks as manually stopped to prevent auto-restart

    Returns:
        True if stopped successfully
    """
    global _server_process, _manually_stopped, _health_check_task

    if manual:
        _manually_stopped = True

    # Cancel health check
    if _health_check_task and not _health_check_task.done():
        _health_check_task.cancel()
        try:
            await _health_check_task
        except asyncio.CancelledError:
            pass
        _health_check_task = None

    _update_status(
        state=ServerState.STOPPED,
        message="Stopping server...",
        progress=0,
    )

    try:
        # Kill the wsl process if we have it
        if _server_process and _server_process.poll() is None:
            _server_process.terminate()
            try:
                _server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _server_process.kill()
            _server_process = None

        # Also kill any Python TTS server process in WSL2
        try:
            process = await asyncio.create_subprocess_exec(
                "wsl", "-d", WSL2_DISTRO, "--",
                "pkill", "-f", "tts_server.py",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(process.wait(), timeout=10)
        except Exception:
            pass

        _update_status(
            state=ServerState.STOPPED,
            message="Server stopped" + (" (manual)" if manual else ""),
            model_loaded=False,
        )

        logger.info("wsl2_server_stopped", manual=manual)
        return True

    except Exception as e:
        logger.error("wsl2_server_stop_error", error=str(e))
        return False


async def restart_server() -> bool:
    """Restart the WSL2 TTS server."""
    global _server_status

    with _lock:
        _server_status.restart_count += 1

    logger.info("wsl2_server_restarting", count=_server_status.restart_count)

    await stop_server(manual=False)
    await asyncio.sleep(2)  # Brief pause before restart
    return await start_server(force=True)


async def _health_check_loop():
    """Background loop that monitors server health and restarts if needed."""
    global _manually_stopped

    consecutive_failures = 0
    last_restart_time = 0

    logger.info("wsl2_health_check_started")

    while True:
        try:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

            # Skip if manually stopped
            if _manually_stopped:
                continue

            health = await _check_server_health()

            with _lock:
                _server_status.last_health_check = datetime.now()

            if health.get("running"):
                # Server is healthy (responding to /status)
                consecutive_failures = 0
                model_loaded = health.get("model_loaded", False)

                # Update status if changed
                if _server_status.state != ServerState.READY:
                    _update_status(
                        state=ServerState.READY,
                        message="TTS server ready" + (" (model loads on first request)" if not model_loaded else ""),
                        model_loaded=model_loaded,
                        optimized=health.get("optimized", False),
                        gpu_name=health.get("gpu"),
                    )
            else:
                # Server not responding
                consecutive_failures += 1
                logger.warning("wsl2_health_check_failed", failures=consecutive_failures)

                if consecutive_failures >= 2:
                    # Server seems down, try to restart
                    current_time = time.time()

                    if current_time - last_restart_time < RESTART_COOLDOWN:
                        logger.debug("wsl2_restart_cooldown")
                        continue

                    if _server_status.restart_count >= MAX_RESTART_ATTEMPTS:
                        _update_status(
                            state=ServerState.ERROR,
                            message="Server keeps crashing",
                            error=f"Restarted {MAX_RESTART_ATTEMPTS} times, giving up",
                        )
                        logger.error("wsl2_max_restarts_exceeded")
                        break

                    logger.info("wsl2_auto_restart_triggered")
                    last_restart_time = current_time

                    _update_status(
                        state=ServerState.STARTING,
                        message="Restarting server...",
                    )

                    if await restart_server():
                        consecutive_failures = 0
                    else:
                        _update_status(
                            state=ServerState.ERROR,
                            message="Restart failed",
                            error="Could not restart the TTS server",
                        )

        except asyncio.CancelledError:
            logger.info("wsl2_health_check_cancelled")
            break
        except Exception as e:
            logger.error("wsl2_health_check_error", error=str(e))

    logger.info("wsl2_health_check_stopped")


async def ensure_server_running() -> bool:
    """
    Ensure the server is running, starting it if necessary.

    Returns:
        True if server is available
    """
    # Quick check if already running
    health = await _check_server_health()
    if health.get("model_loaded"):
        return True

    # Not running, try to start
    return await start_server()


# Cleanup function to be called when the app exits
def cleanup():
    """Synchronous cleanup for app exit."""
    global _server_process, _health_check_task

    logger.info("wsl2_server_cleanup")

    # Cancel health check
    if _health_check_task and not _health_check_task.done():
        _health_check_task.cancel()

    # Kill server process
    if _server_process and _server_process.poll() is None:
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()

    # Also try to kill via WSL (sync version)
    try:
        run_kwargs = {
            "capture_output": True,
            "timeout": 5,
        }
        if sys.platform == "win32":
            run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.run(
            ["wsl", "-d", WSL2_DISTRO, "--", "pkill", "-f", "tts_server.py"],
            **run_kwargs
        )
    except Exception:
        pass
