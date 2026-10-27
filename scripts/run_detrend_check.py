"""Pre-registered check: is the released INSTANCE Z array a reproducible transform of the INGV miniSEED?

Protocol, sample, exclusions, success criteria and decision rule are fixed in
docs/preregistration_detrend_check.md (committed before this script was run). Read-only on data/; no detector
is run. Requires the `data` extra.

    python scripts/run_detrend_check.py --data-dir data/instance_sample --raw-dir data/raw/detrend_check \
        --out-dir data/instance_sample/detrend_check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import subprocess
import time
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import numpy as np

PREREG = "docs/preregistration_detrend_check.md"
SEED = 20261101
N_PER_FAMILY = 100
FAMILIES = ("HH", "HN")
NETWORK = "IV"
N_SAMPLES = 12000
DT = 0.01
PAD_S = 15.0
SLEEP_S = 1.0
Z_INDEX = 2
LAG_RANGE = 2
FDSN = "https://webservices.ingv.it/fdsnws/dataselect/1/query"
USER_AGENT = "quakenode-research/0.0.1 (sequential, cached; contact via repository)"
CASTS = ("rint", "trunc", "floor")
TRANSFORMS = ("T1", "T2")
VARIANTS = tuple(f"{t}-{c}" for t in TRANSFORMS for c in CASTS)
EXCLUDED_CANDIDATES = (
    "11032751.MN.AQU..HH 1107931.IV.SALO..HH 11138771.IV.COR1..EH 11091901.IV.T1245..HH 11251911.IV.PTQR..HH "
    "11212081.IV.APEC..HH 11271611.IV.SMA1..EH 11069371.IV.CESI..HH 11032751.IV.GUMA..HN 11211211.IV.T1216..EH "
    "11280401.IV.CAMP..HH"
).split()
EXCLUSION_ORDER = (
    "fetch_failed",
    "native_rate_not_100hz",
    "gaps_or_overlaps",
    "raw_does_not_cover_window",
    "hdf5_all_zero",
)
# Success criteria, fixed in the pre-registration.
REPRODUCES_MAX_ABS = 1
APPROX_MAX_ABS = 2
APPROX_RMS = 1.5
EXPLAINS_FRACTION = 0.95
LAG_FINDING_FRACTION = 0.05


# ---- pure functions (unit-tested) -------------------------------------------------------------------------


def linear_fit_subtract(w: np.ndarray) -> np.ndarray:
    """T1: subtract the least-squares line fitted over the whole window (index 0..n-1)."""
    w = np.asarray(w, dtype=float)
    i = np.arange(len(w))
    return w - np.polyval(np.polyfit(i, w, 1), i)


def mean_subtract(w: np.ndarray) -> np.ndarray:
    """T2: subtract the window mean."""
    w = np.asarray(w, dtype=float)
    return w - w.mean()


def cast_int(y: np.ndarray, mode: str) -> np.ndarray:
    """Cast floats to integers: 'rint' (round half to even), 'trunc' (toward zero) or 'floor'."""
    fn = {"rint": np.rint, "trunc": np.trunc, "floor": np.floor}.get(mode)
    if fn is None:
        raise ValueError(f"unknown cast mode {mode!r}")
    return fn(np.asarray(y, dtype=float)).astype(np.int64)


def variant_output(w: np.ndarray, variant: str) -> np.ndarray:
    transform, cast = variant.split("-")
    if transform == "T1":
        return cast_int(linear_fit_subtract(w), cast)
    if transform == "T2":
        return cast_int(mean_subtract(w), cast)
    raise ValueError(f"unknown transform {transform!r}")


def residual_stats(hdf: np.ndarray, reproduced: np.ndarray) -> dict:
    r = np.asarray(hdf, dtype=np.int64) - np.asarray(reproduced, dtype=np.int64)
    return {
        "max_abs": int(np.abs(r).max()),
        "rms": float(np.sqrt((r.astype(float) ** 2).mean())),
        "n_nonzero": int((r != 0).sum()),
    }


def wilson_interval(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default). (nan, nan) if n == 0."""
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def draw_sample(trace_names: Sequence[str], families: Sequence[str], exclude: Sequence[str], seed: int, n: int) -> dict:
    """Per family: pool = IV traces of that family minus `exclude`, sorted by name, then a seeded sample of n."""
    excluded = set(exclude)
    out = {}
    for fam in families:
        pool = sorted(
            t for t in trace_names if t.split(".")[1] == NETWORK and t.split(".")[-1] == fam and t not in excluded
        )
        if len(pool) < n:
            raise ValueError(f"pool for {fam} has {len(pool)} < {n} traces")
        out[fam] = random.Random(seed).sample(pool, n)
    return out


