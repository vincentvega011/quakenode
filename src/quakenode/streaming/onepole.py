"""Streaming causal one-pole baseline removal with an explicit warm-up."""

from __future__ import annotations

from collections.abc import Sequence


class StreamingOnePoleHighpass:
    """State-carrying version of quakenode.preprocessing.causal_one_pole_highpass.

    Initializes the baseline from the first observed sample (output 0.0) and then applies
    baseline = alpha*baseline + (1-alpha)*x, same arithmetic as the batch function. The
    first `warmup_samples` outputs after construction or reset() are marked not scorable.
    """

    def __init__(self, alpha: float, warmup_samples: int) -> None:
        if not 0.0 <= alpha < 1.0:
            raise ValueError(f"alpha must be in [0, 1), got {alpha!r}")
        if warmup_samples < 0:
            raise ValueError("warmup_samples must be >= 0")
        self.alpha = alpha
        self.warmup_samples = warmup_samples
        self.reset()

    def reset(self) -> None:
        self._baseline: float | None = None
        self.n_processed = 0

    @property
    def warming_up(self) -> bool:
        return self.n_processed < self.warmup_samples

    def process(self, samples: Sequence[float]) -> tuple[list[float], list[bool]]:
        """Return (filtered outputs, scorable flags) for the new samples."""
        out: list[float] = []
        scorable: list[bool] = []
        for x in samples:
            if self._baseline is None:
                self._baseline = x
            else:
                self._baseline = self.alpha * self._baseline + (1.0 - self.alpha) * x
            out.append(x - self._baseline)
            scorable.append(self.n_processed >= self.warmup_samples)
            self.n_processed += 1
        return out, scorable
