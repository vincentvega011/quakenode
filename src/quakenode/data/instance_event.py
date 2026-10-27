"""Replay a real recorded INSTANCE event (needs the `data` extra and the user's own downloaded INSTANCE sample).

This is a TOOL DEMONSTRATION source. Every output built from it is labeled with its input kind:

  release_hdf5  the INSTANCE release product (full-window detrended/resampled counts, int32). It is NOT causal input:
                the release processing used the whole 120 s window.
  mseed         the original INGV miniSEED, cut at the nearest raw sample to the metadata start time, no shifting.

Timeline: all stations are placed on one clock whose zero is the earliest trace start time of the event; station i's
first sample has timeline index round((start_i - start_min) * rate). Catalog P time of station i =
(index_i + trace_P_arrival_sample_i) / rate (the sample clock); the stated P uncertainty is carried along and reported
with every number. P picks are reviewed picks with that stated uncertainty; they are the reference, not truth.
Missing station metadata are None with a reason; nothing is invented.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from quakenode.data.instance import (
    TraceRecord,
    load_raw_window,
    load_release_z,
    make_stream_packets,
    parse_utc_ns,
)
from quakenode.scenario.loader import ScenarioData

CSV_NAME = "metadata/metadata_Instance_events_10k.csv"
HDF5_NAME = "data/Instance_events_counts_10k.hdf5"
N_SAMPLES = 12000
RATE_HZ = 100.0
INSTANCE_DOI = "10.13127/instance"
# Network DOIs known from docs/instance_access.md (INGV FDSN station service, read 2026-10-26). Others were not checked.
NETWORK_DOIS = {"IV": "10.13127/sd/x0fxnh7qfy", "MN": "10.13127/sd/fbbbtdtd6q"}
INPUT_LABELS = {
    "release_hdf5": "INSTANCE release product, full-window processed, NOT causal input",
    "mseed": "raw INGV miniSEED (cut at the nearest raw sample, no shifting)",
}
_HASH_CACHE: dict[tuple[str, int, int], str] = {}


def sha256_cached(path: Path) -> str:
    st = path.stat()
    key = (str(path.resolve()), st.st_size, st.st_mtime_ns)
    if key not in _HASH_CACHE:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _HASH_CACHE[key] = h.hexdigest()
    return _HASH_CACHE[key]


def select_event_rows(
    rows: list[dict[str, str]], event_id: str, network: str, family: str, stations: list[str] | None = None
) -> list[dict[str, str]]:
    """Metadata rows of one event for a network and channel family (optionally some stations), sorted by name."""
    out = []
    for r in rows:
        parts = r["trace_name"].split(".")
        if len(parts) != 5 or r["source_id"] != event_id or parts[1] != network or parts[4] != family:
            continue
        if stations is not None and parts[2] not in stations:
            continue
        out.append(r)
    return sorted(out, key=lambda r: r["trace_name"])


def station_metadata(row: dict[str, str]) -> dict[str, Any]:
    """Coordinates from the event CSV; a missing or empty field is None with a reason, never a guess."""
    info: dict[str, Any] = {}
    for key, col in (("latitude_deg", "station_latitude_deg"), ("longitude_deg", "station_longitude_deg"),
                     ("elevation_m", "station_elevation_m")):  # fmt: skip
        raw = row.get(col)
        if raw in (None, ""):
            info[key], info[f"{key}_missing_reason"] = None, f"column {col!r} absent or empty in the event CSV"
        else:
            info[key] = float(raw)
    return info


def timeline_indices(start_times_utc: list[str], rate_hz: float = RATE_HZ) -> list[int]:
    """Timeline index of each station's first sample (zero = earliest start); rounds to the nearest sample."""
    ns = [parse_utc_ns(t) for t in start_times_utc]
    t0 = min(ns)
    step = 1e9 / rate_hz
    return [round((v - t0) / step) for v in ns]


