"""Offline preprocessing. These use the whole finite window, so they are NOT causal."""

from __future__ import annotations

from collections.abc import Sequence


def mean_remove(samples: Sequence[float]) -> list[float]:
    """Subtract the mean of the complete input window."""
    mean = sum(samples) / len(samples)
    return [x - mean for x in samples]


def linear_detrend(samples: Sequence[float]) -> list[float]:
    """Subtract a least-squares line fit over the complete finite input window."""
    n = len(samples)
    xbar = (n - 1) / 2.0
    ybar = sum(samples) / n
    denom = sum((i - xbar) ** 2 for i in range(n))
    slope = sum((i - xbar) * (y - ybar) for i, y in enumerate(samples)) / denom
    intercept = ybar - slope * xbar
    return [y - (intercept + slope * i) for i, y in enumerate(samples)]
