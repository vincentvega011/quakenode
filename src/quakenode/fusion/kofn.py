"""k-of-n fusion: an event candidate needs detections from at least k DISTINCT stations within a time window.

Clock choice (explicit): the window is measured on the **emission clock** (`window_clock="emission"`, default) or
the **arrival clock** (`"arrival"`), never on the sample clock. A fusion centre only knows when detections reach it,
not when the sample was recorded, so a late (delayed, buffered) detection counts late. Candidate creation time is
always on the emission clock: the emission time of the detection that completes the k-th station (max emission
time over the contributors when the arrival clock is used for the window).

Rules, applied to detections sorted by (clock time, station id, trigger index):
  1. Candidates older than update_window_s (since creation) are closed.
  2. A detection from a station that already contributes to an open candidate is ignored (duplicate).
  3. Otherwise, if a candidate is open, the detection joins it ("updated"; at most one station per candidate).
  4. Otherwise it goes to the pending pool (entries older than window_s are expired; one entry per station, a repeat
     from the same station is ignored). When the pool has >= k distinct stations, a candidate is created from it.
Every step is recorded as a FusionDecision.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from quakenode.replay import Detection

WINDOW_CLOCKS = ("emission", "arrival")


@dataclass(frozen=True)
class FusionConfig:
    k: int
    window_s: float
    update_window_s: float
    window_clock: str = "emission"

    def __post_init__(self) -> None:
        if self.k < 1:
            raise ValueError("k must be >= 1")
        if self.window_s <= 0 or self.update_window_s < 0:
            raise ValueError("window_s must be > 0 and update_window_s >= 0")
        if self.window_clock not in WINDOW_CLOCKS:
            raise ValueError(f"window_clock must be one of {WINDOW_CLOCKS}")


@dataclass
class Candidate:
    id: int
    created_time_s: float  # emission clock
    detections: list[Detection]
    status: str = "created"  # created -> updated (a station joined) -> closed
    update_times_s: list[float] = field(default_factory=list)
    closed_time_s: float | None = None

    @property
    def station_ids(self) -> tuple[str, ...]:
        return tuple(d.station_id for d in self.detections)


@dataclass(frozen=True)
class FusionDecision:
    # detection_pending | duplicate_ignored | pending_expired | candidate_created | candidate_updated | candidate_closed
    kind: str
    time_s: float
    station_id: str | None = None
    candidate_id: int | None = None
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "decision": self.kind,
            "time_s": self.time_s,
            "station_id": self.station_id,
            "candidate_id": self.candidate_id,
            "detail": self.detail,
        }


@dataclass
class FusionResult:
    candidates: list[Candidate]
    decisions: list[FusionDecision]


def fuse(detections: Sequence[Detection], cfg: FusionConfig) -> FusionResult:
    def clock(d: Detection) -> float:
        return d.emission_time_s if cfg.window_clock == "emission" else d.arrival_time_s

    ordered = sorted(detections, key=lambda d: (clock(d), d.station_id, d.trigger_sample_index))
    candidates: list[Candidate] = []
    decisions: list[FusionDecision] = []
    pending: list[Detection] = []

    for d in ordered:
        t = clock(d)
        for c in candidates:
            if c.status != "closed" and t > c.created_time_s + cfg.update_window_s:
                c.status, c.closed_time_s = "closed", c.created_time_s + cfg.update_window_s
                decisions.append(FusionDecision("candidate_closed", c.closed_time_s, None, c.id))
        open_c = [c for c in candidates if c.status != "closed"]
        if any(d.station_id in c.station_ids for c in open_c):
            decisions.append(
                FusionDecision("duplicate_ignored", t, d.station_id, None, "station already in an open candidate")
            )
            continue
        if open_c:
            c = open_c[0]
            c.detections.append(d)
            c.status = "updated"
            c.update_times_s.append(d.emission_time_s)
            decisions.append(FusionDecision("candidate_updated", d.emission_time_s, d.station_id, c.id))
            continue
        expired = [p for p in pending if clock(p) < t - cfg.window_s]
        for p in expired:
            decisions.append(FusionDecision("pending_expired", t, p.station_id, None, "older than window_s"))
        pending = [p for p in pending if clock(p) >= t - cfg.window_s]
        if any(p.station_id == d.station_id for p in pending):
            decisions.append(FusionDecision("duplicate_ignored", t, d.station_id, None, "station already pending"))
            continue
        pending.append(d)
        decisions.append(FusionDecision("detection_pending", t, d.station_id))
        if len({p.station_id for p in pending}) >= cfg.k:
            created = max(p.emission_time_s for p in pending)
            c = Candidate(len(candidates) + 1, created, list(pending))
            candidates.append(c)
            pending = []
            decisions.append(FusionDecision("candidate_created", created, d.station_id, c.id, ",".join(c.station_ids)))
    return FusionResult(candidates, decisions)