def is_reproduced(stats: dict) -> bool:
    return stats["max_abs"] <= REPRODUCES_MAX_ABS


def is_approx(stats: dict) -> bool:
    return stats["max_abs"] <= APPROX_MAX_ABS and stats["rms"] <= APPROX_RMS


def percentile(values: Sequence[float], q: float) -> float | None:
    return float(np.percentile(np.asarray(values, dtype=float), q)) if len(values) else None


def summarize_variant(rows: Sequence[dict], variant: str) -> dict:
    """Counts, Wilson intervals and residual distributions for one variant over comparable rows."""
    n = len(rows)
    maxabs = [r[f"{variant}_max_abs"] for r in rows]
    rms = [r[f"{variant}_rms"] for r in rows]
    stats_list = [{"max_abs": r[f"{variant}_max_abs"], "rms": r[f"{variant}_rms"]} for r in rows]
    k_rep = sum(is_reproduced(s) for s in stats_list)
    k_app = sum(is_approx(s) for s in stats_list)
    k_exact = sum(m == 0 for m in maxabs)

    def prop(k: int) -> dict:
        lo, hi = wilson_interval(k, n)
        return {"k": k, "n": n, "proportion": (k / n if n else None), "wilson95": [lo, hi]}

    return {
        "reproduces_max_abs_le_1": prop(k_rep),
        "approx_max_abs_le_2_and_rms_le_1.5": prop(k_app),
        "exact_max_abs_0_descriptive": prop(k_exact),
        "max_abs": {
            "median": percentile(maxabs, 50), "p90": percentile(maxabs, 90),
            "p99": percentile(maxabs, 99), "max": (max(maxabs) if maxabs else None),
        },
        "rms": {
            "median": percentile(rms, 50), "p90": percentile(rms, 90),
            "p99": percentile(rms, 99), "max": (max(rms) if rms else None),
        },
    }  # fmt: skip


def verdict(pooled: dict[str, dict]) -> dict:
    """Apply the pre-registered decision rule to pooled summaries ({variant: summarize_variant})."""
    explaining = [v for v in VARIANTS if _prop(pooled[v], "reproduces_max_abs_le_1") >= EXPLAINS_FRACTION]
    approx = [v for v in VARIANTS if _prop(pooled[v], "approx_max_abs_le_2_and_rms_le_1.5") >= EXPLAINS_FRACTION]
    preferred = None
    if explaining:
        preferred = max(explaining, key=lambda v: (pooled[v]["exact_max_abs_0_descriptive"]["k"], -VARIANTS.index(v)))
    if explaining:
        offline = f"offline arm may be the reproduced transform {preferred}, labeled as a reproduction of the release"
    else:
        offline = (
            "offline arm must be the released HDF5 array itself, labeled as the release product, "
            "with the residual caveat"
        )
    return {
        "variants_that_explain_the_release": explaining,
        "variants_that_approximately_explain": approx,
        "preferred_variant": preferred,
        "offline_arm_decision": offline,
    }


def _prop(summary: dict, key: str) -> float:
    p = summary[key]["proportion"]
    return -1.0 if p is None else p


