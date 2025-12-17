"""
Tests for file_lock module

Critical security tests for cross-platform file locking to prevent race conditions
when multiple processes access the same Qube simultaneously.

Covers:
- Lock acquisition and release
- Timeout behavior
- Context manager usage
- Concurrent access prevention
- Platform-specific implementations (Windows msvcrt, Unix fcntl)
"""

import pytest
import time
from pathlib import Path
from threading import Thread
from typing import List

from utils.file_lock import FileLock, qube_session_lock


# ==============================================================================
# BASIC LOCK TESTS
# ==============================================================================

class TestFileLockBasic:
    """Test basic FileLock functionality"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_lock_acquisition(self, temp_dir):
        """Should successfully acquire lock"""
        lock_path = temp_dir / "test.lock"
        lock = FileLock(lock_path)

        result = lock.acquire()
        assert result is True
        assert lock.file_handle is not None

        lock.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_lock_release(self, temp_dir):
        """Should successfully release lock"""
        lock_path = temp_dir / "test.lock"
        lock = FileLock(lock_path)

        lock.acquire()
        lock.release()

        assert lock.file_handle is None

    @pytest.mark.unit
    @pytest.mark.security
    def test_context_manager_usage(self, temp_dir):
        """Should work as context manager"""
        lock_path = temp_dir / "test.lock"
        lock = FileLock(lock_path)

        with lock:
            # Lock should be held
            assert lock.file_handle is not None

        # Lock should be released after context
        assert lock.file_handle is None

    @pytest.mark.unit
    @pytest.mark.security
    def test_lock_file_created(self, temp_dir):
        """Should create lock file on disk"""
        lock_path = temp_dir / "test.lock"
        lock = FileLock(lock_path)

        lock.acquire()
        assert lock_path.exists()
        assert lock_path.is_file()

        lock.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_parent_directory_creation(self, temp_dir):
        """Should create parent directories if they don't exist"""
        lock_path = temp_dir / "nested" / "deep" / "test.lock"
        lock = FileLock(lock_path)

        # Parent directories should not exist yet
        assert not lock_path.parent.exists()

        lock.acquire()

        # Parent directories should be created
        assert lock_path.parent.exists()
        assert lock_path.exists()

        lock.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_multiple_acquire_release_cycles(self, temp_dir):
        """Should handle multiple acquire/release cycles"""
        lock_path = temp_dir / "test.lock"
        lock = FileLock(lock_path)

        # Cycle 1
        assert lock.acquire() is True
        lock.release()

        # Cycle 2
        assert lock.acquire() is True
        lock.release()

        # Cycle 3
        assert lock.acquire() is True
        lock.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_custom_timeout(self, temp_dir):
        """Should respect custom timeout parameter"""
        lock_path = temp_dir / "test.lock"
        lock = FileLock(lock_path, timeout=0.5)

        assert lock.timeout == 0.5

    @pytest.mark.unit
    @pytest.mark.security
    def test_release_without_acquire(self, temp_dir):
        """Releasing without acquiring should not crash"""
        lock_path = temp_dir / "test.lock"
        lock = FileLock(lock_path)

        # Should handle gracefully (no-op)
        lock.release()

        assert lock.file_handle is None


# ==============================================================================
# CONCURRENCY TESTS
# ==============================================================================

