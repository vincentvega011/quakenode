"""Deterministic, seeded fault injection on packet lists (applied before delivery)."""

from quakenode.faults.base import Fault, FaultRecord, Selection
from quakenode.faults.library import (
    ClockOffset,
    Duplicate,
    FixedDelay,
    Jitter,
    MissingSamples,
    PacketLoss,
    Reorder,
    StationOutage,
    apply_faults,
)
from quakenode.faults.rng import Stream, derive_seed

FAULT_TYPES = (
    "fixed_delay",
    "jitter",
    "packet_loss",
    "duplicate",
    "reorder",
    "station_outage",
    "clock_offset",
    "missing_samples",
)

__all__ = [
    "FAULT_TYPES",
    "ClockOffset",
    "Duplicate",
    "Fault",
    "FaultRecord",
    "FixedDelay",
    "Jitter",
    "MissingSamples",
    "PacketLoss",
    "Reorder",
    "Selection",
    "StationOutage",
    "Stream",
    "apply_faults",
    "derive_seed",
]
