"""Event-queue replay engine and the receiver view of delivered data."""

from __future__ import annotations

import heapq
from collections.abc import Sequence
from dataclasses import dataclass, replace

from quakenode.replay.clock import VirtualClock
from quakenode.replay.packet import Packet


class UndeliveredPacketError(LookupError):
    """Raised when a consumer asks for a packet that has not arrived by the logical clock."""


@dataclass(frozen=True)
class Trace:
    """A full waveform for one station/channel; sample i is at time i / sample_rate_hz. Producer side only."""

    station_id: str
    channel_id: str
    sample_rate_hz: float
    samples: tuple[float, ...]
    # Index of samples[0] on a shared timeline (sample time = index / rate). Lets several stations whose records
    # start at different times be replayed on one clock. Default 0.
    first_sample_index: int = 0


def with_fixed_delay(packets: Sequence[Packet], delay_s: float) -> list[Packet]:
    """Copy packets with arrival_time_s shifted by delay_s; sample and ready times are untouched."""
    return [replace(p, arrival_time_s=p.arrival_time_s + delay_s) for p in packets]


class Receiver:
    """Consumer view: holds only delivered packets, no reference to the engine's pending queue."""

    def __init__(self, delivered: dict[tuple[str, str, int], Packet]) -> None:
        self._delivered = delivered

    def delivered_packets(self) -> tuple[Packet, ...]:
        """Delivered packets in delivery order."""
        return tuple(self._delivered.values())

    def get_packet(self, station_id: str, channel_id: str, sequence_number: int) -> Packet:
        try:
            return self._delivered[(station_id, channel_id, sequence_number)]
        except KeyError:
            raise UndeliveredPacketError(
                f"packet {(station_id, channel_id, sequence_number)} has not been delivered"
            ) from None

    def contiguous_samples(self, station_id: str, channel_id: str) -> tuple[float, ...]:
        """Delivered samples from index 0 up to the first gap (what a causal consumer may use)."""
        packets = sorted(
            (p for p in self._delivered.values() if p.station_id == station_id and p.channel_id == channel_id),
            key=lambda p: p.first_sample_index,
        )
        out: list[float] = []
        for p in packets:
            if p.first_sample_index != len(out):
                break
            out.extend(p.samples)
        return tuple(out)


class ReplayEngine:
    """Releases scheduled packets in arrival order as the logical clock advances."""

    def __init__(self) -> None:
        self.clock = VirtualClock()
        self._queue: list[tuple[float, int, str, str, int, Packet]] = []
        self._insertion = 0
        self._delivered: dict[tuple[str, str, int], Packet] = {}
        self._scheduled_keys: set[tuple[str, str, int]] = set()
        self.receiver = Receiver(self._delivered)

    @staticmethod
    def packetize(
        trace: Trace, packet_len_samples: int, delay_s: float = 0.0, first_sequence_number: int = 0
    ) -> list[Packet]:
        """Split a trace into packets; ready = time of last sample, arrival = ready + delay_s."""
        if packet_len_samples < 1:
            raise ValueError("packet_len_samples must be >= 1")
        if delay_s < 0.0:
            raise ValueError("delay_s must be >= 0")
        rate = trace.sample_rate_hz
        packets = []
        base = trace.first_sample_index
        for seq, start in enumerate(range(0, len(trace.samples), packet_len_samples), start=first_sequence_number):
            chunk = trace.samples[start : start + packet_len_samples]
            ready = (base + start + len(chunk) - 1) / rate
            packets.append(
                Packet(
                    station_id=trace.station_id,
                    channel_id=trace.channel_id,
                    sequence_number=seq,
                    sample_rate_hz=rate,
                    first_sample_index=base + start,
                    first_sample_time_s=(base + start) / rate,
                    samples=chunk,
                    ready_time_s=ready,
                    arrival_time_s=ready + delay_s,
                )
            )
        return packets

    def schedule(self, packets: Sequence[Packet], allow_duplicates: bool = False) -> None:
        """Queue packets for delivery. Packets already past the clock would violate causality.

        With allow_duplicates=True the same packet key may be scheduled more than once (a "duplicate" network
        fault); the receiver keeps the first delivered copy, advance_to returns every delivery.
        """
        for p in packets:
            if p.key in self._scheduled_keys and not allow_duplicates:
                raise ValueError(f"duplicate packet {p.key}")
            if p.arrival_time_s < self.clock.now_s:
                raise ValueError(f"packet {p.key} arrives at {p.arrival_time_s}, before clock {self.clock.now_s}")
            self._scheduled_keys.add(p.key)
            # Order: arrival time, then sequence number, then station (channel and insertion as final ties).
            heapq.heappush(
                self._queue,
                (p.arrival_time_s, p.sequence_number, p.station_id, p.channel_id, self._insertion, p),
            )
            self._insertion += 1

    @property
    def next_arrival_time_s(self) -> float | None:
        return self._queue[0][0] if self._queue else None

    def advance_to(self, t_s: float) -> list[Packet]:
        """Move the logical clock to t_s and return packets with arrival_time_s <= t_s, in delivery order."""
        self.clock.advance_to(t_s)
        released = []
        while self._queue and self._queue[0][0] <= t_s:
            packet = heapq.heappop(self._queue)[-1]
            self._delivered.setdefault(packet.key, packet)
            released.append(packet)
        return released
