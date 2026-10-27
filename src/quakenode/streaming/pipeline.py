"""Streaming pipeline: Receiver packets -> per-stream detectors -> Detection records.

The pipeline owns ordering, gaps and the out-of-order policy; detectors (see protocol.StreamDetector) only ever see
in-order packets.

Gap rule (per station/channel stream): a packet that starts after the next expected sample index leaves a gap. A
GapEvent is ALWAYS recorded (policy, missing sample count, filled sample count). What else happens depends on
`gap_policy` (see docs/gap_policies.md); nothing is ever interpolated:
  reset      (default) the detector is reset and re-warms from the new packet.
  hold       filter and detector state are kept; no samples are inserted; the next packet continues the stream.
             Windowed statistics then span the discontinuity. A fault-tolerance policy, not a repair.
  zero_fill  zeros are inserted for the missing indices and fed through the detector; these samples are labeled
             (GapEvent.filled_samples, detections triggered on them have on_filled_samples=True). Zeros are
             arbitrary: on data with a baseline offset they create a step.

Out-of-order policy (`order_policy`), applied to packets that arrive out of order:
  reject     a packet that starts before the expected index (duplicate, overlapping or late) raises
             StreamOrderError. A packet that starts after it is a gap, declared immediately.
  drop_late  such late/duplicate packets are dropped and recorded in `dropped`; gaps are declared immediately.
  buffer     a packet that starts after the expected index is HELD (reordering buffer) for up to `max_wait_s` of
             simulated time, measured from the arrival of the first held packet. If the missing data arrive in
             time, the held packets are released in order, with no gap; each released packet is processed at the
             time the missing packet arrived, so its detections are emitted LATER than its own arrival (emission
             time = processing time + processing delay). If the wait expires, a gap is declared at the deadline
             (GapEvent.declared_time_s) and the held packets are processed at the deadline. A packet that arrives
             after its gap was declared is late and is dropped (as in drop_late).
In every policy a sample-rate change within a stream raises StreamOrderError.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace

from quakenode.replay import Detection, Packet, ReplayEngine
from quakenode.streaming.protocol import DetectorFactory, StreamDetector

ORDER_POLICIES = ("reject", "drop_late", "buffer")
GAP_POLICIES = ("reset", "hold", "zero_fill")


class StreamOrderError(ValueError):
    """Raised for duplicate, overlapping, out-of-order or rate-inconsistent packets (policy 'reject')."""


@dataclass(frozen=True)
class GapEvent:
    station_id: str
    channel_id: str
    expected_index: int
    received_index: int
    arrival_time_s: float  # arrival of the packet that revealed the gap
    declared_time_s: float | None = None  # when the gap was declared (later than arrival under 'buffer')
    policy: str = "reset"
    missing_samples: int | None = None  # indices skipped: received_index - expected_index
    filled_samples: int = 0  # zeros inserted (zero_fill only)
    state_kept: bool = False  # True when detector state was carried across the gap (hold, zero_fill)


@dataclass(frozen=True)
class DroppedPacket:
    station_id: str
    channel_id: str
    sequence_number: int
    first_sample_index: int
    expected_index: int
    arrival_time_s: float
    reason: str  # 'late_or_duplicate'


@dataclass(frozen=True)
class ProcessedPacket:
    station_id: str
    channel_id: str
    sequence_number: int
    arrival_time_s: float
    filtered: tuple[float, ...]
    scorable: tuple[bool, ...]


@dataclass
class _Stream:
    detector: StreamDetector
    sample_rate_hz: float
    next_index: int = 0
    hold: dict[int, Packet] = field(default_factory=dict)
    deadline_s: float | None = None
    samples_processed: int = 0  # recorded samples handed to the detector (inserted zeros are not counted)
    samples_filled: int = 0


def _legacy_factory(
    alpha: float, warmup_samples: int, sta_samples: int, lta_samples: int, threshold: float, delay: float
) -> DetectorFactory:
    from quakenode.streaming.detectors import StaLtaRmsDetector

    def factory(station_id: str, channel_id: str, rate_hz: float) -> StreamDetector:
        return StaLtaRmsDetector(
            alpha=alpha,
            warmup_samples=warmup_samples,
            sta_samples=sta_samples,
            lta_samples=lta_samples,
            threshold=threshold,
            processing_delay_s=delay,
            sample_rate_hz=rate_hz,
        )

    return factory


@dataclass
class StreamingPipeline:
    """Either pass `detector_factory`, or the legacy arguments of the Phase 1 RMS STA/LTA detector."""

    alpha: float | None = None
    warmup_samples: int | None = None
    sta_samples: int | None = None
    lta_samples: int | None = None
    threshold: float | None = None
    processing_delay_s: float = 0.0
    detector_factory: DetectorFactory | None = None
    order_policy: str = "reject"
    max_wait_s: float = 0.0
    gap_policy: str = "reset"
    detections: list[Detection] = field(default_factory=list)
    gap_events: list[GapEvent] = field(default_factory=list)
    processed: list[ProcessedPacket] = field(default_factory=list)
    dropped: list[DroppedPacket] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.processing_delay_s < 0.0:
            raise ValueError("processing_delay_s must be >= 0")
        if self.order_policy not in ORDER_POLICIES:
            raise ValueError(f"order_policy must be one of {ORDER_POLICIES}, got {self.order_policy!r}")
        if self.gap_policy not in GAP_POLICIES:
            raise ValueError(f"gap_policy must be one of {GAP_POLICIES}, got {self.gap_policy!r}")
        if self.max_wait_s < 0.0:
            raise ValueError("max_wait_s must be >= 0")
        if self.order_policy == "buffer" and self.max_wait_s <= 0.0:
            raise ValueError("order_policy 'buffer' requires max_wait_s > 0")
        if self.detector_factory is None:
            legacy = (self.alpha, self.warmup_samples, self.sta_samples, self.lta_samples, self.threshold)
            if any(v is None for v in legacy):
                raise ValueError("give a detector_factory or all of alpha, warmup_samples, sta/lta samples, threshold")
            self.detector_factory = _legacy_factory(*legacy, self.processing_delay_s)  # type: ignore[arg-type]
        self._streams: dict[tuple[str, str], _Stream] = {}

    # ---- status -------------------------------------------------------------------------------------------

    def warming_up(self, station_id: str, channel_id: str) -> bool:
        """True while the stream's detector is still warming up."""
        return self._streams[(station_id, channel_id)].detector.warming_up

    def samples_processed(self, station_id: str, channel_id: str) -> int:
        return self._streams[(station_id, channel_id)].samples_processed

    def samples_filled(self, station_id: str, channel_id: str) -> int:
        return self._streams[(station_id, channel_id)].samples_filled

    @property
    def next_deadline_s(self) -> float | None:
        deadlines = [s.deadline_s for s in self._streams.values() if s.deadline_s is not None]
        return min(deadlines) if deadlines else None

    # ---- feeding ------------------------------------------------------------------------------------------

    def feed(self, packet: Packet, now_s: float | None = None) -> None:
        """Process one delivered packet. Packets must be fed in delivery order; now_s defaults to its arrival."""
        now = packet.arrival_time_s if now_s is None else now_s
        self.flush_until(now, inclusive=False)
        key = (packet.station_id, packet.channel_id)
        stream = self._streams.get(key)
        if stream is None:
            stream = _Stream(self.detector_factory(key[0], key[1], packet.sample_rate_hz), packet.sample_rate_hz)  # type: ignore[misc]
            stream.next_index = packet.first_sample_index  # a stream may begin at a nonzero index; not a gap
            self._streams[key] = stream
        if packet.sample_rate_hz != stream.sample_rate_hz:
            raise StreamOrderError(f"sample rate changed within stream {key}")
        first = packet.first_sample_index
        if first < stream.next_index or first in stream.hold:
            if self.order_policy == "reject":
                raise StreamOrderError(
                    f"stream {key}: packet {packet.sequence_number} starts at {first}, "
                    f"before expected {stream.next_index} (duplicate or out of order)"
                )
            self.dropped.append(
                DroppedPacket(
                    key[0],
                    key[1],
                    packet.sequence_number,
                    first,
                    stream.next_index,
                    packet.arrival_time_s,
                    "late_or_duplicate",
                )
            )
            return
        if first == stream.next_index:
            self._process(stream, packet, now)
            self._drain(stream, now)
            return
        if self.order_policy == "buffer":
            stream.hold[first] = packet
            if stream.deadline_s is None:
                stream.deadline_s = packet.arrival_time_s + self.max_wait_s
            return
        self._declare_gap(stream, packet, declared_s=packet.arrival_time_s, at_s=now)
        self._process(stream, packet, now)

    def flush_until(self, now_s: float, inclusive: bool = True) -> None:
        """Expire reordering-buffer waits whose deadline has passed (declare gaps, process the held packets)."""
        for stream in self._streams.values():
            d = stream.deadline_s
            if d is not None and (d <= now_s if inclusive else d < now_s):
                self._expire(stream, d)

    def _expire(self, stream: _Stream, deadline_s: float) -> None:
        held = [stream.hold[i] for i in sorted(stream.hold)]
        stream.hold.clear()
        stream.deadline_s = None
        for packet in held:
            if packet.first_sample_index != stream.next_index:
                self._declare_gap(stream, packet, declared_s=deadline_s, at_s=deadline_s)
            self._process(stream, packet, deadline_s)

    def _drain(self, stream: _Stream, now_s: float) -> None:
        while stream.next_index in stream.hold:
            self._process(stream, stream.hold.pop(stream.next_index), now_s)
        stream.deadline_s = (now_s + self.max_wait_s) if stream.hold else None

    def _declare_gap(self, stream: _Stream, packet: Packet, declared_s: float, at_s: float) -> None:
        missing = packet.first_sample_index - stream.next_index
        filled = 0
        if self.gap_policy == "reset":
            stream.detector.reset()
        elif self.gap_policy == "zero_fill":
            filled = missing
        self.gap_events.append(
            GapEvent(
                packet.station_id, packet.channel_id, stream.next_index, packet.first_sample_index,
                packet.arrival_time_s, declared_s, self.gap_policy, missing, filled, self.gap_policy != "reset",
            )
        )  # fmt: skip
        if filled:
            self._fill_with_zeros(stream, packet, filled, at_s)

    def _fill_with_zeros(self, stream: _Stream, packet: Packet, n: int, at_s: float) -> None:
        """Feed n zeros for the missing indices through the detector, labeled as filled samples."""
        first, rate = stream.next_index, stream.sample_rate_hz
        ready = (first + n - 1) / rate
        filler = Packet(
            packet.station_id, packet.channel_id, packet.sequence_number, rate, first, first / rate,
            (0.0,) * n, ready, max(at_s, ready),
        )  # fmt: skip
        self._process(stream, filler, filler.arrival_time_s, filled=True)

    def _process(self, stream: _Stream, packet: Packet, at_s: float, filled: bool = False) -> None:
        found = stream.detector.process(packet, max(at_s, packet.arrival_time_s))
        if filled:
            found = [replace(d, on_filled_samples=True) for d in found]
        self.detections.extend(found)
        filtered = getattr(stream.detector, "last_filtered", None)
        scorable = getattr(stream.detector, "last_scorable", None)
        if filtered is not None and scorable is not None and not filled:
            self.processed.append(
                ProcessedPacket(
                    packet.station_id,
                    packet.channel_id,
                    packet.sequence_number,
                    packet.arrival_time_s,
                    tuple(filtered),
                    tuple(scorable),
                )
            )
        stream.next_index = packet.first_sample_index + len(packet.samples)
        if filled:
            stream.samples_filled += len(packet.samples)
        else:
            stream.samples_processed += len(packet.samples)

    # ---- driving ------------------------------------------------------------------------------------------

    def run(self, engine: ReplayEngine, times_s: list[float] | None = None) -> StreamingPipeline:
        """Advance the engine and feed newly delivered packets in order; returns self.

        With times_s, advances to each time in turn (non-decreasing). Without, advances to each pending arrival
        time (and reordering-buffer deadline) until nothing is pending.
        """
        if times_s is not None:
            for t in times_s:
                self._feed_all(engine.advance_to(t))
                self.flush_until(t, inclusive=True)
            return self
        while True:
            candidates = [t for t in (engine.next_arrival_time_s, self.next_deadline_s) if t is not None]
            if not candidates:
                return self
            t = max(min(candidates), engine.clock.now_s)
            self._feed_all(engine.advance_to(t))
            self.flush_until(t, inclusive=True)

    def _feed_all(self, packets: list[Packet]) -> None:
        for p in packets:
            self.feed(p)


# type alias kept for callers that want to annotate a delivery callback
DeliveryCallback = Callable[[Packet], None]