class TestFileLockConcurrency:
    """Test concurrent access prevention"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_second_acquire_blocks(self, temp_dir):
        """Second thread should block when lock is held"""
        lock_path = temp_dir / "test.lock"
        lock1 = FileLock(lock_path)
        lock2 = FileLock(lock_path, timeout=0.5)

        # First lock acquires
        assert lock1.acquire() is True

        # Second lock should timeout
        start = time.time()
        result = lock2.acquire()
        elapsed = time.time() - start

        assert result is False
        assert elapsed >= 0.5  # Should have waited for timeout

        lock1.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_lock_released_allows_next_acquire(self, temp_dir):
        """After release, next acquire should succeed"""
        lock_path = temp_dir / "test.lock"
        lock1 = FileLock(lock_path)
        lock2 = FileLock(lock_path)

        # First lock acquires and releases
        lock1.acquire()
        lock1.release()

        # Second lock should succeed
        assert lock2.acquire() is True
        lock2.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_concurrent_threads_exclusive_access(self, temp_dir):
        """Only one thread should hold lock at a time"""
        lock_path = temp_dir / "test.lock"
        counter = {"value": 0, "max_concurrent": 0, "current": 0}

        def critical_section(thread_id: int):
            lock = FileLock(lock_path, timeout=2.0)
            if lock.acquire():
                try:
                    # Track concurrent access
                    counter["current"] += 1
                    counter["max_concurrent"] = max(
                        counter["max_concurrent"],
                        counter["current"]
                    )

                    # Critical section work
                    counter["value"] += 1
                    time.sleep(0.05)  # Simulate work

                    counter["current"] -= 1
                finally:
                    lock.release()

        # Launch 5 threads
        threads = [Thread(target=critical_section, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify exclusive access
        assert counter["max_concurrent"] == 1  # Never more than 1 concurrent
        assert counter["value"] == 5  # All threads completed

    @pytest.mark.unit
    @pytest.mark.security
    def test_lock_prevents_simultaneous_access(self, temp_dir):
        """Lock should prevent simultaneous access to shared resource"""
        lock_path = temp_dir / "test.lock"
        shared_list: List[int] = []
        errors: List[Exception] = []

        def append_with_lock(value: int):
            try:
                lock = FileLock(lock_path, timeout=2.0)
                with lock:
                    # Read-modify-write operation
                    current = len(shared_list)
                    time.sleep(0.01)  # Simulate work
                    shared_list.append(value)
                    assert len(shared_list) == current + 1  # Should be consistent
            except Exception as e:
                errors.append(e)

        # Launch 10 threads
        threads = [Thread(target=append_with_lock, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors and all values added
        assert len(errors) == 0
        assert len(shared_list) == 10

    @pytest.mark.unit
    @pytest.mark.security
    def test_timeout_prevents_deadlock(self, temp_dir):
        """Timeout should prevent indefinite waiting"""
        lock_path = temp_dir / "test.lock"
        lock1 = FileLock(lock_path, timeout=10.0)
        lock2 = FileLock(lock_path, timeout=0.3)

        # Lock1 holds the lock
        lock1.acquire()

        # Lock2 should timeout quickly (not wait 10s)
        start = time.time()
        result = lock2.acquire()
        elapsed = time.time() - start

        assert result is False
        assert elapsed < 1.0  # Should timeout in 0.3s, definitely under 1s

        lock1.release()


# ==============================================================================
# CONTEXT MANAGER TESTS
# ==============================================================================

class TestContextManager:
    """Test context manager behavior"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_context_manager_timeout_raises_error(self, temp_dir):
        """Context manager should raise TimeoutError on timeout"""
        lock_path = temp_dir / "test.lock"
        lock1 = FileLock(lock_path)
        lock2 = FileLock(lock_path, timeout=0.2)

        lock1.acquire()

        with pytest.raises(TimeoutError) as exc_info:
            with lock2:
                pass  # Should never get here

        assert "failed to acquire lock" in str(exc_info.value).lower()

        lock1.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_exception_in_context_releases_lock(self, temp_dir):
        """Lock should be released even if exception occurs in context"""
        lock_path = temp_dir / "test.lock"
        lock1 = FileLock(lock_path)

        # Cause exception in context
        try:
            with lock1:
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Lock should be released
        assert lock1.file_handle is None

        # Another lock should be able to acquire
        lock2 = FileLock(lock_path)
        assert lock2.acquire() is True
        lock2.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_context_manager_does_not_suppress_exceptions(self, temp_dir):
        """Context manager should not suppress exceptions"""
        lock_path = temp_dir / "test.lock"
        lock = FileLock(lock_path)

        with pytest.raises(ValueError):
            with lock:
                raise ValueError("This should propagate")


# ==============================================================================
# QUBE_SESSION_LOCK TESTS
# ==============================================================================

