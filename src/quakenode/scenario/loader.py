"""Scenario sources: SYNTHETIC network or a real recorded INSTANCE event. Both yield the same ScenarioData."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from quakenode.config import ExperimentConfig
from quakenode.replay import Packet
from quakenode.scenario.synthetic_network import (
    SYNTHETIC_LABEL,
    EventSpec,
    NetworkSpec,
    StationSpec,
    build_packets,
    p_arrival_time_s,
)


@dataclass
class ScenarioData:
    source: str  # synthetic_network | instance_event
    input_kind: str  # synthetic | release_hdf5 | mseed
    label: dict[str, Any]  # what the data are; copied into metrics.json, the report and the manifest
    channel_id: str
    sample_rate_hz: float
    duration_s: float
    # one dict per station: station_id, p_time_s (timeline), n_samples_total, duration_s, p_uncertainty_s, start_time_s
    stations: list[dict[str, Any]]
    packets_fn: Callable[[int], list[Packet]]  # seed -> clean packets (real data ignore the seed)
    station_info: dict[str, dict[str, Any]] = field(default_factory=dict)
    exclusions: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    default_event_reference: str = "kth_p"
    file_hashes: dict[str, str] = field(default_factory=dict)  # path -> sha256 of real input files


def network_spec(cfg: ExperimentConfig) -> NetworkSpec:
    sc = cfg.scenario
    ev = sc.event
    return NetworkSpec(
        stations=tuple(StationSpec(s.id, s.x_km, s.y_km) for s in sc.stations),
        event=None if ev is None else EventSpec(ev.origin_time_s, ev.x_km, ev.y_km, ev.depth_km, ev.amplitude),
        duration_s=sc.duration_s,
        sample_rate_hz=sc.sample_rate_hz,
        packet_len_samples=sc.packet_len_samples,
        velocity_km_s=sc.velocity_km_s,
        noise_sigma=sc.noise_sigma,
        baseline_counts=sc.baseline_counts,
        amplitude_ref_km=sc.amplitude_ref_km,
        coda_decay_per_s=sc.coda_decay_per_s,
        pulse_freq_hz=sc.pulse_freq_hz,
    )


def load_synthetic(cfg: ExperimentConfig) -> ScenarioData:
    spec = network_spec(cfg)
    n_total = round(spec.duration_s * spec.sample_rate_hz)
    stations = [
        {
            "station_id": st.id,
            "p_time_s": p_arrival_time_s(spec, st) if spec.event is not None else None,
            "n_samples_total": n_total,
            "duration_s": spec.duration_s,
            "p_uncertainty_s": None,
            "start_time_s": 0.0,
        }
        for st in spec.stations
    ]
    return ScenarioData(
        source="synthetic_network",
        input_kind="synthetic",
        label={
            "source": "synthetic_network",
            "input_kind": "synthetic",
            "label": SYNTHETIC_LABEL,
            "notice": "SYNTHETIC data generated in-process; not a seismological model.",
        },
        channel_id=spec.channel_id,
        sample_rate_hz=spec.sample_rate_hz,
        duration_s=spec.duration_s,
        stations=stations,
        packets_fn=lambda seed: build_packets(spec, seed),
        station_info={st.id: {"x_km": st.x_km, "y_km": st.y_km} for st in spec.stations},
        warnings=[
            "All data in this run are SYNTHETIC (generated in-process); results support software-invariant claims only."
        ],
    )


def load_scenario(cfg: ExperimentConfig) -> ScenarioData:
    if cfg.scenario.source == "instance_event":
        from quakenode.data.instance_event import load_instance_event

        return load_instance_event(cfg.scenario.instance)  # type: ignore[arg-type]
    return load_synthetic(cfg)
