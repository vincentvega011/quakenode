"""Metrics for a multi-station streaming experiment. Definitions: docs/metrics.md.

All times are seconds. Truth comes from the SYNTHETIC scenario: `p_time_s` is the true P arrival on the SAMPLE clock.
Latencies on the sample clock and on the emission clock are reported separately and never merged.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from quakenode.fusion import Candidate
from quakenode.replay import Detection


@dataclass(frozen=True)
class MetricsConfig:
    detection_pre_margin_s: float = 1.0  # a detection this much before P still counts as a hit
    detection_post_horizon_s: float = 10.0  # ... and up to this long after P
    event_reference: str = "kth_p"  # 'kth_p': k-th smallest P time; 'earliest_p': the earliest P time


@dataclass(frozen=True)
class StationTruth:
    station_id: str
    p_time_s: float | None  # None when the scenario has no event
    n_samples_total: int
    warmup_s: float  # detector warm-up; pre-event scoring starts after it
    duration_s: float = 0.0  # trace duration (used to score a noise-only scenario)
    p_uncertainty_s: float | None = None  # stated uncertainty of the reference P time (real events); reported only
    start_time_s: float = 0.0  # timeline time of this station's first sample (real events start at different times)


def _first_hit(dets: Sequence[Detection], truth: StationTruth, cfg: MetricsConfig) -> Detection | None:
    if truth.p_time_s is None:
        return None
    lo, hi = truth.p_time_s - cfg.detection_pre_margin_s, truth.p_time_s + cfg.detection_post_horizon_s
    hits = [d for d in dets if lo <= d.trigger_sample_time_s <= hi]
    return min(hits, key=lambda d: (d.trigger_sample_time_s, d.trigger_sample_index)) if hits else None


def station_metrics(
    truth: StationTruth,
    detections: Sequence[Detection],
    samples_processed: int,
    cfg: MetricsConfig,
    filled_samples: int = 0,
) -> dict:
    """Per-station, per-seed metrics.

    Detections triggered on INSERTED (zero-filled) samples are not evidence: they are left out of hits and of the
    false-trigger count and reported separately as detections_on_filled_samples. Completeness counts recorded
    samples only; filled_samples are reported separately.
    """
    all_mine = [d for d in detections if d.station_id == truth.station_id]
    mine = [d for d in all_mine if not d.on_filled_samples]
    hit = _first_hit(mine, truth, cfg)
    out: dict = {
        "station_id": truth.station_id,
        "detected": bool(hit) if truth.p_time_s is not None else None,
        "sample_latency_s": None,
        "emission_latency_s": None,
        "reported_timestamp_error_s": None,
        "false_triggers": 0,
        "scored_pre_event_s": 0.0,
        "p_uncertainty_s": truth.p_uncertainty_s,
        "filled_samples": filled_samples,
        "detections_on_filled_samples": len(all_mine) - len(mine),
        "completeness": min(1.0, samples_processed / truth.n_samples_total) if truth.n_samples_total else None,
    }
    if truth.p_time_s is None:
        out["false_triggers"] = len(mine)  # no event anywhere: every detection is false
        out["scored_pre_event_s"] = max(0.0, truth.duration_s - truth.warmup_s)
        return out
    out["false_triggers"] = sum(
        1 for d in mine if d.trigger_sample_time_s < truth.p_time_s - cfg.detection_pre_margin_s
    )
    out["scored_pre_event_s"] = max(
        0.0, truth.p_time_s - truth.start_time_s - cfg.detection_pre_margin_s - truth.warmup_s
    )
    if hit is not None:
        out["sample_latency_s"] = hit.trigger_sample_time_s - truth.p_time_s
        out["emission_latency_s"] = hit.emission_time_s - truth.p_time_s
        if hit.reported_trigger_sample_time_s is not None:
            out["reported_timestamp_error_s"] = hit.reported_trigger_sample_time_s - hit.trigger_sample_time_s
    return out


def event_metrics(
    truths: Sequence[StationTruth],
    detections: Sequence[Detection],
    candidates: Sequence[Candidate],
    k: int,
    cfg: MetricsConfig,
) -> dict:
    """Event-level metrics for one seed.

    reference time (cfg.event_reference) = the k-th smallest P time over all stations ('kth_p', the earliest moment
    at which k stations could have had a P arrival; default for synthetic scenarios) or the earliest P time
    ('earliest_p', used for real catalog events); association latency = first TRUE candidate's creation time
    (emission clock) minus that reference. A candidate is TRUE when at least k of its contributing detections are hits.
    """
    p_times = sorted(t.p_time_s for t in truths if t.p_time_s is not None)
    ref_index = 0 if cfg.event_reference == "earliest_p" else k - 1
    out: dict = {
        "n_candidates": len(candidates),
        "true_candidates": 0,
        "false_candidates": 0,
        "event_detected": None,
        "association_latency_s": None,
        "reference_time_s": None,
    }
    if len(p_times) < k:
        out["false_candidates"] = len(candidates)
        return out
    out["reference_time_s"] = p_times[ref_index]
    by_station = {t.station_id: t for t in truths}
    true_cands = []
    for c in candidates:
        n_hit = sum(
            1 for d in c.detections if (h := _first_hit([d], by_station[d.station_id], cfg)) is not None and h is d
        )
        if n_hit >= k:
            true_cands.append(c)
    out["true_candidates"], out["false_candidates"] = len(true_cands), len(candidates) - len(true_cands)
    out["event_detected"] = bool(true_cands)
    if true_cands:
        first = min(true_cands, key=lambda c: c.created_time_s)
        out["association_latency_s"] = first.created_time_s - p_times[ref_index]
    return out


def seed_summary(stations: Sequence[dict], event: dict, gap_events: int = 0, missing_samples: int = 0) -> dict:
    """Seed-level scalars used for aggregation and for paired comparison against a control."""

    def med(key: str) -> float | None:
        vals = [s[key] for s in stations if s[key] is not None]
        return median(vals) if vals else None

    det = [s["detected"] for s in stations if s["detected"] is not None]
    comp = [s["completeness"] for s in stations if s["completeness"] is not None]
    scored = math.fsum(s["scored_pre_event_s"] for s in stations)
    false = sum(s["false_triggers"] for s in stations)
    return {
        "detection_fraction": (sum(det) / len(det)) if det else None,
        "median_sample_latency_s": med("sample_latency_s"),
        "median_emission_latency_s": med("emission_latency_s"),
        "mean_completeness": (math.fsum(comp) / len(comp)) if comp else None,
        "false_triggers": false,
        "false_trigger_rate_per_station_hour": (false / (scored / 3600.0)) if scored > 0 else None,
        "event_detected": (1.0 if event["event_detected"] else 0.0) if event["event_detected"] is not None else None,
        "association_latency_s": event["association_latency_s"],
        "false_candidates": event["false_candidates"],
        "gap_events": gap_events,
        "missing_samples_total": missing_samples,
        "filled_samples_total": sum(s.get("filled_samples", 0) for s in stations),
        "detections_on_filled_samples": sum(s.get("detections_on_filled_samples", 0) for s in stations),
    }


# ---- statistics -------------------------------------------------------------------------------------------------


def quantile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation quantile (the 'type 7' definition). Raises on an empty input."""
    xs = sorted(values)
    if not xs:
        raise ValueError("quantile of an empty sequence")
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def median(values: Sequence[float]) -> float:
    return quantile(values, 0.5)


