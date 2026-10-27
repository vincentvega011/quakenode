"""RMS-ratio STA/LTA first-trigger detector."""

from __future__ import annotations

import math
from collections.abc import Sequence


def rms_sta_lta_first_trigger(
    samples: Sequence[float], sta_samples: int, lta_samples: int, threshold: float, stop_index: int | None = None
) -> int | None:
    """First index where causal RMS STA / preceding, non-overlapping RMS LTA >= threshold.

    The decision at index i uses samples[:i + 1] only. stop_index (inclusive) limits
    the scan, which lets callers emulate a data prefix. Returns None if no trigger.
    """
    if sta_samples < 1 or lta_samples < 1:
        raise ValueError("sta_samples and lta_samples must be >= 1")
    if threshold <= 0.0:
        raise ValueError("threshold must be positive")
    last = len(samples) - 1 if stop_index is None else min(stop_index, len(samples) - 1)
    for i in range(lta_samples + sta_samples - 1, last + 1):
        sta = samples[i - sta_samples + 1 : i + 1]
        lta = samples[i - sta_samples - lta_samples + 1 : i - sta_samples + 1]
        sta_rms = math.sqrt(sum(x * x for x in sta) / sta_samples)
        lta_rms = math.sqrt(sum(x * x for x in lta) / lta_samples)
        if lta_rms > 0.0 and sta_rms / lta_rms >= threshold:
            return i
    return None
