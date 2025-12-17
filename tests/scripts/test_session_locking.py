"""
Test file locking for session race condition prevention

Tests that multiple processes cannot simultaneously:
- Start sessions
- Anchor sessions to the chain
"""

import pytest
import tempfile
import time
import multiprocessing
from pathlib import Path

from utils.file_lock import FileLock, qube_session_lock


def test_file_lock_basic():
    """Test basic file lock acquisition and release"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / ".session.lock"
        lock = FileLock(lock_path, timeout=1.0)

        # Should acquire successfully
        assert lock.acquire() is True

        # Release
        lock.release()


def test_file_lock_contention():
    """Test that second process cannot acquire lock while first holds it"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / ".session.lock"

        lock1 = FileLock(lock_path, timeout=0.5)
        lock2 = FileLock(lock_path, timeout=0.5)

        # First lock acquires
        assert lock1.acquire() is True

        # Second lock should timeout (cannot acquire while first holds)
        assert lock2.acquire() is False

        # Release first lock
        lock1.release()

        # Now second lock should acquire
        assert lock2.acquire() is True
        lock2.release()


def test_file_lock_context_manager():
    """Test file lock with context manager"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / ".session.lock"

        # Should work in context manager
        with FileLock(lock_path, timeout=1.0):
            # Lock is held
            pass

        # Lock should be released after exiting context


def test_qube_session_lock_context():
    """Test qube_session_lock helper function"""
    with tempfile.TemporaryDirectory() as tmpdir:
        qube_dir = Path(tmpdir)

        # Should create lock file in qube directory
        with qube_session_lock(qube_dir):
            # Verify lock file exists
            lock_file = qube_dir / ".session.lock"
            assert lock_file.exists()


def worker_acquire_lock(lock_path, delay, results_queue):
    """Worker process that tries to acquire lock"""
    lock = FileLock(lock_path, timeout=2.0)

    start_time = time.time()
    acquired = lock.acquire()
    acquire_time = time.time()

    if acquired:
        # Hold lock for specified delay
        time.sleep(delay)
        lock.release()

        results_queue.put({
            'success': True,
            'acquire_time': acquire_time - start_time
        })
    else:
        results_queue.put({
            'success': False,
            'acquire_time': acquire_time - start_time
        })


def test_multiprocess_locking():
    """Test that file locking works across multiple processes"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / ".session.lock"
        results_queue = multiprocessing.Queue()

        # Start first process that holds lock for 1 second
        p1 = multiprocessing.Process(
            target=worker_acquire_lock,
            args=(lock_path, 1.0, results_queue)
        )
        p1.start()

        # Give first process time to acquire lock
        time.sleep(0.1)

        # Start second process that tries to acquire same lock
        p2 = multiprocessing.Process(
            target=worker_acquire_lock,
            args=(lock_path, 0.1, results_queue)
        )
        p2.start()

        # Wait for both processes
        p1.join(timeout=5)
        p2.join(timeout=5)

        # Get results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        # Both should have succeeded
        assert len(results) == 2
        assert all(r['success'] for r in results)

        # Second process should have waited for first
        # (acquire_time should be > 0.9 seconds for at least one process)
        acquire_times = [r['acquire_time'] for r in results]
        assert max(acquire_times) > 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
