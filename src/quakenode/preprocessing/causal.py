"""Causal one-pole baseline removal with an explicit chunk-state API."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence


def one_pole_alpha(cutoff_hz: float, fs_hz: float) -> float:
    """Smoothing coefficient alpha = exp(-2*pi*fc/fs) for a one-pole baseline estimator."""
    if cutoff_hz <= 0.0 or fs_hz <= 0.0:
        raise ValueError("cutoff_hz and fs_hz must be positive")
    return math.exp(-2.0 * math.pi * cutoff_hz / fs_hz)


def causal_one_pole_highpass(
    samples: Iterable[float], alpha: float, state: float | None = None
) -> tuple[list[float], float | None]:
    """One-sided exponential baseline removal; initialize from the first observed sample.

    Returns (output, state). State is the final baseline estimate and must be
    carried across chunks; state=None means no sample has been seen yet.
    """
    if not 0.0 <= alpha < 1.0:
        raise ValueError(f"alpha must be in [0, 1), got {alpha!r}")
    baseline = state
    result = []
    for sample in samples:
        if baseline is None:
            baseline = sample
        else:
            baseline = alpha * baseline + (1.0 - alpha) * sample
        result.append(sample - baseline)
    return result, baseline


def chunked_one_pole_highpass(samples: Sequence[float], chunks: Sequence[int], alpha: float) -> list[float]:
    """Apply the filter chunk by chunk, carrying state; any remainder is one final chunk."""
    if sum(chunks) > len(samples):
        raise ValueError("chunk sizes exceed input length")
    output: list[float] = []
    state: float | None = None
    start = 0
    for size in chunks:
        part, state = causal_one_pole_highpass(samples[start : start + size], alpha, state)
        output.extend(part)
        start += size
    if start < len(samples):
        part, state = causal_one_pole_highpass(samples[start:], alpha, state)
        output.extend(part)
    return output
