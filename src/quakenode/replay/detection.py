"""Detection record that keeps the clocks apart."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    """One emitted trigger.

    Clocks (seconds, trace start = 0):
      trigger_sample_time_s  sample clock: time of the triggering sample (index / sample_rate_hz)
      trigger_ready_time_s   when that sample existed at the sensor: its sample time plus the
                             packet's (ready_time_s - last sample time), i.e. sensor latency is
                             assumed constant within a packet
      arrival_time_s         arrival of the packet that contained the triggering sample
      emission_time_s        arrival_time_s + processing_delay_s (simulated time the detector emitted)
    """

    station_id: str
    channel_id: str
    trigger_sample_index: int
    trigger_sample_time_s: float
    trigger_ready_time_s: float
    arrival_time_s: float
    emission_time_s: float
    processing_delay_s: float
    detector_name: str
    detector_version: str
    ratio: float
    threshold: float
    parameters: tuple[tuple[str, float | int], ...]
    # Trigger sample timestamp as reported by the sensor clock (None if no clock error). The true sample clock
    # is trigger_sample_time_s; this field exists so clock errors can be measured, never used to merge clocks.
    reported_trigger_sample_time_s: float | None = None
    # True if the triggering sample was INSERTED by the zero_fill gap policy (not recorded data).
    on_filled_samples: bool = False
