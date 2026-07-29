"""
Atomic operations for lock-free data structures.

Provides thread-safe atomic primitives using Python's multiprocessing
shared memory and atomic operations. For production deployment, this
should be replaced with C/C++ implementation using hardware CAS.
"""

import threading
from typing import TypeVar, Generic
from ctypes import c_int32, c_uint64, c_bool, Structure
import multiprocessing as mp

T = TypeVar("T")


class AtomicInt:
    """
    Thread-safe atomic integer with compare-and-swap operations.

    For production: Replace with C extension using hardware CAS.
    Current implementation uses threading primitives for compatibility.
    """

    def __init__(self, value: int = 0):
        self._value = value
        self._lock = threading.Lock()

    def load(self) -> int:
        """Atomically load the current value."""
        with self._lock:
            return self._value

    def store(self, value: int) -> None:
        """Atomically store a new value."""
        with self._lock:
            self._value = value

    def fetch_add(self, delta: int = 1) -> int:
        """Atomically add delta and return the old value."""
        with self._lock:
            old = self._value
            self._value += delta
            return old

    def compare_exchange(
        self, expected: int, desired: int
    ) -> tuple[bool, int]:
        """
        Compare and swap operation.
        Returns (success, actual_value).
        """
        with self._lock:
            if self._value == expected:
                self._value = desired
                return (True, expected)
            return (False, self._value)

    def increment(self) -> int:
        """Atomically increment by 1 and return new value."""
        with self._lock:
            self._value += 1
            return self._value

    def decrement(self) -> int:
        """Atomically decrement by 1 and return new value."""
        with self._lock:
            self._value -= 1
            return self._value


class AtomicBool:
    """
    Thread-safe atomic boolean.
    """

    def __init__(self, value: bool = False):
        self._value = value
        self._lock = threading.Lock()

    def load(self) -> bool:
        """Atomically load the current value."""
        with self._lock:
            return self._value

    def store(self, value: bool) -> None:
        """Atomically store a new value."""
        with self._lock:
            self._value = value

    def compare_exchange(
        self, expected: bool, desired: bool
    ) -> tuple[bool, bool]:
        """
        Compare and swap operation.
        Returns (success, actual_value).
        """
        with self._lock:
            if self._value == expected:
                self._value = desired
                return (True, expected)
            return (False, self._value)


class CacheLinePad:
    """
    Padding to prevent false sharing across cache lines.
    x86-64 cache lines are 64 bytes.
    """

    __slots__ = ("_pad",)

    def __init__(self):
        # 64 bytes of padding
        self._pad = b"\x00" * 64
