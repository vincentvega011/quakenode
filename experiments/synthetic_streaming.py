"""Synthetic streaming experiment: the causal arm pushed through packet delivery (software test).

Same four synthetic signal cases and 12 seeds as synthetic_causality.py, but the causal one-pole +
STA/LTA path runs through ReplayEngine -> Receiver -> StreamingPipeline at several packet sizes.
Stress scenarios (one dropped packet, one fixed delay) are software stress tests, NOT network
models. "Emission latency" is synthetic detector delay, NOT warning time. Not seismic validation.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experiments.synthetic_causality import (  # noqa: E402
    CASES,
    CAUSAL_CUTOFF_HZ,
    DETECTOR_THRESHOLD,
    FS_HZ,
    HORIZON_S,
    LTA_SAMPLES,
    P_INDEX,
    P_TIME_S,
    SEEDS,
    STA_SAMPLES,
    causal_baseline,
    fixed_sta_lta_first_trigger,
    generate_signal,
)

from quakenode.manifest import DatasetRecord, RunManifest, results_sha256  # noqa: E402
from quakenode.manifest import provenance as _provenance  # noqa: E402
from quakenode.preprocessing import one_pole_alpha  # noqa: E402
from quakenode.replay import ReplayEngine, Trace, with_fixed_delay  # noqa: E402
from quakenode.streaming import StreamingPipeline  # noqa: E402

PACKET_SIZES = (1, 10, 100)
DROP_NEAR_INDEX = 500  # the packet containing this sample (5 s, before P at 8 s) is dropped
FIXED_DELAY_S = 0.5
WARMUP_SAMPLES = 0  # explicit; 0 keeps the first-trigger semantics identical to the batch path
METRIC_DEFINITION_VERSION = "synthetic_streaming_v1"
SCENARIOS = ("nominal", "dropped_packet_before_p", "fixed_delay")


def _packets(case, seed: int, size: int, scenario: str):
    trace = Trace("SYN", "HHZ", FS_HZ, tuple(generate_signal(case, seed)))
    packets = ReplayEngine.packetize(trace, size)
    if scenario == "dropped_packet_before_p":
        packets = [p for p in packets if not p.first_sample_index <= DROP_NEAR_INDEX < p.first_sample_index + size]
    elif scenario == "fixed_delay":
        packets = with_fixed_delay(packets, FIXED_DELAY_S)
    return packets


def run_one(case, seed: int, size: int, scenario: str) -> dict:
    engine = ReplayEngine()
    engine.schedule(_packets(case, seed, size, scenario))
    pipe = StreamingPipeline(
        one_pole_alpha(CAUSAL_CUTOFF_HZ, FS_HZ), WARMUP_SAMPLES, STA_SAMPLES, LTA_SAMPLES, DETECTOR_THRESHOLD, 0.0
    ).run(engine)
    batch_idx = fixed_sta_lta_first_trigger(causal_baseline(generate_signal(case, seed))[0])
    det = pipe.detections[0] if pipe.detections else None
    idx = det.trigger_sample_index if det else None
    in_horizon = det is not None and P_INDEX <= idx <= P_INDEX + int(HORIZON_S * FS_HZ)
    return {
        "seed": seed,
        "first_trigger_index": idx,
        "batch_first_trigger_index": batch_idx,
        "agrees_with_batch": idx == batch_idx,
        "hit_within_horizon": bool(case.has_event and in_horizon),
        "false_trigger": bool(not case.has_event and det is not None),
        "gap_events": len(pipe.gap_events),
        "trigger_sample_s_from_p": None if det is None else round(det.trigger_sample_time_s - P_TIME_S, 6),
        "emission_latency_s_from_p": None if det is None else round(det.emission_time_s - P_TIME_S, 6),
    }


def _stats(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "median": None, "min": None, "max": None}
    return {
        "mean": round(statistics.mean(values), 6),
        "median": round(statistics.median(values), 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


def run_experiment() -> dict:
    config = {
        "fs_hz": FS_HZ, "p_time_s": P_TIME_S, "horizon_s": HORIZON_S, "seeds": list(SEEDS),
        "sta_samples": STA_SAMPLES, "lta_preceding_samples": LTA_SAMPLES,
        "detector_ratio_threshold": DETECTOR_THRESHOLD, "causal_fc_hz": CAUSAL_CUTOFF_HZ,
        "warmup_samples": WARMUP_SAMPLES, "packet_sizes": list(PACKET_SIZES),
        "scenarios": list(SCENARIOS), "drop_near_index": DROP_NEAR_INDEX, "fixed_delay_s": FIXED_DELAY_S,
        "cases": [c.name for c in CASES],
    }  # fmt: skip
    results: dict = {}
    for scenario in SCENARIOS:
        for case in CASES:
            for size in PACKET_SIZES:
                rows = [run_one(case, seed, size, scenario) for seed in SEEDS]
                detected = [r for r in rows if r["first_trigger_index"] is not None]
                results[f"{scenario}/{case.name}/packet_{size}"] = {
                    "scenario": scenario, "case": case.name, "packet_size": size, "n_seeds": len(rows),
                    "hits_within_horizon": sum(r["hit_within_horizon"] for r in rows),
                    "misses_within_horizon": sum(1 for r in rows if case.has_event and not r["hit_within_horizon"]),
                    "event_denominator": len(rows) if case.has_event else 0,
                    "false_triggers": sum(r["false_trigger"] for r in rows),
                    "negative_denominator": 0 if case.has_event else len(rows),
                    "first_trigger_agrees_with_batch": sum(r["agrees_with_batch"] for r in rows),
                    "emission_latency_s_from_p_detected_only": _stats(
                        [r["emission_latency_s_from_p"] for r in detected if r["hit_within_horizon"]]
                    ),
                    "trigger_sample_s_from_p_detected_only": _stats(
                        [r["trigger_sample_s_from_p"] for r in detected if r["hit_within_horizon"]]
                    ),
                    "per_seed": rows,
                }  # fmt: skip
    return {"config": config, "results": results}


def with_manifest(result: dict) -> dict:
    manifest = RunManifest.create(
        config=result["config"],
        seeds=list(SEEDS),
        metric_definition_version=METRIC_DEFINITION_VERSION,
        repo_dir=Path(__file__).resolve().parent,
        datasets=[DatasetRecord(id="synthetic:generate_signal", license_note="generated in-process; no external data")],
        warnings=[
            "synthetic signals only; supports software-invariant claims, not seismic performance",
            "dropped-packet and fixed-delay scenarios are software stress tests, not network models",
            "emission latency is synthetic detector delay, not warning time",
        ],
    )
    return {
        **result,
        "provenance": _provenance(result["config"], __file__),
        "manifest": manifest.to_dict(),
        "results_sha256": results_sha256(result),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit full machine-readable JSON")
    args = parser.parse_args()
    result = run_experiment()
    if args.json:
        print(json.dumps(with_manifest(result), indent=2, sort_keys=True))
        return
    print("Synthetic streaming experiment (software test; not seismic validation, not warning time)")
    print(f"Seeds: {len(SEEDS)}; fs={FS_HZ:g} Hz; P={P_TIME_S:g} s; horizon={HORIZON_S:g} s; warm-up={WARMUP_SAMPLES}")
    print(f"results_sha256: {results_sha256(result)}")
    print("emission latency = emission_time_s - P sample time (synthetic detector delay), detected-in-horizon traces")
    header = (
        f"{'case':21} {'pkt':>4} {'hit':>5} {'miss':>5} {'false':>5} {'=batch':>7} {'latency mean/min/max (s)':>28}"
    )
    for scenario in SCENARIOS:
        print(f"\n[{scenario}]" + ("  (software stress test)" if scenario != "nominal" else ""))
        print(header)
        for r in (v for v in result["results"].values() if v["scenario"] == scenario):
            lat = r["emission_latency_s_from_p_detected_only"]
            lat_s = "-" if lat["mean"] is None else f"{lat['mean']:.3f}/{lat['min']:.3f}/{lat['max']:.3f}"
            print(
                f"{r['case']:21} {r['packet_size']:>4} {r['hits_within_horizon']:>2}/{r['event_denominator']:<2} "
                f"{r['misses_within_horizon']:>2}/{r['event_denominator']:<2} "
                f"{r['false_triggers']:>2}/{r['negative_denominator']:<2} "
                f"{r['first_trigger_agrees_with_batch']:>4}/{r['n_seeds']:<2} {lat_s:>28}"
            )


if __name__ == "__main__":
    main()