# ---- I/O ------------------------------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(name: str, start, raw_dir: Path, log: list[dict]) -> bytes | None:
    """Fetch (or reuse cached) miniSEED for the Z channel of a trace; log URL, status, bytes, sha256."""
    import obspy  # noqa: F401  (UTCDateTime arithmetic is done by the caller)

    _, net, sta, loc, fam = name.split(".")
    cache = raw_dir / f"{name.replace('..', '.')}.Z.mseed"
    q = {
        "network": net, "station": sta, "location": loc or "--", "channel": fam + "Z",
        "starttime": (start - PAD_S).strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": (start + N_SAMPLES * DT + PAD_S).strftime("%Y-%m-%dT%H:%M:%S"),
        "format": "miniseed",
    }  # fmt: skip
    url = FDSN + "?" + urllib.parse.urlencode(q)
    if cache.exists():
        blob = cache.read_bytes()
        log.append(
            {
                "trace": name,
                "url": url,
                "source": "cache",
                "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )
        return blob or None
    blob, err, status = b"", None, None
    for _attempt in (1, 2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (fixed https endpoint)
                status, blob = r.status, r.read()
            err = None
            break
        except Exception as exc:  # recorded, and retried once
            err = f"{type(exc).__name__}: {exc}"
            time.sleep(5.0)
    time.sleep(SLEEP_S)
    entry = {"trace": name, "url": url, "source": "network", "http_status": status, "bytes": len(blob), "error": err,
             "sha256": hashlib.sha256(blob).hexdigest() if blob else None}  # fmt: skip
    log.append(entry)
    if blob:
        raw_dir.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(blob)
    return blob or None


def best_lag(hdf: np.ndarray, raw: np.ndarray, k0: int) -> tuple[int | None, float | None]:
    hz = hdf.astype(float) - hdf.mean()
    best = (None, -2.0)
    for lag in range(-LAG_RANGE, LAG_RANGE + 1):
        lo = k0 + lag
        if lo < 0 or lo + N_SAMPLES > len(raw):
            continue
        s = raw[lo : lo + N_SAMPLES].astype(float)
        s -= s.mean()
        d = math.sqrt((hz**2).sum() * (s**2).sum())
        if d > 0 and (v := float((hz * s).sum() / d)) > best[1]:
            best = (lag, v)
    return best if best[0] is not None else (None, None)


def evaluate_trace(name: str, row: dict, hdf: np.ndarray, blob: bytes | None) -> dict:
    """One trace -> status row. Exclusions are checked in the pre-registered order."""
    import obspy

    out: dict = {"trace_name": name, "family": name.split(".")[-1], "status": "comparable", "reason": ""}

    def exclude(reason: str) -> dict:
        out.update(status="excluded", reason=reason)
        return out

    if blob is None:
        return exclude("fetch_failed")
    try:
        st = obspy.read(io.BytesIO(blob))
    except Exception as exc:
        out["detail"] = f"{type(exc).__name__}: {exc}"
        return exclude("fetch_failed")
    out["n_traces_in_response"] = len(st)
    rates = {float(tr.stats.sampling_rate) for tr in st}
    out["raw_rate_hz"] = sorted(rates)[0]
    if rates != {100.0}:
        return exclude("native_rate_not_100hz")
    if len(st) != 1:
        return exclude("gaps_or_overlaps")
    tr = st[0]
    raw = tr.data
    start = obspy.UTCDateTime(row["trace_start_time"])
    off = (start - tr.stats.starttime) / DT
    k0 = int(round(off))
    out.update(raw_npts=int(tr.stats.npts), raw_dtype=str(raw.dtype), k0=k0, sub_sample_offset_s=(off - k0) * DT)
    if k0 < 0 or k0 + N_SAMPLES > len(raw):
        return exclude("raw_does_not_cover_window")
    if not hdf.any():
        return exclude("hdf5_all_zero")
    lag, ncc = best_lag(hdf, raw, k0)
    out.update(best_lag=lag, ncc_at_best_lag=ncc)
    w = raw[k0 : k0 + N_SAMPLES].astype(float)
    for v in VARIANTS:
        s = residual_stats(hdf, variant_output(w, v))
        out.update({f"{v}_max_abs": s["max_abs"], f"{v}_rms": s["rms"], f"{v}_nonzero": s["n_nonzero"]})
    return out


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    import h5py

    from quakenode.manifest import DatasetRecord, RunManifest, results_sha256

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default="data/instance_sample")
    ap.add_argument("--raw-dir", default="data/raw/detrend_check")
    ap.add_argument("--out-dir", default="data/instance_sample/detrend_check")
    args = ap.parse_args()
    root, raw_dir, out_dir = Path(args.data_dir), Path(args.raw_dir), Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # The pre-registration must be committed and unchanged.
    if git("status", "--porcelain", "--", PREREG):
        raise SystemExit(f"{PREREG} is modified or uncommitted; refusing to run")
    prereg_commit = git("log", "-n1", "--format=%H", "--", PREREG)
    if not prereg_commit:
        raise SystemExit(f"{PREREG} has no commit; refusing to run")

    csv_path = root / "metadata/metadata_Instance_events_10k.csv"
    hdf_path = root / "data/Instance_events_counts_10k.hdf5"
    with open(csv_path, newline="") as f:
        meta = {r["trace_name"]: r for r in csv.DictReader(f)}
    sample = draw_sample(sorted(meta), FAMILIES, EXCLUDED_CANDIDATES, SEED, N_PER_FAMILY)
    sample_names = [n for fam in FAMILIES for n in sample[fam]]
    sample_hash = hashlib.sha256("\n".join(sample_names).encode()).hexdigest()

    rows, log = [], []
    with h5py.File(hdf_path, "r") as h5:
        assert h5["data_format/component_order"][()] == b"ENZ"
        import obspy

        for i, name in enumerate(sample_names, 1):
            row = meta[name]
            blob = fetch(name, obspy.UTCDateTime(row["trace_start_time"]), raw_dir, log)
            rows.append(evaluate_trace(name, row, h5["data"][name][Z_INDEX].astype(np.int64), blob))
            print(f"[{i}/{len(sample_names)}] {name}: {rows[-1]['status']} {rows[-1]['reason']}", flush=True)

    # Per-trace CSV and request log.
    cols = ["trace_name", "family", "status", "reason", "raw_rate_hz", "n_traces_in_response", "raw_npts", "raw_dtype",
            "k0", "sub_sample_offset_s", "best_lag", "ncc_at_best_lag"]  # fmt: skip
    cols += [f"{v}_{m}" for v in VARIANTS for m in ("max_abs", "rms", "nonzero")]
    with open(out_dir / "per_trace.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    (out_dir / "requests.jsonl").write_text("\n".join(json.dumps(e, sort_keys=True) for e in log) + "\n")

    comparable = [r for r in rows if r["status"] == "comparable"]
    excl = Counter(r["reason"] for r in rows if r["status"] == "excluded")
    lag_nonzero = sum(1 for r in comparable if r.get("best_lag") not in (0, None))
    summary = {
        "preregistration_commit": prereg_commit,
        "seed": SEED,
        "sample_names_sha256": sample_hash,
        "sample_names": sample_names,
        "n_sampled": len(rows),
        "exclusions": {k: excl.get(k, 0) for k in EXCLUSION_ORDER},
        "excluded_traces": {k: [r["trace_name"] for r in rows if r["reason"] == k] for k in EXCLUSION_ORDER},
        "comparable": len(comparable),
        "comparable_by_family": {fam: sum(r["family"] == fam for r in comparable) for fam in FAMILIES},
        "resampled_traces_not_compared": [
            {"trace": r["trace_name"], "raw_rate_hz": r.get("raw_rate_hz")}
            for r in rows
            if r["reason"] == "native_rate_not_100hz"
        ],
        "lag": {
            "n_best_lag_nonzero": lag_nonzero,
            "fraction": (lag_nonzero / len(comparable) if comparable else None),
            "finding_triggered": bool(comparable and lag_nonzero / len(comparable) > LAG_FINDING_FRACTION),
        },
        "variants": {
            "pooled": {v: summarize_variant(comparable, v) for v in VARIANTS},
            **{
                fam: {v: summarize_variant([r for r in comparable if r["family"] == fam], v) for v in VARIANTS}
                for fam in FAMILIES
            },
        },
    }
    summary["verdict"] = verdict(summary["variants"]["pooled"])
    summary["results_sha256"] = results_sha256(summary)
    archive_url = "https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2"
    license_note = "CC BY 4.0 per INGV INSTANCE page"
    manifest = RunManifest.create(
        config={
            "preregistration": PREREG,
            "preregistration_commit": prereg_commit,
            "seed": SEED,
            "n_per_family": N_PER_FAMILY,
            "variants": list(VARIANTS),
            "sample_names_sha256": sample_hash,
        },
        seeds=[SEED],
        metric_definition_version="detrend_check_v1",
        repo_dir=Path.cwd(),
        datasets=[
            DatasetRecord(
                id="INSTANCE sample v3 events metadata CSV",
                source_url=archive_url,
                doi="10.13127/instance",
                license_note=license_note,
                sha256=sha256_file(csv_path),
            ),
            DatasetRecord(
                id="INSTANCE sample v3 events counts HDF5",
                source_url=archive_url,
                doi="10.13127/instance",
                license_note=license_note,
                sha256=sha256_file(hdf_path),
            ),
            DatasetRecord(
                id="INGV FDSN dataselect miniSEED (IV; cached under data/raw/detrend_check)",
                source_url=FDSN,
                license_note="IV restrictedStatus=open per INGV station service; EIDA Italy policy: CC BY 4.0 mostly",
                retrieval_date=time.strftime("%Y-%m-%d", time.gmtime()),
            ),
        ],
        output_paths=[str(out_dir / name) for name in ("per_trace.csv", "summary.json", "requests.jsonl")],
        exclusions=[f"{k}: {v}" for k, v in excl.items()],
    )
    (out_dir / "summary.json").write_text(
        json.dumps({"summary": summary, "manifest": manifest.to_dict()}, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {"comparable": len(comparable), "exclusions": summary["exclusions"], "verdict": summary["verdict"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
