"""Deterministic synthetic preprocessing causality experiment (stdlib only).

This is a controlled software experiment, not a seismic detector or EEW system.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from quakenode.detectors import rms_sta_lta_first_trigger
from quakenode.manifest import DatasetRecord, RunManifest, results_sha256
from quakenode.manifest import provenance as _provenance
from quakenode.preprocessing import (
    causal_one_pole_highpass,
    chunked_one_pole_highpass,
    linear_detrend,
    mean_remove,
    one_pole_alpha,
)

FS_HZ = 100.0
DURATION_S = 20.0
P_TIME_S = 8.0
P_INDEX = int(FS_HZ * P_TIME_S)
HORIZON_S = 2.0
STA_SAMPLES = 10
LTA_SAMPLES = 100
DETECTOR_THRESHOLD = 3.0
CAUSAL_CUTOFF_HZ = 0.5
PREFIX_CUTOFF_INDEX = P_INDEX + 150
PERTURB_OFFSET = 2.0
PERTURB_RAMP_PER_S = 0.25
SEEDS = tuple(range(202601, 202613))
METRIC_DEFINITION_VERSION = "synthetic_causality_v1"  # label for the metrics computed in this script


@dataclass(frozen=True)
class SignalCase:
    name: str
    event_amplitude: float
    baseline: float
    trend_per_s: float
    noise_sigma: float
    has_event: bool


CASES = (
    SignalCase("trended_event", 1.0, 0.8, 0.04, 0.08, True),
    SignalCase("flat_event", 1.0, 0.0, 0.0, 0.08, True),
    SignalCase("quiet_noise_control", 0.0, 0.0, 0.0, 0.08, False),
    SignalCase("trend_only_control", 0.0, 0.8, 0.04, 0.08, False),
)


def generate_signal(case: SignalCase, seed: int) -> list[float]:
    """Generate seeded Gaussian noise, baseline+linear trend, and a P-like pulse."""
    rng = random.Random(seed)
    n = int(FS_HZ * DURATION_S)
    noise = [rng.gauss(0.0, case.noise_sigma) for _ in range(n)]
    out = []
    for i, eps in enumerate(noise):
        t = i / FS_HZ
        value = case.baseline + case.trend_per_s * t + eps
        if case.has_event and i >= P_INDEX:
            tau = (i - P_INDEX) / FS_HZ
            # 6 Hz damped onset, with a smooth 0.8 s envelope.
            if tau < 0.8:
                value += case.event_amplitude * math.exp(-2.2 * tau) * math.sin(2 * math.pi * 6.0 * tau)
        out.append(value)
    return out


def future_perturbation(samples: Sequence[float], cutoff: int) -> list[float]:
    """Leave samples[:cutoff] bit-identical; add a fixed offset and ramp after it."""
    changed = list(samples)
    for i in range(cutoff, len(changed)):
        dt = (i - cutoff) / FS_HZ
        changed[i] += PERTURB_OFFSET + PERTURB_RAMP_PER_S * dt
    return changed


# Experiment-bound wrappers: names and signatures are kept from the original script.
offline_mean_remove = mean_remove
offline_linear_detrend = linear_detrend


def causal_baseline(
    samples: Iterable[float], state: float | None = None, alpha: float | None = None
) -> tuple[list[float], float | None]:
    """Causal one-pole baseline removal; alpha defaults to exp(-2*pi*fc/fs) for the study fc and fs."""
    if alpha is None:
        alpha = one_pole_alpha(CAUSAL_CUTOFF_HZ, FS_HZ)
    return causal_one_pole_highpass(samples, alpha, state)


def causal_baseline_chunked(samples: Sequence[float], chunks: Sequence[int]) -> list[float]:
    return chunked_one_pole_highpass(samples, chunks, one_pole_alpha(CAUSAL_CUTOFF_HZ, FS_HZ))


def fixed_sta_lta_first_trigger(samples: Sequence[float], stop_index: int | None = None) -> int | None:
    """First causal RMS STA / preceding, non-overlapping RMS LTA threshold crossing (study parameters)."""
    return rms_sta_lta_first_trigger(samples, STA_SAMPLES, LTA_SAMPLES, DETECTOR_THRESHOLD, stop_index)


def _first_horizon_trigger(samples: Sequence[float], has_event: bool) -> int | None:
    idx = fixed_sta_lta_first_trigger(samples)
    if idx is None:
        return None
    if not has_event or P_INDEX <= idx <= P_INDEX + int(HORIZON_S * FS_HZ):
        return idx
    return None


def _first_prefix_trigger(samples: Sequence[float]) -> int | None:
    return fixed_sta_lta_first_trigger(samples, stop_index=PREFIX_CUTOFF_INDEX - 1)


def _rms(values: Sequence[float]) -> float:
    return math.sqrt(sum(x * x for x in values) / len(values)) if values else 0.0


def provenance(config: dict) -> dict:
    return _provenance(config, __file__)


def run_experiment() -> dict:
    arms = ("raw", "mean", "linear_detrend", "causal_one_pole")
    per_case = {}
    all_decision_changes = {arm: 0 for arm in arms}
    all_prefix_max = {arm: [] for arm in arms}
    for case in CASES:
        metrics = {
            arm: {
                "decisions": [],
                "trigger_shift_s": [],
                "misses": 0,
                "future_prefix_max_abs": [],
                "future_prefix_rms": [],
            }
            for arm in arms
        }
        seed_rows = []
        for seed in SEEDS:
            raw = generate_signal(case, seed)
            perturbed = future_perturbation(raw, PREFIX_CUTOFF_INDEX)
            processed = {
                "raw": raw,
                "mean": offline_mean_remove(raw),
                "linear_detrend": offline_linear_detrend(raw),
                "causal_one_pole": causal_baseline(raw)[0],
            }
            processed_perturbed = {
                "raw": perturbed,
                "mean": offline_mean_remove(perturbed),
                "linear_detrend": offline_linear_detrend(perturbed),
                "causal_one_pole": causal_baseline(perturbed)[0],
            }
            row = {"seed": seed, "arms": {}}
            for arm in arms:
                base_idx = _first_horizon_trigger(processed[arm], case.has_event)
                prefix_base_idx = _first_prefix_trigger(processed[arm])
                prefix_pert_idx = _first_prefix_trigger(processed_perturbed[arm])
                changed = prefix_base_idx != prefix_pert_idx
                metrics[arm]["decisions"].append(changed)
                all_decision_changes[arm] += int(changed)
                prefix_diff = [
                    abs(a - b)
                    for a, b in zip(
                        processed[arm][:PREFIX_CUTOFF_INDEX], processed_perturbed[arm][:PREFIX_CUTOFF_INDEX]
                    )
                ]
                max_diff = max(prefix_diff, default=0.0)
                rms_diff = _rms(prefix_diff)
                metrics[arm]["future_prefix_max_abs"].append(max_diff)
                metrics[arm]["future_prefix_rms"].append(rms_diff)
                all_prefix_max[arm].append(max_diff)
                row["arms"][arm] = {
                    "unperturbed_first_trigger_index": fixed_sta_lta_first_trigger(processed[arm]),
                    "unperturbed_trigger_in_event_horizon_index": base_idx,
                    "prefix_first_trigger_original_index": prefix_base_idx,
                    "prefix_first_trigger_perturbed_index": prefix_pert_idx,
                    "prefix_decision_changed": changed,
                    "prefix_max_abs_difference": max_diff,
                    "prefix_rms_difference": rms_diff,
                    "trigger_shift_s_from_p": ((base_idx - P_INDEX) / FS_HZ if base_idx is not None else None),
                }
                if case.has_event:
                    if base_idx is None:
                        metrics[arm]["misses"] += 1
                    else:
                        metrics[arm]["trigger_shift_s"].append((base_idx - P_INDEX) / FS_HZ)
                else:
                    metrics[arm].setdefault("false_triggers", 0)
                    metrics[arm]["false_triggers"] += int(fixed_sta_lta_first_trigger(processed[arm]) is not None)
            seed_rows.append(row)
        case_result = {}
        for arm in arms:
            vals = metrics[arm]["trigger_shift_s"]
            case_result[arm] = {
                "decision_changes": sum(metrics[arm]["decisions"]),
                "decision_change_denominator": len(metrics[arm]["decisions"]),
                "misses_within_2s": metrics[arm]["misses"],
                "event_denominator": len(SEEDS) if case.has_event else 0,
                "false_triggers_over_20s": metrics[arm].get("false_triggers", 0),
                "negative_trace_denominator": len(SEEDS) if not case.has_event else 0,
                "trigger_shift_mean_s_detected_only": round(statistics.mean(vals), 6) if vals else None,
                "trigger_shift_median_s_detected_only": round(statistics.median(vals), 6) if vals else None,
                "trigger_shift_min_s_detected_only": round(min(vals), 6) if vals else None,
                "trigger_shift_max_s_detected_only": round(max(vals), 6) if vals else None,
                "detected_denominator": len(vals),
                "future_prefix_max_abs_mean": round(statistics.mean(metrics[arm]["future_prefix_max_abs"]), 12),
                "future_prefix_max_abs_max": round(max(metrics[arm]["future_prefix_max_abs"], default=0.0), 12),
                "future_prefix_rms_mean": round(statistics.mean(metrics[arm]["future_prefix_rms"]), 12),
            }
        per_case[case.name] = {"aggregate": case_result, "per_seed": seed_rows}
    config = {
        "fs_hz": FS_HZ,
        "duration_s": DURATION_S,
        "p_time_s": P_TIME_S,
        "horizon_s": HORIZON_S,
        "seeds": list(SEEDS),
        "sta_samples": STA_SAMPLES,
        "lta_preceding_samples": LTA_SAMPLES,
        "detector_ratio_threshold": DETECTOR_THRESHOLD,
        "causal_fc_hz": CAUSAL_CUTOFF_HZ,
        "causal_alpha": round(math.exp(-2 * math.pi * CAUSAL_CUTOFF_HZ / FS_HZ), 12),
        "prefix_cutoff_index": PREFIX_CUTOFF_INDEX,
        "future_perturbation": {"offset": PERTURB_OFFSET, "ramp_per_s": PERTURB_RAMP_PER_S},
        "cases": [asdict(c) for c in CASES],
    }
    protocol = {
        **config,
        "arm_decision_changes_total": all_decision_changes,
        "arm_prefix_diff_mean_over_cases_seeds": {arm: round(statistics.mean(all_prefix_max[arm]), 12) for arm in arms},
    }
    return {
        "protocol": protocol,
        "provenance": provenance(config),
        "results_by_case": per_case,
    }


def build_manifest(result: dict) -> RunManifest:
    """Run manifest for the synthetic experiment (synthetic data only; no external datasets)."""
    protocol = result["protocol"]
    return RunManifest.create(
        config={k: v for k, v in protocol.items() if not k.startswith("arm_")},
        seeds=list(SEEDS),
        metric_definition_version=METRIC_DEFINITION_VERSION,
        repo_dir=Path(__file__).resolve().parent,
        datasets=[DatasetRecord(id="synthetic:generate_signal", license_note="generated in-process; no external data")],
        warnings=["synthetic signals only; supports software-invariant claims, not seismic performance"],
    )


def with_manifest(result: dict) -> dict:
    """Add the run manifest and results_sha256 (hash of everything except manifest and provenance)."""
    return {**result, "manifest": build_manifest(result).to_dict(), "results_sha256": results_sha256(result)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit full machine-readable JSON")
    args = parser.parse_args()
    result = run_experiment()
    if args.json:
        result = with_manifest(result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    print("Synthetic preprocessing causality experiment (not real seismic validation)")
    print(f"Seeds: {len(SEEDS)}; fs={FS_HZ:g} Hz; P={P_TIME_S:g} s; horizon={HORIZON_S:g} s")
    print(f"Fixed detector: {STA_SAMPLES}-sample STA / preceding {LTA_SAMPLES}-sample LTA >= {DETECTOR_THRESHOLD:g}")
    print(
        "case                 arm              prefix decision changes/12  misses/12  false triggers/12  "
        "mean P-relative trigger (s)  prefix max abs mean"
    )
    for case, case_data in result["results_by_case"].items():
        for arm, m in case_data["aggregate"].items():
            mean_shift = m["trigger_shift_mean_s_detected_only"]
            print(
                f"{case:21} {arm:16} {m['decision_changes']:2}/{m['decision_change_denominator']:<2}"
                f"                      {m['misses_within_2s']:2}/{m['event_denominator']:<2}"
                f"       {m['false_triggers_over_20s']:2}/{m['negative_trace_denominator']:<2}"
                f"         {mean_shift!s:>10}                 {m['future_prefix_max_abs_mean']:.6g}"
            )


if __name__ == "__main__":
    main()
