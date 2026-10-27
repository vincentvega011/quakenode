"""Deterministic random streams for fault injection and the synthetic generator.

Only `random.Random(seed).random()` is used: CPython documents that this stream is reproducible for a given integer
seed across versions (other random-module algorithms may change). Gaussian and exponential variates are built from
it, so patterns are identical on Python 3.10, 3.11 and 3.12.
"""

from __future__ import annotations

import hashlib
import math
import random


def derive_seed(*parts: object) -> int:
    """Stable 63-bit integer seed from arbitrary parts (hash of their reprs)."""
    digest = hashlib.sha256("|".join(repr(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") >> 1


class Stream:
    """A seeded stream of uniform, normal and exponential variates."""

    def __init__(self, seed: int) -> None:
        self._r = random.Random(seed)

    def uniform(self) -> float:
        """Uniform on [0, 1)."""
        return self._r.random()

    def bernoulli(self, p: float) -> bool:
        return self._r.random() < p

    def normal(self) -> float:
        """Standard normal by Box-Muller (one variate per call; the second is discarded for simplicity)."""
        u1 = 1.0 - self._r.random()  # (0, 1]
        u2 = self._r.random()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

    def exponential(self, mean: float) -> float:
        return -mean * math.log(1.0 - self._r.random())
