"""SYNTHETIC multi-station network scenario. Not a seismological model.

N stations at planar coordinates (km) and, optionally, one event with an origin time, a location and an amplitude.
Everything here is invented to exercise the software:

  P arrival at a station:  t_P = origin_time + hypot(dx, dy, depth) / velocity   (constant velocity, straight ray)
  amplitude at distance r: A(r) = amplitude / (1 + r / amplitude_ref_km)          (arbitrary decay law)
  signal after t_P:        A(r) * exp(-coda_decay_per_s * tau) * sin(2 pi f tau),  tau = t - t_P
  trace = baseline_counts + noise (Gaussian, sigma noise_sigma) + signal

Noise is seeded per station from (seed, station id). Results support software-invariant claims only; they say
nothing about real earthquakes, real detectors on real data, or warning times.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from quakenode.faults.rng import Stream, derive_seed
from quakenode.replay import Packet, ReplayEngine, Trace

SYNTHETIC_LABEL = "SYNTHETIC"


@dataclass(frozen=True)
class StationSpec:
    id: str
    x_km: float
    y_km: float


@dataclass(frozen=True)
class EventSpec:
    origin_time_s: float
    x_km: float
    y_km: float
    depth_km: float = 10.0
    amplitude: float = 50.0


@dataclass(frozen=True)
class NetworkSpec:
    stations: tuple[StationSpec, ...]
    event: EventSpec | None
    duration_s: float = 60.0
    sample_rate_hz: float = 50.0
    packet_len_samples: int = 25
    velocity_km_s: float = 6.0
    noise_sigma: float = 1.0
    baseline_counts: float = 800.0
    amplitude_ref_km: float = 50.0
    coda_decay_per_s: float = 0.5
    pulse_freq_hz: float = 4.0
    channel_id: str = "SYN"


def hypocentral_distance_km(spec: NetworkSpec, station: StationSpec) -> float:
    ev = spec.event
    if ev is None:
        raise ValueError("scenario has no event")
    return math.sqrt((station.x_km - ev.x_km) ** 2 + (station.y_km - ev.y_km) ** 2 + ev.depth_km**2)


def p_arrival_time_s(spec: NetworkSpec, station: StationSpec) -> float:
    """True P arrival time on the sample clock (seconds from trace start)."""
    distance_km = hypocentral_distance_km(spec, station)  # raises ValueError when the scenario has no event
    return spec.event.origin_time_s + distance_km / spec.velocity_km_s  # type: ignore[union-attr]


def generate_trace(spec: NetworkSpec, station: StationSpec, seed: int) -> list[float]:
    """SYNTHETIC samples for one station (floats, count-like)."""
    n = round(spec.duration_s * spec.sample_rate_hz)
    rng = Stream(derive_seed(seed, "noise", station.id))
    out = [spec.baseline_counts + spec.noise_sigma * rng.normal() for _ in range(n)]
    if spec.event is not None:
        t_p = p_arrival_time_s(spec, station)
        amp = spec.event.amplitude / (1.0 + hypocentral_distance_km(spec, station) / spec.amplitude_ref_km)
        for i in range(n):
            tau = i / spec.sample_rate_hz - t_p
            if tau >= 0.0:
                out[i] += (
                    amp * math.exp(-spec.coda_decay_per_s * tau) * math.sin(2.0 * math.pi * spec.pulse_freq_hz * tau)
                )
    return out


def build_packets(spec: NetworkSpec, seed: int) -> list[Packet]:
    """Packetize every station's SYNTHETIC trace with identical timing rules (arrival = ready, no faults)."""
    packets: list[Packet] = []
    for st in spec.stations:
        trace = Trace(st.id, spec.channel_id, spec.sample_rate_hz, tuple(generate_trace(spec, st, seed)))
        packets.extend(ReplayEngine.packetize(trace, spec.packet_len_samples))
    return packets