def distribution(values: Sequence[float | None]) -> dict:
    """Count, defined count, median, quartiles, min, max and mean of the defined values (None = undefined).

    Float sums use math.fsum (exactly rounded): the built-in sum() changed its float rounding in Python 3.12, which
    would make results differ between Python versions.
    """
    xs = [v for v in values if v is not None]
    base: dict = {"n": len(values), "n_defined": len(xs)}
    if not xs:
        return {**base, "median": None, "q1": None, "q3": None, "min": None, "max": None, "mean": None}
    return {
        **base,
        "median": median(xs),
        "q1": quantile(xs, 0.25),
        "q3": quantile(xs, 0.75),
        "min": min(xs),
        "max": max(xs),
        "mean": math.fsum(xs) / len(xs),
    }


def wilson_interval(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci_median(
    values: Sequence[float], seed: int, n_boot: int = 2000, level: float = 0.95
) -> tuple[float, float]:
    """Percentile bootstrap CI of the median over seeds (seeded; resamples seeds with replacement)."""
    rng = random.Random(seed)
    n = len(values)
    meds = sorted(median([values[int(rng.random() * n)] for _ in range(n)]) for _ in range(n_boot))
    lo, hi = (1 - level) / 2, 1 - (1 - level) / 2
    return quantile(meds, lo), quantile(meds, hi)


def paired_difference(
    test: dict[int, float | None], control: dict[int, float | None], bootstrap_seed: int | None = None
) -> dict:
    """Seed-level paired difference test - control over seeds where both are defined.

    Reports the number of seeds, how many differences are positive / negative / zero, the distribution of the
    differences (median, quartiles, min, max) and, if bootstrap_seed is given, a 95% percentile bootstrap CI of the
    median difference. Seeds where either value is undefined are counted in n_undefined and left out.
    """
    seeds = sorted(set(test) & set(control))
    diffs, undefined = [], 0
    for s in seeds:
        a, b = test[s], control[s]
        if a is None or b is None:
            undefined += 1
        else:
            diffs.append(a - b)
    out = {
        "n_seeds": len(seeds),
        "n_paired": len(diffs),
        "n_undefined": undefined,
        "n_positive": sum(d > 0 for d in diffs),
        "n_negative": sum(d < 0 for d in diffs),
        "n_zero": sum(d == 0 for d in diffs),
        "differences": distribution(diffs),
        "bootstrap_ci95_median": None,
    }
    if bootstrap_seed is not None and len(diffs) >= 2:
        out["bootstrap_ci95_median"] = list(bootstrap_ci_median(diffs, bootstrap_seed))
    return out
