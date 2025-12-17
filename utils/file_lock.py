"""
Cross-platform file locking for session synchronization

Prevents race conditions when multiple processes access the same Qube:
- CLI + GUI simultaneously
- Multiple CLI instances
- Parallel test runners

Uses:
- fcntl (Unix/Linux/macOS)
- msvcrt (Windows)
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from utils.logging import get_logger

logger = get_logger(__name__)

# Platform-specific lock imports
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


class FileLock:
    """
    Cross-platform file lock implementation

    Example:
        lock = FileLock("/path/to/qube_alice/.session.lock")
        with lock:
            # Critical section - only one process can execute this
            session = start_session()
    """

    def __init__(self, lock_path: Path, timeout: float = 5.0):
        """
        Initialize file lock

        Args:
            lock_path: Path to lock file (e.g., qube_dir/.session.lock)
            timeout: Maximum seconds to wait for lock acquisition (default: 5s)
        """
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.file_handle: Optional[object] = None

    def acquire(self) -> bool:
        """
        Acquire the lock (blocking with timeout)

        Returns:
            True if lock acquired, False if timeout
        """
        start_time = time.time()

        # Ensure parent directory exists
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        while True:
            try:
                # Open lock file (create if doesn't exist)
                self.file_handle = open(self.lock_path, 'w')

                # Try to acquire lock
                if sys.platform == "win32":
                    # Windows: Use msvcrt.locking
                    msvcrt.locking(
                        self.file_handle.fileno(),
                        msvcrt.LK_NBLCK,  # Non-blocking lock
                        1
                    )
                else:
                    # Unix/Linux/macOS: Use fcntl
                    fcntl.flock(
                        self.file_handle.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB  # Exclusive, non-blocking
                    )

                # Lock acquired successfully
                logger.debug(
                    "lock_acquired",
                    lock_path=str(self.lock_path),
                    wait_time=time.time() - start_time
                )
                return True

            except (IOError, OSError) as e:
                # Lock is held by another process
                if self.file_handle:
                    self.file_handle.close()
                    self.file_handle = None

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= self.timeout:
                    logger.warning(
                        "lock_timeout",
                        lock_path=str(self.lock_path),
                        timeout=self.timeout
                    )
                    return False

                # Wait a bit before retrying
                time.sleep(0.05)  # 50ms

    def release(self):
        """Release the lock"""
        if self.file_handle:
            try:
                if sys.platform == "win32":
                    # Windows: Unlock
                    msvcrt.locking(
                        self.file_handle.fileno(),
                        msvcrt.LK_UNLCK,
                        1
                    )
                else:
                    # Unix/Linux/macOS: Unlock
                    fcntl.flock(
                        self.file_handle.fileno(),
                        fcntl.LOCK_UN
                    )

                self.file_handle.close()
                logger.debug("lock_released", lock_path=str(self.lock_path))

            except Exception as e:
                logger.error(
                    "lock_release_failed",
                    lock_path=str(self.lock_path),
                    error=str(e)
                )
            finally:
                self.file_handle = None

    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            raise TimeoutError(
                f"Failed to acquire lock on {self.lock_path} "
                f"within {self.timeout} seconds. "
                f"Another process may be accessing this Qube."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
        return False  # Don't suppress exceptions


@contextmanager
def qube_session_lock(qube_dir: Path, timeout: float = 5.0):
    """
    Context manager for Qube session operations

    Usage:
        with qube_session_lock(qube.storage_path):
            qube.start_session()
            asyncio.run(qube.current_session.anchor_to_chain())

    Args:
        qube_dir: Path to Qube storage directory
        timeout: Lock acquisition timeout in seconds

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
    """
    lock_path = Path(qube_dir) / ".session.lock"
    lock = FileLock(lock_path, timeout=timeout)

    with lock:
        yield