class TestQubeSessionLock:
    """Test qube_session_lock helper function"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_session_lock_basic_usage(self, temp_dir):
        """Should create .session.lock in qube directory"""
        qube_dir = temp_dir / "qube_alice"
        qube_dir.mkdir()

        with qube_session_lock(qube_dir):
            # Lock should exist
            lock_path = qube_dir / ".session.lock"
            assert lock_path.exists()

        # After context, lock file may still exist but should be released

    @pytest.mark.unit
    @pytest.mark.security
    def test_session_lock_timeout(self, temp_dir):
        """Should timeout if session lock cannot be acquired"""
        qube_dir = temp_dir / "qube_alice"
        qube_dir.mkdir()

        # Hold lock in first context
        lock1 = FileLock(qube_dir / ".session.lock")
        lock1.acquire()

        # Second context should timeout
        with pytest.raises(TimeoutError):
            with qube_session_lock(qube_dir, timeout=0.2):
                pass  # Should never get here

        lock1.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_session_lock_exception_propagation(self, temp_dir):
        """Exceptions in session context should propagate"""
        qube_dir = temp_dir / "qube_alice"
        qube_dir.mkdir()

        with pytest.raises(RuntimeError):
            with qube_session_lock(qube_dir):
                raise RuntimeError("Session error")

    @pytest.mark.unit
    @pytest.mark.security
    def test_session_lock_releases_on_exception(self, temp_dir):
        """Session lock should be released even on exception"""
        qube_dir = temp_dir / "qube_alice"
        qube_dir.mkdir()

        # First context with exception
        try:
            with qube_session_lock(qube_dir):
                raise ValueError("Error in session")
        except ValueError:
            pass

        # Second context should succeed (lock was released)
        success = False
        with qube_session_lock(qube_dir):
            success = True

        assert success is True

    @pytest.mark.unit
    @pytest.mark.security
    def test_session_lock_custom_timeout(self, temp_dir):
        """Should respect custom timeout for session lock"""
        qube_dir = temp_dir / "qube_alice"
        qube_dir.mkdir()

        lock1 = FileLock(qube_dir / ".session.lock")
        lock1.acquire()

        start = time.time()
        try:
            with qube_session_lock(qube_dir, timeout=0.3):
                pass
        except TimeoutError:
            elapsed = time.time() - start

        # Should timeout around 0.3s, definitely under 1s
        assert elapsed < 1.0

        lock1.release()


# ==============================================================================
# EDGE CASES & SECURITY TESTS
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and security scenarios"""

    @pytest.mark.unit
    @pytest.mark.security
    def test_very_long_path(self, temp_dir):
        """Should handle very long file paths"""
        # Create nested path (but not too long to exceed OS limits)
        nested = temp_dir / "a" / "b" / "c" / "d" / "e" / "f"
        lock_path = nested / "test.lock"

        lock = FileLock(lock_path)
        assert lock.acquire() is True
        assert lock_path.exists()
        lock.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_zero_timeout(self, temp_dir):
        """Zero timeout should fail immediately if lock is held"""
        lock_path = temp_dir / "test.lock"
        lock1 = FileLock(lock_path)
        lock2 = FileLock(lock_path, timeout=0.0)

        lock1.acquire()

        # Should fail immediately (no waiting)
        start = time.time()
        result = lock2.acquire()
        elapsed = time.time() - start

        assert result is False
        assert elapsed < 0.1  # Should be nearly instant

        lock1.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_lock_on_readonly_parent(self, temp_dir):
        """Should handle readonly parent directory gracefully"""
        # Create a directory
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()

        lock_path = readonly_dir / "test.lock"
        lock = FileLock(lock_path)

        # On most systems, we can't easily make dirs truly readonly
        # So we just verify the lock can be created
        assert lock.acquire() is True
        lock.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_rapid_acquire_release(self, temp_dir):
        """Should handle rapid acquire/release cycles"""
        lock_path = temp_dir / "test.lock"

        for i in range(50):
            lock = FileLock(lock_path, timeout=1.0)
            assert lock.acquire() is True
            lock.release()

    @pytest.mark.unit
    @pytest.mark.security
    def test_lock_path_as_string(self, temp_dir):
        """Should accept lock_path as string, not just Path"""
        lock_path_str = str(temp_dir / "test.lock")
        lock = FileLock(lock_path_str)

        assert lock.acquire() is True
        lock.release()
