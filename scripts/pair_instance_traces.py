"""Compare INSTANCE HDF5 Z arrays with original INGV FDSN miniSEED (read-only; no detector, no tuning).

For each trace: download the raw Z channel for [trace_start - 15 s, trace_start + 135 s] from INGV dataselect,
align on the nominal start (nearest raw sample), report the sample-rate match, the sub-sample start offset, and
the best integer lag from normalized cross-correlation (reported, never applied silently). Then evaluate a FIXED
list of hypotheses, each with no free parameters:

  a  identical to raw                           b  raw - mean(full downloaded trace)
  c1 raw - LSQ line over full downloaded trace  c2 raw - LSQ line over the exact window
  d  raw - mean(exact window)

Residual = HDF5 - hypothesis (max abs, RMS, count of nonzero), also after rounding or truncating the
hypothesis to integers (HDF5 is int32).

POST-HOC observation (found on the first trace, NOT one of the pre-listed hypotheses; reported for replication):
  S  hdf5 == x - sign(x), x = raw_window - c, with c = floor / round / trunc of mean(exact window).
Exact-match counts for S are reported per trace so the observation can fail on other traces.

    python scripts/pair_instance_traces.py --trace 11032751.MN.AQU..HH --out data/instance_sample/pairing.json
    python scripts/pair_instance_traces.py --random-iv 10 --seed 20261026 --out data/instance_sample/pairing_iv10.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

import h5py
import numpy as np
import obspy

FDSN = "https://webservices.ingv.it/fdsnws/dataselect/1/query"
Z_INDEX = 2  # HDF5 data_format/component_order is b"ENZ" in all three files -> Z is index 2
MAX_LAG = 100
PAD_BEFORE_S, PAD_AFTER_S = 15.0, 15.0


def stats(diff: np.ndarray) -> dict:
    d = diff.astype(float)
    return {"max_abs": float(np.abs(d).max()), "rms": float(np.sqrt((d**2).mean())), "n_nonzero": int((d != 0).sum())}


def hypotheses(raw_full: np.ndarray, start: int, n: int) -> dict[str, np.ndarray]:
    seg = raw_full[start : start + n].astype(float)
    x_full, x_win = np.arange(len(raw_full)), np.arange(n)
    full_fit = np.polyval(np.polyfit(x_full, raw_full.astype(float), 1), x_full)[start : start + n]
    win_fit = np.polyval(np.polyfit(x_win, seg, 1), x_win)
    return {
        "a_identical": seg,
        "b_minus_mean_full_trace": seg - raw_full.astype(float).mean(),
        "c1_minus_linear_trend_full_trace": seg - full_fit,
        "c2_minus_linear_trend_window": seg - win_fit,
        "d_minus_mean_trimmed_window": seg - seg.mean(),
    }


def shrink_rule(hdf: np.ndarray, seg: np.ndarray) -> dict:
    """Post-hoc rule S: hdf == x - sign(x) with x = seg - c, for three integer choices of c."""
    mean = float(seg.mean())
    out = {}
    for name, c in (("floor", int(np.floor(mean))), ("round", int(round(mean))), ("trunc", int(mean))):
        x = seg - c
        out[name] = {"c": c, "mismatches": int((hdf != x - np.sign(x)).sum())}
    return out


def evaluate(hdf: np.ndarray, raw: np.ndarray, nominal: int, n: int) -> dict:
    lags = list(range(-MAX_LAG, MAX_LAG + 1))
    hz = hdf.astype(float) - hdf.mean()
    ncc = []
    for lag in lags:
        lo = nominal + lag
        if lo < 0 or lo + n > len(raw):
            ncc.append(float("nan"))
            continue
        s = raw[lo : lo + n].astype(float)
        s -= s.mean()
        denom = np.sqrt((hz**2).sum() * (s**2).sum())
        ncc.append(float((hz * s).sum() / denom) if denom > 0 else float("nan"))
    ok = [i for i, v in enumerate(ncc) if v == v]
    top = sorted(ok, key=lambda i: ncc[i], reverse=True)[:3]
    res = {
        "xcorr_top3": [{"lag_samples": lags[i], "ncc": ncc[i]} for i in top],
        "best_integer_lag_samples": lags[top[0]] if top else None,
        "ncc_at_nominal": ncc[lags.index(0)],
    }
    for label, lag in (("nominal_alignment", 0), ("best_lag_alignment", res["best_integer_lag_samples"])):
        if lag is None or nominal + lag < 0 or nominal + lag + n > len(raw):
            res[label] = None
            continue
        hyp = {}
        for name, h in hypotheses(raw, nominal + lag, n).items():
            hyp[name] = {
                "residual": stats(hdf - h),
                "residual_after_round_to_int": stats(hdf - np.round(h)),
                "residual_after_truncate_to_int": stats(hdf - np.trunc(h)),
            }
        res[label] = {
            "lag_samples": lag,
            "hypotheses": hyp,
            "post_hoc_shrink_rule_S": shrink_rule(hdf, raw[nominal + lag : nominal + lag + n].astype(np.int64)),
        }
    return res


def fetch_mseed(net: str, sta: str, loc: str, cha: str, start: obspy.UTCDateTime, end: obspy.UTCDateTime) -> bytes:
    q = {
        "network": net, "station": sta, "location": loc or "--", "channel": cha,
        "starttime": start.strftime("%Y-%m-%dT%H:%M:%S"), "endtime": end.strftime("%Y-%m-%dT%H:%M:%S"),
        "format": "miniseed",
    }  # fmt: skip
    url = FDSN + "?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (fixed https endpoint)
        return r.read()


def pair_one(h5: h5py.File, row: dict, raw_dir: Path) -> dict:
    name = row["trace_name"]
    _, net, sta, loc, fam = name.split(".")
    n, dt = int(row["trace_npts"]), float(row["trace_dt_s"])
    start = obspy.UTCDateTime(row["trace_start_time"])
    info: dict = {"trace": name, "channel_family": fam, "trace_start_time": row["trace_start_time"]}
    t0 = time.time()
    try:
        blob = fetch_mseed(net, sta, loc, fam + "Z", start - PAD_BEFORE_S, start + n * dt + PAD_AFTER_S)
    except Exception as exc:  # network/HTTP error is a result, not a crash
        return {**info, "fetch_error": f"{type(exc).__name__}: {exc}"}
    info["fetch_seconds"] = round(time.time() - t0, 2)
    info["mseed_bytes"] = len(blob)
    if not blob:
        return {**info, "fetch_error": "empty response"}
    raw_path = raw_dir / f"{name.replace('..', '.')}.Z.mseed"
    raw_path.write_bytes(blob)
    info["mseed_sha256"] = hashlib.sha256(blob).hexdigest()
    st = obspy.read(io.BytesIO(blob))
    info["n_traces_in_response"] = len(st)
    if len(st) != 1:
        return {**info, "skipped": "response has more than one trace (gaps or overlaps); not merged"}
    tr = st[0]
    raw = tr.data.astype(np.int64)
    off = (start - tr.stats.starttime) / dt
    nominal = int(round(off))
    info.update(
        raw_id=tr.id, raw_start=str(tr.stats.starttime), raw_npts=int(tr.stats.npts),
        raw_rate_hz=float(tr.stats.sampling_rate), sample_rate_match=bool(abs(tr.stats.sampling_rate * dt - 1) < 1e-9),
        metadata_start_minus_raw_start_samples=off, sub_sample_misalignment_s=(off - nominal) * dt,
        hdf5_min_max_mean=None,
    )  # fmt: skip
    hdf = h5["data"][name][Z_INDEX].astype(np.int64)
    info["hdf5_min_max_mean"] = [int(hdf.min()), int(hdf.max()), float(hdf.mean())]
    info["raw_window_mean"] = float(raw[nominal : nominal + n].mean()) if nominal + n <= len(raw) else None
    info["evaluation"] = evaluate(hdf, raw, nominal, n)
    return info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="data/instance_sample")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--trace", action="append", default=[], help="trace_name (repeatable)")
    ap.add_argument("--random-iv", type=int, default=0, help="seeded random sample of N IV-network traces")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.data_dir)
    with open(root / "metadata/metadata_Instance_events_10k.csv", newline="") as f:
        rows = {r["trace_name"]: r for r in csv.DictReader(f)}
    names = list(args.trace)
    if args.random_iv:
        if args.seed is None:
            raise SystemExit("--random-iv requires --seed")
        pool = sorted(n for n in rows if n.split(".")[1] == "IV" and n not in names)
        names += random.Random(args.seed).sample(pool, args.random_iv)
    Path(args.raw_dir).mkdir(parents=True, exist_ok=True)
    results = []
    with h5py.File(root / "data/Instance_events_counts_10k.hdf5", "r") as h5:
        assert h5["data_format/component_order"][()] == b"ENZ"
        for name in names:
            results.append(pair_one(h5, rows[name], Path(args.raw_dir)))
    text = json.dumps({"seed": args.seed, "traces": results}, indent=2, sort_keys=True)
    Path(args.out).write_text(text + "\n")
    print(f"wrote {args.out}: {len(results)} traces")


if __name__ == "__main__":
    main()
