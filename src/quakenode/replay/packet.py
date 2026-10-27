"""Packet record. Sample, ready and arrival times are separate fields on purpose."""

from __future__ import annotations

import math
from dataclasses import dataclass

_TIME_TOL_S = 1e-9


@dataclass(frozen=True)
class Packet:
    """A contiguous run of samples from one station/channel.

    Clocks (all seconds, trace start = 0):
      first_sample_time_s  sample clock: time of samples[0] = first_sample_index / sample_rate_hz
      ready_time_s         when the LAST sample exists at the sensor (>= time of the last sample)
      arrival_time_s       simulated arrival at the receiver (>= ready_time_s)
    """

    station_id: str
    channel_id: str
    sequence_number: int
    sample_rate_hz: float
    first_sample_index: int
    first_sample_time_s: float
    samples: tuple[float, ...]
    ready_time_s: float
    arrival_time_s: float
    # Sample timestamp as REPORTED by a (possibly mis-set) sensor clock. None means "equals the true sample time".
    # first_sample_time_s always stays the true sample clock; the clock_offset fault only sets this field.
    reported_first_sample_time_s: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "samples", tuple(float(x) for x in self.samples))
        if not self.samples:
            raise ValueError("packet must contain at least one sample")
        if not all(math.isfinite(x) for x in self.samples):
            raise ValueError("packet samples must be finite")
        if not self.sample_rate_hz > 0.0:
            raise ValueError("sample_rate_hz must be positive")
        if self.sequence_number < 0 or self.first_sample_index < 0:
            raise ValueError("sequence_number and first_sample_index must be >= 0")
        if abs(self.first_sample_time_s - self.first_sample_index / self.sample_rate_hz) > _TIME_TOL_S:
            raise ValueError("first_sample_time_s inconsistent with first_sample_index and sample_rate_hz")
        if self.ready_time_s < self.sample_time_s(len(self.samples) - 1) - _TIME_TOL_S:
            raise ValueError("ready_time_s precedes the time of the packet's last sample")
        if self.arrival_time_s < self.ready_time_s:
            raise ValueError("arrival_time_s must be >= ready_time_s")

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.station_id, self.channel_id, self.sequence_number)

    def sample_time_s(self, k: int) -> float:
        """Sample-clock time of samples[k], computed from the global index so packet size cannot change it."""
        return (self.first_sample_index + k) / self.sample_rate_hz

    def reported_sample_time_s(self, k: int) -> float | None:
        """Reported (sensor-clock) timestamp of samples[k], or None if no clock error was applied."""
        if self.reported_first_sample_time_s is None:
            return None
        return self.reported_first_sample_time_s + k / self.sample_rate_hz
