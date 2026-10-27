"""EXPLORATORY follow-up to the pre-registered detrend check (does not affect the verdict).

Reads the per-trace CSV and the cached miniSEED written by scripts/run_detrend_check.py; prints a JSON report.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections import Counter
from pathlib import Path

import h5py
import numpy as np
import obspy

from scripts.run_detrend_check import N_SAMPLES, Z_INDEX, linear_fit_subtract


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default="data/instance_sample")
    ap.add_argument("--raw-dir", default="data/raw/detrend_check")
    ap.add_argument("--run-dir", default="data/instance_sample/detrend_check")
    args = ap.parse_args()
    root, raw_dir, run_dir = Path(args.data_dir), Path(args.raw_dir), Path(args.run_dir)
    rows = list(csv.DictReader(open(run_dir / "per_trace.csv", newline="")))
    meta = {r["trace_name"]: r for r in csv.DictReader(open(root / "metadata/metadata_Instance_events_10k.csv"))}

    # E1: structure of hdf5 - trunc(T1) by sign of y, and shrink of |y| relative to |hdf5|.
    resid_by_sign: Counter = Counter()
    shrink_bins: dict[str, Counter] = {"y>0": Counter(), "y<0": Counter()}
    n_traces = 0
    frac_table = np.zeros((10, 2), dtype=np.int64)  # rows: frac(|y|) decile; cols: shift 0 or 1
    eh = []  # per-trace (max_abs, rms, n_nonzero) of hdf5 - (rint(y) - sign(rint(y)))
    with h5py.File(root / "data/Instance_events_counts_10k.hdf5", "r") as h5:
        for r in rows:
            if r["status"] != "comparable":
                continue
            name = r["trace_name"]
            st = obspy.read(io.BytesIO((raw_dir / f"{name.replace('..', '.')}.Z.mseed").read_bytes()))
            k0 = int(r["k0"])
            w = st[0].data[k0 : k0 + N_SAMPLES].astype(float)
            y = linear_fit_subtract(w)
            hdf = h5["data"][name][Z_INDEX].astype(np.int64)
            res = hdf - np.trunc(y).astype(np.int64)
            for sgn, mask in (("y>0", y > 0), ("y<0", y < 0)):
                resid_by_sign.update({(sgn, int(v)): int(c) for v, c in zip(*np.unique(res[mask], return_counts=True))})
                shrink = np.abs(y[mask]) - np.abs(hdf[mask])  # >0 means hdf5 is closer to zero than y
                shrink_bins[sgn].update(np.floor(shrink).astype(int).tolist())
            big = np.abs(y) >= 2
            shift = np.abs(np.trunc(y)).astype(int)[big] - np.abs(hdf)[big]
            decile = np.minimum(((np.abs(y) % 1.0)[big] * 10).astype(int), 9)
            for d, sh in zip(decile, shift, strict=True):
                if sh in (0, 1):
                    frac_table[d, int(sh)] += 1
            ry = np.rint(y).astype(np.int64)
            e = hdf - (ry - np.sign(ry))
            eh.append((int(np.abs(e).max()), float(np.sqrt((e.astype(float) ** 2).mean())), int((e != 0).sum())))
            n_traces += 1

    # E2: who is excluded, by reason, family and station.
    excl = Counter(
        (r["reason"], r["family"], meta[r["trace_name"]]["station_code"][:2]) for r in rows if r["status"] == "excluded"
    )
    resampled = Counter(
        (r["family"], r["trace_name"].split(".")[2], r["raw_rate_hz"])
        for r in rows
        if r["reason"] == "native_rate_not_100hz"
    )
    out = {
        "n_traces": n_traces,
        "E1_hdf5_minus_trunc_T1_by_sign_of_y": {f"{k[0]}|{k[1]:+d}": v for k, v in sorted(resid_by_sign.items())},
        "E1_floor_of_(|y|-|hdf5|)_by_sign_of_y": {s: dict(sorted(c.items())) for s, c in shrink_bins.items()},
        "E3_shift_vs_frac_of_abs_y": {
            f"{i / 10:.1f}-{(i + 1) / 10:.1f}": {"shift0": int(frac_table[i, 0]), "shift1": int(frac_table[i, 1])}
            for i in range(10)
        },
        "E3_rint_minus_sign_hypothesis": {
            "traces_with_max_abs_0": sum(1 for m, _, _ in eh if m == 0),
            "traces_with_max_abs_le_1": sum(1 for m, _, _ in eh if m <= 1),
            "traces_with_max_abs_le_2": sum(1 for m, _, _ in eh if m <= 2),
            "median_n_nonzero_samples": float(np.median([n for _, _, n in eh])),
            "max_of_max_abs": max(m for m, _, _ in eh),
            "median_rms": float(np.median([r for _, r, _ in eh])),
        },
        "E2_exclusions_by_reason_family_station_prefix": {"|".join(k): v for k, v in sorted(excl.items())},
        "E2_resampled_by_family_station_rate": {"|".join(map(str, k)): v for k, v in sorted(resampled.items())},
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