def load_instance_event(cfg: Any, n_samples: int = N_SAMPLES) -> ScenarioData:
    """Build the ScenarioData for a config.scenario.instance section (InstanceEventConfig).

    n_samples is the window length (12,000 for INSTANCE); tests pass a small value for fabricated files.
    """
    data_dir = Path(cfg.data_dir)
    csv_path, hdf5 = data_dir / CSV_NAME, data_dir / HDF5_NAME
    for p in (csv_path, hdf5):
        if not p.exists():
            raise FileNotFoundError(
                f"{p} not found. Download and extract the INSTANCE sample (see examples/instance_event/README.md); "
                "waveform data are never part of the repository."
            )
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = select_event_rows(list(csv.DictReader(f)), cfg.event_id, cfg.network, cfg.channel_family, cfg.stations)
    if not rows:
        raise ValueError(f"no {cfg.network}.{cfg.channel_family} traces for event {cfg.event_id!r} in {csv_path}")

    raw_dir = Path(cfg.raw_dir)
    usable: list[tuple[TraceRecord, Any, dict[str, Any]]] = []
    exclusions: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    for row in rows:
        rec = TraceRecord.from_metadata_row(row)
        if cfg.input == "release_hdf5":
            samples = load_release_z(hdf5, rec.trace_name)
        else:
            path = raw_dir / f"{rec.trace_name.replace('..', '.')}.Z.mseed"
            w = load_raw_window(path, rec.trace_start_time, n_samples, RATE_HZ)
            if w.exclusion_reason:
                exclusions.append({"trace": rec.trace_name, "station": rec.station, "reason": w.exclusion_reason,
                                   "detail": w.detail})  # fmt: skip
                continue
            samples = w.samples
            hashes[str(path)] = sha256_cached(path)
        usable.append((rec, samples, station_metadata(row)))
    if len(usable) < cfg.min_stations:
        raise ValueError(
            f"event {cfg.event_id}: only {len(usable)} usable station(s), min_stations is {cfg.min_stations}; "
            f"exclusions: {exclusions}"
        )
    indices = timeline_indices([rec.trace_start_time for rec, _, _ in usable])
    packets_by_station = {}
    stations, info = [], {}
    for (rec, samples, meta), idx0 in zip(usable, indices, strict=True):
        n = len(samples)
        packets_by_station[rec.station] = make_stream_packets(
            samples, station_id=rec.station, channel_id="HHZ", sample_rate_hz=RATE_HZ,
            packet_len_samples=cfg.packet_len_samples, first_sample_index=idx0,
        )  # fmt: skip
        stations.append({
            "station_id": rec.station, "p_time_s": (idx0 + rec.p_sample) / RATE_HZ, "n_samples_total": n,
            "duration_s": n / RATE_HZ, "p_uncertainty_s": rec.p_uncertainty_s, "start_time_s": idx0 / RATE_HZ,
        })  # fmt: skip
        info[rec.station] = {
            **meta,
            "trace_name": rec.trace_name,
            "network": rec.network,
            "p_sample": rec.p_sample,
            "p_uncertainty_s": rec.p_uncertainty_s,
            "magnitude": rec.magnitude,
            "epicentral_distance_km": rec.epicentral_distance_km,
        }
    packets = [p for st in stations for p in packets_by_station[st["station_id"]]]
    hashes[str(hdf5)] = sha256_cached(hdf5) if cfg.input == "release_hdf5" else ""
    hashes[str(csv_path)] = sha256_cached(csv_path)
    hashes = {k: v for k, v in hashes.items() if v}
    nets = sorted({r.network for r, _, _ in usable})
    label = {
        "source": "instance_event",
        "input_kind": cfg.input,
        "input_description": INPUT_LABELS[cfg.input],
        "event_id": cfg.event_id,
        "data_source": "INSTANCE v3 sample (INGV), events_counts HDF5 and events metadata CSV",
        "doi": INSTANCE_DOI,
        "license": "CC BY 4.0 (INGV INSTANCE page)",
        "network_dois": {n: NETWORK_DOIS.get(n) for n in nets},
        "network_dois_note": "None = not checked in this repository",
        "p_reference": "catalog P sample per station (reviewed pick) with its stated uncertainty; reference, not truth",
        "tool_demonstration": True,
    }
    warnings = [
        f"REAL RECORDED EVENT {cfg.event_id}, input kind {cfg.input}: {INPUT_LABELS[cfg.input]}.",
        "Tool demonstration only: not performance evidence; no scientific claim may be drawn from this run.",
    ]
    if cfg.input == "release_hdf5":
        warnings.append("The release product was processed over the whole 120 s window: this is NOT causal input.")
    return ScenarioData(
        source="instance_event", input_kind=cfg.input, label=label, channel_id="HHZ", sample_rate_hz=RATE_HZ,
        duration_s=n_samples / RATE_HZ, stations=stations, packets_fn=lambda seed: list(packets), station_info=info,
        exclusions=exclusions, warnings=warnings, default_event_reference="earliest_p", file_hashes=hashes,
    )  # fmt: skip


def hashes_to_json(hashes: dict[str, str]) -> str:
    return json.dumps(hashes, sort_keys=True)
