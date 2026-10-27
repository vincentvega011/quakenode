"""Deterministic logical clock. Never reads or waits on wall-clock time."""

from __future__ import annotations


class VirtualClock:
    """Monotonic logical time in seconds on the receiver's (arrival) timeline."""

    def __init__(self, start_s: float = 0.0) -> None:
        self._now_s = float(start_s)

    @property
    def now_s(self) -> float:
        return self._now_s

    def advance_to(self, t_s: float) -> float:
        if t_s < self._now_s:
            raise ValueError(f"clock cannot move backwards: now={self._now_s!r}, requested={t_s!r}")
        self._now_s = float(t_s)
        return self._now_s
