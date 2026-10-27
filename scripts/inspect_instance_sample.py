"""Read-only inventory of the INSTANCE v3 sample dataset (metadata CSVs + HDF5 structure).

Does NOT run any detector or preprocessing. Opens HDF5 files in read-only mode and only reads
dataset shapes/dtypes (waveform samples are not read). Requires the `data` extra (h5py).

    python scripts/inspect_instance_sample.py --data-dir data/instance_sample \
        --out data/instance_sample/inventory.json
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

EVENTS_CSV = "metadata/metadata_Instance_events_10k.csv"
NOISE_CSV = "metadata/metadata_Instance_noise_1k.csv"
EVENTS_HDF5 = "data/Instance_events_counts_10k.hdf5"
NOISE_HDF5 = "data/Instance_noise_1k.hdf5"
CANDIDATE = "11032751.MN.AQU..HH"


class TraceName(NamedTuple):
    source_id: str
    network: str
    station: str
    location: str  # may be empty
    channel_family: str  # e.g. HH, HN, EH (the last field; the component letter is NOT part of it)


def split_trace_name(name: str) -> TraceName:
    """Split 'source_id.NET.STA.LOC.CHAN'. LOC may be empty. Raises ValueError otherwise."""
    parts = name.split(".")
    if len(parts) != 5 or not parts[0] or not parts[1] or not parts[2] or not parts[4]:
        raise ValueError(f"unexpected trace_name format: {name!r}")
    return TraceName(*parts)


def parse_utc(text: str) -> datetime:
    """Parse '2016-12-04T16:23:14.51Z' (1 to 6 fractional digits, trailing Z). Raises ValueError otherwise."""
    if not text.endswith("Z"):
        raise ValueError(f"expected trailing Z: {text!r}")
    body = text[:-1]
    base, _, frac = body.partition(".")
    if not frac.isdigit() and frac != "" or len(frac) > 6:
        raise ValueError(f"bad fractional seconds: {text!r}")
    dt = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.replace(microsecond=int(frac.ljust(6, "0")) if frac else 0)


def p_sample_offsets(rows: Iterable[dict[str, str]]) -> dict:
    """Metadata self-consistency: (P_arrival_time - trace_start_time)/dt minus trace_P_arrival_sample, per row.

    Rounded to the nearest 0.001 sample; distribution reported as {offset: count}.
    """
    offsets: Counter = Counter()
    sample_idx = []
    for r in rows:
        dt = float(r["trace_dt_s"])
        implied = (parse_utc(r["trace_P_arrival_time"]) - parse_utc(r["trace_start_time"])).total_seconds() / dt
        stated = int(float(r["trace_P_arrival_sample"]))
        sample_idx.append(stated)
        offsets[round(implied - stated, 3)] += 1
    return {
        "implied_minus_stated_samples": {str(k): v for k, v in sorted(offsets.items())},
        "P_sample_min": min(sample_idx),
        "P_sample_max": max(sample_idx),
    }


def read_csv_rows(path: str | Path) -> Iterator[dict[str, str]]:
    with open(path, newline="") as f:
        yield from csv.DictReader(f)


def _present(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def summarize_rows(rows: Iterable[dict[str, str]]) -> dict:
    """Counts over metadata rows; works for both the event and the noise CSV (missing columns -> absent)."""
    n = 0
    fam, dt, npts, nets, bad_names = Counter(), Counter(), Counter(), Counter(), []
    eval_p, p_sample_present, eval_by_family, units, source_type = Counter(), 0, Counter(), Counter(), Counter()
    station_ids, columns = set(), None
    for row in rows:
        n += 1
        columns = columns or list(row)
        try:
            tn = split_trace_name(row["trace_name"])
        except ValueError:
            bad_names.append(row.get("trace_name"))
            continue
        fam[tn.channel_family] += 1
        nets[tn.network] += 1
        station_ids.add((tn.network, tn.station))
        dt[row.get("trace_dt_s", "")] += 1
        npts[row.get("trace_npts", "")] += 1
        if "trace_eval_P" in row:
            eval_p[row["trace_eval_P"] or "<empty>"] += 1
            eval_by_family[(tn.channel_family, row["trace_eval_P"] or "<empty>")] += 1
            p_sample_present += _present(row.get("trace_P_arrival_sample"))
        if "trace_deconvolved_units" in row:
            units[row["trace_deconvolved_units"] or "<empty>"] += 1
        if "source_type" in row:
            source_type[row["source_type"] or "<empty>"] += 1
    return {
        "rows": n,
        "columns": columns,
        "unparseable_trace_names": bad_names[:20],
        "n_unparseable_trace_names": len(bad_names),
        "channel_family": dict(fam),
        "trace_dt_s": dict(dt),
        "trace_npts": dict(npts),
        "networks": dict(nets),
        "n_stations": len(station_ids),
        "trace_eval_P": dict(eval_p),
        "trace_eval_P_by_channel_family": {f"{k[0]}|{k[1]}": v for k, v in sorted(eval_by_family.items())},
        "rows_with_P_arrival_sample": p_sample_present,
        "trace_deconvolved_units": dict(units),
        "source_type": dict(source_type),
    }


def noise_partner_counts(event_rows: Iterable[dict[str, str]], noise_rows: Iterable[dict[str, str]]) -> dict:
    """How many event traces share a station (net.sta) or net.sta.loc.family with some noise trace.

    The CSVs carry no explicit event<->noise pairing field, so this is a station-level coincidence count only.
    """
    noise_sta, noise_full = set(), set()
    for r in noise_rows:
        t = split_trace_name(r["trace_name"])
        noise_sta.add((t.network, t.station))
        noise_full.add((t.network, t.station, t.location, t.channel_family))
    total = by_sta = by_full = 0
    by_family: Counter = Counter()
    for r in event_rows:
        t = split_trace_name(r["trace_name"])
        total += 1
        s = (t.network, t.station) in noise_sta
        f = (t.network, t.station, t.location, t.channel_family) in noise_full
        by_sta += s
        by_full += f
        by_family[(t.channel_family, f)] += 1
    return {
        "event_traces": total,
        "with_noise_trace_same_station": by_sta,
        "with_noise_trace_same_station_location_family": by_full,
        "by_family_full_match": {f"{k[0]}|{'match' if k[1] else 'no_match'}": v for k, v in sorted(by_family.items())},
    }


def hdf5_inventory(path: str | Path, csv_names: list[str], sample_key: str | None = None) -> dict:
    """Structure of one HDF5 file (read-only; no waveform samples read) and CSV<->HDF5 key cross-check."""
    import h5py

    with h5py.File(path, "r") as h:
        data = h["data"]
        keys = set(data.keys())
        shapes, dtypes = Counter(), Counter()
        for k in keys:
            d = data[k]
            shapes[str(d.shape)] += 1
            dtypes[str(d.dtype)] += 1
        fmt = {k: (v[()].decode() if isinstance(v[()], bytes) else str(v[()])) for k, v in h["data_format"].items()}
        csv_set = set(csv_names)
        out = {
            "top_level": list(h.keys()),
            "file_attrs": {k: str(v) for k, v in h.attrs.items()},
            "data_group_attrs": {k: str(v) for k, v in data.attrs.items()},
            "n_datasets": len(keys),
            "shapes": dict(shapes),
            "dtypes": dict(dtypes),
            "data_format": fmt,
            "dataset_attrs_example": {k: str(v) for k, v in data[next(iter(keys))].attrs.items()},
            "csv_names": len(csv_names),
            "csv_names_unique": len(csv_set),
            "csv_names_missing_in_hdf5": sorted(csv_set - keys)[:20],
            "n_csv_names_missing_in_hdf5": len(csv_set - keys),
            "hdf5_keys_missing_in_csv": sorted(keys - csv_set)[:20],
            "n_hdf5_keys_missing_in_csv": len(keys - csv_set),
        }
        if sample_key is not None:
            out["sample_key"] = {"name": sample_key, "present": sample_key in keys}
            if sample_key in keys:
                out["sample_key"].update(shape=list(data[sample_key].shape), dtype=str(data[sample_key].dtype))
    return out


def build_inventory(data_dir: str | Path) -> dict:
    root = Path(data_dir)
    events = list(read_csv_rows(root / EVENTS_CSV))
    noise = list(read_csv_rows(root / NOISE_CSV))
    cand_rows = [r for r in events if r["trace_name"] == CANDIDATE]
    return {
        "events_csv": summarize_rows(events),
        "noise_csv": summarize_rows(noise),
        "noise_partners": noise_partner_counts(events, noise),
        "events_hdf5_counts": hdf5_inventory(root / EVENTS_HDF5, [r["trace_name"] for r in events], CANDIDATE),
        "noise_hdf5": hdf5_inventory(root / NOISE_HDF5, [r["trace_name"] for r in noise]),
        "p_sample_offsets": p_sample_offsets(events),
        "rows_with_any_spike_flag": sum(any(float(r[f"trace_{c}_spikes"] or 0) > 0 for c in "ENZ") for r in events),
        "candidate_csv_rows": cand_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/instance_sample")
    parser.add_argument("--out", default=None, help="write JSON here (default: stdout)")
    args = parser.parse_args()
    text = json.dumps(build_inventory(args.data_dir), indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
