"""The built-in faults. Every random choice comes from a per-fault Stream seeded by the caller.

Packets are visited in a canonical order (station, channel, sequence number), so a fault's pattern does not depend
on the order of the input list. Arrival times are only ever increased (never below ready time).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from quakenode.faults.base import FaultRecord, Selection, make_record
from quakenode.faults.rng import Stream
from quakenode.replay import Packet


def _canonical(packets: Sequence[Packet]) -> list[Packet]:
    return sorted(packets, key=lambda p: (p.station_id, p.channel_id, p.sequence_number))


def _restore_order(original: Sequence[Packet], changed: dict[tuple[str, str, int], Packet]) -> list[Packet]:
    return [changed.get(p.key, p) for p in original]


@dataclass(frozen=True)
class FixedDelay:
    """Add a constant delay_s to the arrival time of every selected packet."""

    delay_s: float
    selection: Selection = Selection()
    type: str = "fixed_delay"

    def apply(self, packets: Sequence[Packet], seed: int) -> tuple[list[Packet], FaultRecord]:
        changed, hit, n = {}, [], 0
        for p in packets:
            if self.selection.matches(p):
                n += 1
                changed[p.key] = replace(p, arrival_time_s=p.arrival_time_s + self.delay_s)
                hit.append(p.key)
        rec = make_record(self.type, {"delay_s": self.delay_s}, self.selection, seed, n, hit)
        return _restore_order(packets, changed), rec


@dataclass(frozen=True)
class Jitter:
    """Add a random nonnegative delay: uniform on [low_s, high_s] or exponential with mean_s."""

    distribution: str  # 'uniform' or 'exponential'
    low_s: float = 0.0
    high_s: float = 0.0
    mean_s: float = 0.0
    selection: Selection = Selection()
    type: str = "jitter"

    def apply(self, packets: Sequence[Packet], seed: int) -> tuple[list[Packet], FaultRecord]:
        rng, changed, hit, n = Stream(seed), {}, [], 0
        for p in _canonical(packets):
            if not self.selection.matches(p):
                continue
            n += 1
            if self.distribution == "uniform":
                extra = self.low_s + (self.high_s - self.low_s) * rng.uniform()
            else:
                extra = rng.exponential(self.mean_s)
            changed[p.key] = replace(p, arrival_time_s=p.arrival_time_s + extra)
            hit.append(p.key)
        params = {"distribution": self.distribution, "low_s": self.low_s, "high_s": self.high_s, "mean_s": self.mean_s}
        return _restore_order(packets, changed), make_record(self.type, params, self.selection, seed, n, hit)


@dataclass(frozen=True)
class PacketLoss:
    """Drop packets. model 'bernoulli': each selected packet is lost with probability p.

    model 'gilbert_elliott': a two-state Markov chain per station stream, advanced once per selected packet in
    sequence order, starting in the good state. In state good a packet is lost with probability loss_good and the
    chain moves to bad with probability p_gb; in state bad it is lost with probability loss_bad and returns to good
    with probability p_bg. Mean burst length (with loss_bad=1) is 1/p_bg packets.
    """

    model: str = "bernoulli"
    p: float = 0.0
    p_gb: float = 0.0
    p_bg: float = 0.0
    loss_good: float = 0.0
    loss_bad: float = 1.0
    selection: Selection = Selection()
    type: str = "packet_loss"

    def apply(self, packets: Sequence[Packet], seed: int) -> tuple[list[Packet], FaultRecord]:
        rng, lost, n = Stream(seed), set(), 0
        bad: dict[tuple[str, str], bool] = {}
        for p in _canonical(packets):
            if not self.selection.matches(p):
                continue
            n += 1
            if self.model == "bernoulli":
                if rng.bernoulli(self.p):
                    lost.add(p.key)
                continue
            stream_key = (p.station_id, p.channel_id)
            in_bad = bad.get(stream_key, False)
            if rng.bernoulli(self.loss_bad if in_bad else self.loss_good):
                lost.add(p.key)
            bad[stream_key] = (not rng.bernoulli(self.p_bg)) if in_bad else rng.bernoulli(self.p_gb)
        kept = [p for p in packets if p.key not in lost]
        params = {
            "model": self.model,
            "p": self.p,
            "p_gb": self.p_gb,
            "p_bg": self.p_bg,
            "loss_good": self.loss_good,
            "loss_bad": self.loss_bad,
        }
        return kept, make_record(self.type, params, self.selection, seed, n, sorted(lost))


@dataclass(frozen=True)
class Duplicate:
    """Deliver selected packets twice (probability p); the copy arrives extra_delay_s after the original."""

    p: float
    extra_delay_s: float = 0.0
    selection: Selection = Selection()
    type: str = "duplicate"

    def apply(self, packets: Sequence[Packet], seed: int) -> tuple[list[Packet], FaultRecord]:
        rng, copies, hit, n = Stream(seed), [], [], 0
        for p in _canonical(packets):
            if self.selection.matches(p):
                n += 1
                if rng.bernoulli(self.p):
                    copies.append(replace(p, arrival_time_s=p.arrival_time_s + self.extra_delay_s))
                    hit.append(p.key)
        params = {"p": self.p, "extra_delay_s": self.extra_delay_s}
        return [*packets, *copies], make_record(self.type, params, self.selection, seed, n, hit)


@dataclass(frozen=True)
class Reorder:
    """Reordering rule: each selected packet is, with probability p, held back by hold_s seconds on top of its
    arrival time, so it can arrive after later packets of the same stream (an overtaking). The record counts the
    packets held back and, in `note`, how many of them actually arrive after at least one later-sequence packet."""

    p: float
    hold_s: float
    selection: Selection = Selection()
    type: str = "reorder"

    def apply(self, packets: Sequence[Packet], seed: int) -> tuple[list[Packet], FaultRecord]:
        rng, changed, hit, n = Stream(seed), {}, [], 0
        for p in _canonical(packets):
            if self.selection.matches(p):
                n += 1
                if rng.bernoulli(self.p):
                    changed[p.key] = replace(p, arrival_time_s=p.arrival_time_s + self.hold_s)
                    hit.append(p.key)
        out = _restore_order(packets, changed)
        overtaken = 0
        by_stream: dict[tuple[str, str], list[Packet]] = {}
        for q in out:
            by_stream.setdefault((q.station_id, q.channel_id), []).append(q)
        held = set(hit)
        for stream in by_stream.values():
            for q in stream:
                if q.key in held and any(
                    o.sequence_number > q.sequence_number and o.arrival_time_s < q.arrival_time_s for o in stream
                ):
                    overtaken += 1
        note = f"{overtaken} of {len(hit)} held-back packets arrive after a later packet" if hit else ""
        return out, make_record(self.type, {"p": self.p, "hold_s": self.hold_s}, self.selection, seed, n, hit, note)


@dataclass(frozen=True)
class StationOutage:
    """Drop every packet of the target stations whose ready time lies in the logical interval (a dead link)."""

    selection: Selection
    type: str = "station_outage"

    def apply(self, packets: Sequence[Packet], seed: int) -> tuple[list[Packet], FaultRecord]:
        lost = [p.key for p in packets if self.selection.matches(p)]
        kept = [p for p in packets if p.key not in set(lost)]
        return kept, make_record(self.type, {}, self.selection, seed, len(lost), sorted(lost))


@dataclass(frozen=True)
class ClockOffset:
    """The sensor clock is wrong by offset_s: reported sample timestamps are shifted. The TRUE sample time
    (first_sample_time_s) is untouched; the shifted one goes in reported_first_sample_time_s."""

    offset_s: float
    selection: Selection = Selection()
    type: str = "clock_offset"

    def apply(self, packets: Sequence[Packet], seed: int) -> tuple[list[Packet], FaultRecord]:
        changed, hit, n = {}, [], 0
        for p in packets:
            if self.selection.matches(p):
                n += 1
                base = (
                    p.reported_first_sample_time_s
                    if p.reported_first_sample_time_s is not None
                    else p.first_sample_time_s
                )
                changed[p.key] = replace(p, reported_first_sample_time_s=base + self.offset_s)
                hit.append(p.key)
        rec = make_record(self.type, {"offset_s": self.offset_s}, self.selection, seed, n, hit)
        return _restore_order(packets, changed), rec


@dataclass(frozen=True)
class MissingSamples:
    """Digitizer dropout: with probability p a selected packet loses its last n_samples samples (the packet is
    shortened; the pipeline then sees a gap before the next packet). Packets with <= n_samples samples are skipped."""

    p: float
    n_samples: int
    selection: Selection = Selection()
    type: str = "missing_samples"

    def apply(self, packets: Sequence[Packet], seed: int) -> tuple[list[Packet], FaultRecord]:
        rng, changed, hit, n = Stream(seed), {}, [], 0
        for p in _canonical(packets):
            if not self.selection.matches(p):
                continue
            n += 1
            if rng.bernoulli(self.p) and len(p.samples) > self.n_samples:
                changed[p.key] = replace(p, samples=p.samples[: len(p.samples) - self.n_samples])
                hit.append(p.key)
        return _restore_order(packets, changed), make_record(
            self.type, {"p": self.p, "n_samples": self.n_samples}, self.selection, seed, n, hit
        )


def apply_faults(
    packets: Sequence[Packet], faults: Sequence[object], base_seed: int
) -> tuple[list[Packet], list[FaultRecord]]:
    """Apply faults in the declared order. Fault i uses seed derive_seed(base_seed, 'fault', i, type)."""
    from quakenode.faults.rng import derive_seed

    current, records = list(packets), []
    for i, fault in enumerate(faults):
        seed = derive_seed(base_seed, "fault", i, fault.type)  # type: ignore[attr-defined]
        current, rec = fault.apply(current, seed)  # type: ignore[attr-defined]
        records.append(rec)
    return current, records
