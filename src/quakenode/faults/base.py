"""Fault records and the fault interface.

A fault is a deterministic, seeded transformation of a list of Packets, applied BEFORE delivery to the replay
engine. It never changes sample values (only metadata, arrival times, presence, or truncation) and always returns a
FaultRecord saying what it did.

Selection: a fault applies to packets whose station is in `targets` ("all" or a list of station ids) and whose
ready_time_s lies in [start_s, end_s) (end_s None = no end). The interval is on the ready clock because that is when
a packet exists at the sensor.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from quakenode.replay import Packet


@dataclass(frozen=True)
class FaultRecord:
    type: str
    parameters: dict[str, Any]
    targets: str | tuple[str, ...]
    start_s: float
    end_s: float | None
    seed: int
    packets_considered: int  # packets in the target/interval selection
    packets_affected: int
    affected: tuple[tuple[str, str, int], ...] = field(default=(), repr=False)  # packet keys
    status: str = "applied"  # 'applied' or 'skipped'
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "parameters": self.parameters,
            "targets": list(self.targets) if isinstance(self.targets, tuple) else self.targets,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "seed": self.seed,
            "packets_considered": self.packets_considered,
            "packets_affected": self.packets_affected,
            "affected": [list(k) for k in self.affected],
            "status": self.status,
            "note": self.note,
        }


class Fault(Protocol):
    type: str

    def apply(self, packets: Sequence[Packet], seed: int) -> tuple[list[Packet], FaultRecord]: ...


@dataclass(frozen=True)
class Selection:
    targets: str | tuple[str, ...] = "all"
    start_s: float = 0.0
    end_s: float | None = None

    def matches(self, p: Packet) -> bool:
        if self.targets != "all" and p.station_id not in self.targets:
            return False
        return p.ready_time_s >= self.start_s and (self.end_s is None or p.ready_time_s < self.end_s)


def make_record(
    type_: str,
    parameters: dict[str, Any],
    sel: Selection,
    seed: int,
    considered: int,
    affected: Sequence[tuple[str, str, int]],
    note: str = "",
) -> FaultRecord:
    status = "applied" if affected else "skipped"
    if not affected and not note:
        note = "no packet was affected" if considered else "no packet matched the target/interval"
    return FaultRecord(
        type_,
        dict(parameters),
        sel.targets,
        sel.start_s,
        sel.end_s,
        seed,
        considered,
        len(affected),
        tuple(affected),
        status,
        note,
    )
