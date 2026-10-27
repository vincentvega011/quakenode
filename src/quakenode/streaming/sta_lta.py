"""Incremental RMS STA/LTA first-trigger detector with bounded buffers."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

DETECTOR_NAME = "rms_sta_lta_first_trigger"
DETECTOR_VERSION = "streaming-1"


@dataclass(frozen=True)
class StaLtaOutput:
    ratio: float | None  # None until the buffer is full, or when LTA RMS is zero
    triggered: bool


class StreamingStaLta:
    """Streaming equivalent of quakenode.detectors.rms_sta_lta_first_trigger.

    Keeps a ring buffer of the last sta_samples + lta_samples inputs (STA = newest
    sta_samples, LTA = the preceding lta_samples, non-overlapping). To be bit-identical
    with the batch function, the window sums are recomputed from the buffer in the same
    order at every sample (O(sta + lta) per sample) instead of using running sums.

    First-trigger semantics are unchanged from the batch detector: it emits ONCE, at the
    first scorable sample with ratio >= threshold and LTA RMS > 0, and never re-arms, not
    even after reset(). reset() clears only the buffer. Samples passed with scorable=False
    fill the buffer but cannot trigger and do not consume the one trigger.
    """

    def __init__(self, sta_samples: int, lta_samples: int, threshold: float) -> None:
        if sta_samples < 1 or lta_samples < 1:
            raise ValueError("sta_samples and lta_samples must be >= 1")
        if threshold <= 0.0:
            raise ValueError("threshold must be positive")
        self.sta_samples = sta_samples
        self.lta_samples = lta_samples
        self.threshold = threshold
        self.fired = False
        self._buffer: deque[float] = deque(maxlen=sta_samples + lta_samples)

    def reset(self) -> None:
        """Drop buffered samples (used after a gap). Does not re-arm a detector that already fired."""
        self._buffer.clear()

    @property
    def buffer_full(self) -> bool:
        return len(self._buffer) == self._buffer.maxlen

    def update(self, x: float, scorable: bool = True) -> StaLtaOutput:
        if self.fired:
            return StaLtaOutput(None, False)
        self._buffer.append(x)
        if not self.buffer_full:
            return StaLtaOutput(None, False)
        window = list(self._buffer)
        lta = window[: self.lta_samples]
        sta = window[self.lta_samples :]
        sta_rms = math.sqrt(sum(v * v for v in sta) / self.sta_samples)
        lta_rms = math.sqrt(sum(v * v for v in lta) / self.lta_samples)
        if not lta_rms > 0.0:
            return StaLtaOutput(None, False)
        ratio = sta_rms / lta_rms
        triggered = scorable and ratio >= self.threshold
        if triggered:
            self.fired = True
        return StaLtaOutput(ratio, triggered)
