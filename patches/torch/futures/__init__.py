"""
torch.futures stub — provides a minimal Future class so TTS/model code
that does `from torch.futures import Future` doesn't crash.

This file will be replaced by the real module if the update package contains it.
"""
import threading
from typing import Any, Callable, Generic, List, Optional, TypeVar

T = TypeVar("T")


class Future(Generic[T]):
    """Minimal stub for torch.futures.Future."""

    def __init__(self) -> None:
        self._result: Optional[Any] = None
        self._exception: Optional[BaseException] = None
        self._done = False
        self._callbacks: List[Callable] = []
        self._lock = threading.Lock()
        self._event = threading.Event()

    def done(self) -> bool:
        return self._done

    def result(self) -> T:
        self._event.wait()
        if self._exception is not None:
            raise self._exception
        return self._result  # type: ignore[return-value]

    def set_result(self, result: T) -> None:
        with self._lock:
            self._result = result
            self._done = True
        self._event.set()
        for cb in self._callbacks:
            try:
                cb(self)
            except Exception:
                pass

    def set_exception(self, exception: BaseException) -> None:
        with self._lock:
            self._exception = exception
            self._done = True
        self._event.set()

    def add_done_callback(self, callback: Callable) -> None:
        with self._lock:
            if self._done:
                callback(self)
            else:
                self._callbacks.append(callback)

    def wait(self) -> "Future[T]":
        self._event.wait()
        return self

    def then(self, callback: Callable) -> "Future":
        fut: Future = Future()
        def _cb(f: "Future") -> None:
            try:
                fut.set_result(callback(f))
            except Exception as e:
                fut.set_exception(e)
        self.add_done_callback(_cb)
        return fut


def collect_all(futures: List[Future]) -> Future:
    """Wait for all futures and return a future of list of results."""
    result_future: Future = Future()
    if not futures:
        result_future.set_result([])
        return result_future
    results = [None] * len(futures)
    remaining = [len(futures)]
    lock = threading.Lock()
    for i, f in enumerate(futures):
        def _cb(fut, idx=i):
            with lock:
                results[idx] = fut.result()
                remaining[0] -= 1
                if remaining[0] == 0:
                    result_future.set_result(results)
        f.add_done_callback(_cb)
    return result_future
