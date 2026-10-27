"""The streaming detector interface.

A detector is a per-stream (one station/channel) stateful object. The pipeline owns ordering, gaps and policies and
calls the detector only with in-order packets, so a detector never sees undelivered or reordered data.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from quakenode.replay import Detection, Packet


@runtime_checkable
class StreamDetector(Protocol):
    """Minimal streaming detector protocol.

    name, version     identify the detector in every Detection record
    warmup_s          seconds of data after (re)start during which no detection can be emitted
    warming_up        True until the warm-up is complete
    reset()           drop all state (called by the pipeline after a gap)
    process(packet, processed_at_s)
                      consume ONE in-order packet and return the detections it triggered. `processed_at_s` is the
                      simulated time at which the pipeline processes the packet (>= packet.arrival_time_s; later
                      than the arrival only when a reordering buffer held the packet). Emission time of a
                      detection is processed_at_s + processing delay.
    Optional attributes `last_filtered` / `last_scorable` (tuples) expose the preprocessed samples of the last
    packet for logging; the pipeline records them when present.
    """

    name: str
    version: str
    warmup_s: float

    @property
    def warming_up(self) -> bool: ...

    def reset(self) -> None: ...

    def process(self, packet: Packet, processed_at_s: float | None = None) -> list[Detection]: ...


# station_id, channel_id, sample_rate_hz -> a fresh detector for that stream
DetectorFactory = Callable[[str, str, float], StreamDetector]
