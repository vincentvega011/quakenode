"""Run a configured SYNTHETIC multi-station streaming experiment and write its outputs.

Per seed: generate the scenario traces -> packetize -> apply the declared faults in order -> replay through the
engine -> streaming pipeline (detector per station) -> k-of-n fusion -> metrics. Outputs per run directory:
manifest.json, events.jsonl, metrics.json, metrics.csv, report.md and (if matplotlib is installed) plots/*.png.
"""

from __future__ import annotations

import csv
import itertools
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quakenode import __version__
from quakenode.config import ExperimentConfig, parse_config, set_path
from quakenode.evaluation import (
    MetricsConfig,
    StationTruth,
    distribution,
    event_metrics,
    paired_difference,
    seed_summary,
    station_metrics,
    wilson_interval,
)
from quakenode.faults import (
    ClockOffset,
    Duplicate,
    FaultRecord,
    FixedDelay,
    Jitter,
    MissingSamples,
    PacketLoss,
    Reorder,
    Selection,
    StationOutage,
    apply_faults,
)
from quakenode.fusion import FusionConfig, fuse
from quakenode.manifest import DatasetRecord, RunManifest, results_sha256
from quakenode.replay import Detection, ReplayEngine
from quakenode.scenario.loader import ScenarioData, load_scenario, network_spec  # noqa: F401 (re-exported)
from quakenode.streaming import StreamingPipeline, create_detector_factory

BANNER = "QuakeNode is a research testbed, not an operational warning system."
SYNTHETIC_NOTICE = (
    "All data in this run are SYNTHETIC (generated in-process); results support software-invariant claims only."
)
METRIC_VERSION = "quakenode_metrics_v1"
HEADLINE_METRICS = (
    "gap_events",
    "filled_samples_total",
    "detection_fraction",
    "median_sample_latency_s",
    "median_emission_latency_s",
    "mean_completeness",
    "false_triggers",
    "event_detected",
    "association_latency_s",
)


def build_fault(f: dict[str, Any]) -> Any:
    """Config mapping (already validated) -> fault object."""
    targets = f.get("targets", "all")
    sel = Selection("all" if targets == "all" else tuple(targets), float(f.get("start_s", 0.0)), f.get("end_s"))
    t = f["type"]
    if t == "fixed_delay":
        return FixedDelay(float(f["delay_s"]), sel)
    if t == "jitter":
        return Jitter(
            f["distribution"], float(f.get("low_s", 0.0)), float(f.get("high_s", 0.0)), float(f.get("mean_s", 0.0)), sel
        )
    if t == "packet_loss":
        return PacketLoss(
            f.get("model", "bernoulli"),
            float(f.get("p", 0.0)),
            float(f.get("p_gb", 0.0)),
            float(f.get("p_bg", 0.0)),
            float(f.get("loss_good", 0.0)),
            float(f.get("loss_bad", 1.0)),
            sel,
        )
    if t == "duplicate":
        return Duplicate(float(f["p"]), float(f.get("extra_delay_s", 0.0)), sel)
    if t == "reorder":
        return Reorder(float(f["p"]), float(f["hold_s"]), sel)
    if t == "station_outage":
        return StationOutage(sel)
    if t == "clock_offset":
        return ClockOffset(float(f["offset_s"]), sel)
    if t == "missing_samples":
        return MissingSamples(float(f["p"]), int(f["n_samples"]), sel)
    raise ValueError(f"unknown fault type {t!r}")  # pragma: no cover (validated earlier)


@dataclass
class SeedResult:
    seed: int
    events: list[dict[str, Any]] = field(default_factory=list)
    stations: list[dict[str, Any]] = field(default_factory=list)
    event: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    fault_records: list[FaultRecord] = field(default_factory=list)
    detections: list[Detection] = field(default_factory=list)


def _det_event(seed: int, d: Detection) -> dict[str, Any]:
    return {
        "seed": seed,
        "kind": "detection",
        "station_id": d.station_id,
        "trigger_sample_index": d.trigger_sample_index,
        "trigger_sample_time_s": d.trigger_sample_time_s,
        "trigger_ready_time_s": d.trigger_ready_time_s,
        "arrival_time_s": d.arrival_time_s,
        "emission_time_s": d.emission_time_s,
        "reported_trigger_sample_time_s": d.reported_trigger_sample_time_s,
        "on_filled_samples": d.on_filled_samples,
        "detector": d.detector_name,
        "ratio": d.ratio,
        "threshold": d.threshold,
    }


def run_seed(cfg: ExperimentConfig, seed: int, scen: ScenarioData | None = None) -> SeedResult:
    scen = scen if scen is not None else load_scenario(cfg)
    res = SeedResult(seed)
    faulted, records = apply_faults(scen.packets_fn(seed), [build_fault(f) for f in cfg.faults], seed)
    res.fault_records = records
    for i, r in enumerate(records):
        res.events.append({"seed": seed, "kind": "fault", "index": i, **r.to_dict()})

    pc = cfg.pipeline
    factory = create_detector_factory(cfg.detector.name, cfg.detector.params, pc.processing_delay_s)
    engine = ReplayEngine()
    engine.schedule(faulted, allow_duplicates=True)
    pipe = StreamingPipeline(
        detector_factory=factory,
        order_policy=pc.order_policy,
        max_wait_s=pc.max_wait_s,
        gap_policy=pc.gap_policy,
        processing_delay_s=pc.processing_delay_s,
    )
    pipe.run(engine)
    res.detections = list(pipe.detections)
    res.events += [_det_event(seed, d) for d in pipe.detections]
    for g in pipe.gap_events:
        res.events.append(
            {
                "seed": seed,
                "kind": "gap",
                "station_id": g.station_id,
                "expected_index": g.expected_index,
                "received_index": g.received_index,
                "arrival_time_s": g.arrival_time_s,
                "declared_time_s": g.declared_time_s,
                "policy": g.policy,
                "missing_samples": g.missing_samples,
                "filled_samples": g.filled_samples,
                "state_kept": g.state_kept,
            }
        )
    for x in pipe.dropped:
        res.events.append(
            {
                "seed": seed,
                "kind": "dropped_packet",
                "station_id": x.station_id,
                "sequence_number": x.sequence_number,
                "arrival_time_s": x.arrival_time_s,
                "reason": x.reason,
            }
        )

    fz = cfg.fusion
    fusion_input = pipe.detections
    if fz.exclude_filled_detections:
        fusion_input = [d for d in pipe.detections if not d.on_filled_samples]
        for d in pipe.detections:
            if d.on_filled_samples:
                excluded = {"seed": seed, "kind": "fusion", "decision": "excluded_filled_detection"}
                excluded |= {"time_s": d.emission_time_s, "station_id": d.station_id, "candidate_id": None}
                excluded["detail"] = "triggered on zero-filled samples"
                res.events.append(excluded)
    fused = fuse(fusion_input, FusionConfig(fz.k, fz.window_s, fz.update_window_s, fz.window_clock))
    res.events += [{"seed": seed, "kind": "fusion", **d.to_dict()} for d in fused.decisions]
    for c in fused.candidates:
        res.events.append(
            {
                "seed": seed,
                "kind": "candidate",
                "id": c.id,
                "created_time_s": c.created_time_s,
                "stations": list(c.station_ids),
                "status": c.status,
                "update_times_s": c.update_times_s,
                "closed_time_s": c.closed_time_s,
            }
        )

    mc = MetricsConfig(
        cfg.metrics.detection_pre_margin_s,
        cfg.metrics.detection_post_horizon_s,
        cfg.metrics.event_reference or scen.default_event_reference,
    )
    truths = []
    for st in scen.stations:
        warm = factory(st["station_id"], scen.channel_id, scen.sample_rate_hz).warmup_s
        truths.append(
            StationTruth(
                st["station_id"], st["p_time_s"], st["n_samples_total"], warm, st["duration_s"],
                st["p_uncertainty_s"], st["start_time_s"],
            )
        )  # fmt: skip
    res.stations = []
    for t in truths:
        key = (t.station_id, scen.channel_id)
        seen = key in pipe._streams
        res.stations.append(
            station_metrics(
                t, pipe.detections, pipe.samples_processed(*key) if seen else 0, mc,
                pipe.samples_filled(*key) if seen else 0,
            )
        )  # fmt: skip
    res.event = event_metrics(truths, fusion_input, fused.candidates, fz.k, mc)
    res.summary = seed_summary(
        res.stations, res.event, len(pipe.gap_events), sum(g.missing_samples or 0 for g in pipe.gap_events)
    )
    res.events.append({"seed": seed, "kind": "seed_summary", **res.summary})
    return res


def aggregate(results: list[SeedResult]) -> dict[str, Any]:
    agg = {m: distribution([r.summary[m] for r in results]) for m in HEADLINE_METRICS}
    detected = [r.summary["event_detected"] for r in results if r.summary["event_detected"] is not None]
    k, n = int(sum(detected)), len(detected)
    lo, hi = wilson_interval(k, n)
    stations: dict[str, dict] = {}
    for sid in {s["station_id"] for r in results for s in r.stations}:
        rows = [s for r in results for s in r.stations if s["station_id"] == sid]
        det = [s["detected"] for s in rows if s["detected"] is not None]
        stations[sid] = {
            "detection_rate": (sum(det) / len(det)) if det else None,
            "p_uncertainty_s": rows[0]["p_uncertainty_s"],
            "sample_latency_s": distribution([s["sample_latency_s"] for s in rows]),
            "emission_latency_s": distribution([s["emission_latency_s"] for s in rows]),
            "completeness": distribution([s["completeness"] for s in rows]),
            "filled_samples": distribution([s["filled_samples"] for s in rows]),
            "false_triggers_total": sum(s["false_triggers"] for s in rows),
            "detections_on_filled_samples_total": sum(s["detections_on_filled_samples"] for s in rows),
        }
    return {
        "summary_over_seeds": agg,
        "event_detection_rate": {"k": k, "n": n, "rate": (k / n) if n else None, "wilson95": [lo, hi]},
        "per_station": dict(sorted(stations.items())),
    }


def _unique_dir(parent: Path, stem: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = parent / f"{stem}-{stamp}-{uuid.uuid4().hex[:8]}"
    path.mkdir(exist_ok=False)
    return path


def _dataset_records(scen: ScenarioData) -> list[DatasetRecord]:
    if scen.source == "synthetic_network":
        return [DatasetRecord(id="SYNTHETIC:synthetic_network", license_note="generated in-process; no external data")]
    lab = scen.label
    recs = []
    for path, digest in sorted(scen.file_hashes.items()):
        recs.append(
            DatasetRecord(
                id=f"INSTANCE v3 sample / INGV: {Path(path).name}",
                source_url="https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2"
                if "instance_sample" in path or path.endswith(".csv") or path.endswith(".hdf5")
                else "https://webservices.ingv.it/fdsnws/dataselect/1/query",
                doi=lab["doi"],
                license_note=lab["license"],
                sha256=digest,
            )
        )
    return recs


def write_run(
    raw: dict[str, Any],
    cfg: ExperimentConfig,
    results: list[SeedResult],
    out: Path,
    config_path: str,
    scen: ScenarioData,
    overrides: list[dict[str, Any]] | None = None,
) -> None:
    from quakenode.report import write_report

    metrics = {
        "schema": METRIC_VERSION,
        "synthetic": scen.source == "synthetic_network",
        "notice": scen.warnings[0],
        "data": scen.label,
        "gap_policy": cfg.pipeline.gap_policy,
        "order_policy": cfg.pipeline.order_policy,
        "detector": cfg.detector.name,
        "station_info": scen.station_info,
        "station_exclusions": scen.exclusions,
        "n_seeds": len(results),
        "seeds": [r.seed for r in results],
        **aggregate(results),
        "per_seed": {
            str(r.seed): {
                "summary": r.summary,
                "stations": r.stations,
                "event": r.event,
                "faults": [x.to_dict() | {"affected": len(x.affected)} for x in r.fault_records],
            }
            for r in results
        },
    }
    metrics["results_sha256"] = results_sha256(metrics)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with open(out / "events.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in results:
            for e in r.events:
                f.write(
                    json.dumps(
                        {**e, "input_kind": scen.input_kind, "gap_policy": cfg.pipeline.gap_policy}, sort_keys=True
                    )
                    + "\n"
                )
    with open(out / "metrics.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scope", "seed", "station", "metric", "value"])
        for r in results:
            for k, v in r.summary.items():
                w.writerow(["seed", r.seed, "", k, "" if v is None else v])
            for s in r.stations:
                for k, v in s.items():
                    if k != "station_id":
                        w.writerow(["station", r.seed, s["station_id"], k, "" if v is None else v])
    manifest = RunManifest.create(
        config={
            "config_file": config_path,
            "experiment": raw,
            "overrides": overrides or [],
            "input_kind": scen.input_kind,
            "quakenode_version": __version__,
        },
        seeds=[r.seed for r in results],
        metric_definition_version=METRIC_VERSION,
        repo_dir=Path.cwd(),
        datasets=_dataset_records(scen),
        output_paths=[
            str(out / n) for n in ("manifest.json", "events.jsonl", "metrics.json", "metrics.csv", "report.md")
        ],
        warnings=[*scen.warnings, BANNER],
        exclusions=[f"{e['trace']}: {e['reason']}" for e in scen.exclusions],
    )
    (out / "manifest.json").write_text(manifest.to_json() + "\n", encoding="utf-8")
    write_report(out)


def run_experiment(
    raw: dict[str, Any],
    config_path: str = "<config>",
    out_dir: Path | None = None,
    out_root: Path | None = None,
    overrides: list[dict[str, Any]] | None = None,
) -> Path:
    """Validate, run all seeds, write a NEW run directory (never overwrites) and return its path."""
    cfg = parse_config(raw, config_path)
    scen = load_scenario(cfg)  # real data are loaded once; the seeds only change fault randomness
    out = out_dir if out_dir is not None else _unique_dir(out_root or Path(cfg.output_dir), cfg.name)
    if out_dir is not None:
        out.mkdir(parents=True, exist_ok=False)
    results = [run_seed(cfg, s, scen) for s in cfg.seeds]
    write_run(raw, cfg, results, out, config_path, scen, overrides)
    return out


# ---- sweeps -----------------------------------------------------------------------------------------------------


def _grid(cfg: ExperimentConfig) -> list[dict[str, Any]]:
    assert cfg.sweep is not None
    names = [p.path for p in cfg.sweep.parameters]
    return [
        dict(zip(names, combo, strict=True)) for combo in itertools.product(*[p.values for p in cfg.sweep.parameters])
    ]


def run_sweep(
    raw: dict[str, Any],
    config_path: str = "<config>",
    out_root: Path | None = None,
    overrides: list[dict[str, Any]] | None = None,
) -> Path:
    """Grid over one or two parameters, same seeds, paired by seed against a MATCHED no-fault control.

    Parameters whose path does not start with 'faults' (a detector name, a gap policy, ...) also define the
    control: each distinct combination of them gets its own control run (same settings, faults removed).
    """
    from quakenode.report import write_sweep_report

    cfg = parse_config(raw, config_path)
    if cfg.sweep is None:
        raise ValueError(f"{config_path}: no 'sweep' section")
    out = _unique_dir(out_root or Path(cfg.output_dir), f"{cfg.name}-sweep")
    (out / "runs").mkdir()
    overrides = overrides or []

    def clean(d: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in d.items() if k != "sweep"}

    non_fault = [p.path for p in cfg.sweep.parameters if not p.path.startswith("faults")]
    controls: dict[tuple, dict[str, Any]] = {}

    def control_for(params: dict[str, Any]) -> dict[str, Any]:
        key = tuple((p, params[p]) for p in non_fault)
        if key not in controls:
            n = len(controls) + 1
            craw = clean(raw) | {"name": f"{cfg.name}-control{n:02d}", "faults": []}
            sweep_ov = []
            for p, v in key:
                craw = set_path(craw, p, v, create=True)
                sweep_ov.append({"path": p, "value": v, "source": "sweep"})
            cdir = run_experiment(
                craw, config_path, out_dir=out / "runs" / f"control_{n:02d}", overrides=overrides + sweep_ov
            )
            controls[key] = {
                "index": n,
                "key": {p: v for p, v in key},
                "run_dir": cdir.relative_to(out).as_posix(),
                "metrics": json.loads((cdir / "metrics.json").read_text(encoding="utf-8")),
            }
        return controls[key]

    points = []
    for i, params in enumerate(_grid(cfg), 1):
        ctrl = control_for(params)
        point_raw = clean(raw)
        sweep_ov = []
        for path, value in params.items():
            point_raw = set_path(point_raw, path, value, create=True)
            sweep_ov.append({"path": path, "value": value, "source": "sweep"})
        point_raw["name"] = f"{cfg.name}-point{i:02d}"
        pdir = run_experiment(
            point_raw, config_path, out_dir=out / "runs" / f"point_{i:02d}", overrides=overrides + sweep_ov
        )
        m = json.loads((pdir / "metrics.json").read_text(encoding="utf-8"))
        paired = {}
        for metric in HEADLINE_METRICS:
            test = {int(sd): v["summary"][metric] for sd, v in m["per_seed"].items()}
            ref = {int(sd): v["summary"][metric] for sd, v in ctrl["metrics"]["per_seed"].items()}
            paired[metric] = paired_difference(test, ref, cfg.metrics.bootstrap_seed)
        points.append(
            {
                "index": i,
                "parameters": params,
                "run_dir": pdir.relative_to(out).as_posix(),
                "control_index": ctrl["index"],
                "aggregate": {
                    "summary_over_seeds": m["summary_over_seeds"],
                    "event_detection_rate": m["event_detection_rate"],
                },
                "paired_vs_control": paired,
            }
        )
    first = m
    result = {
        "schema": "quakenode_sweep_v2",
        "synthetic": first["synthetic"],
        "notice": first["notice"],
        "data": first["data"],
        "name": cfg.name,
        "seeds": cfg.seeds,
        "base_gap_policy": cfg.pipeline.gap_policy,
        "overrides": overrides,
        "parameters": [{"path": p.path, "values": p.values} for p in cfg.sweep.parameters],
        "headline_metric": cfg.sweep.headline_metric,
        "controls": [
            {
                "index": c["index"],
                "key": c["key"],
                "run_dir": c["run_dir"],
                "aggregate": {
                    "summary_over_seeds": c["metrics"]["summary_over_seeds"],
                    "event_detection_rate": c["metrics"]["event_detection_rate"],
                },
            }
            for c in controls.values()
        ],
        "points": points,
    }
    result["results_sha256"] = results_sha256(result)
    (out / "sweep_results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if first["synthetic"]:
        sweep_dataset = DatasetRecord(
            id="SYNTHETIC:synthetic_network", license_note="generated in-process; no external data"
        )
    else:
        sweep_dataset = DatasetRecord(
            id="INSTANCE v3 sample / INGV (file hashes in each run manifest)",
            doi=first["data"]["doi"],
            license_note=first["data"]["license"],
        )
    manifest = RunManifest.create(
        config={
            "config_file": config_path,
            "experiment": raw,
            "overrides": overrides,
            "quakenode_version": __version__,
        },
        seeds=cfg.seeds,
        metric_definition_version=METRIC_VERSION,
        repo_dir=Path.cwd(),
        datasets=[sweep_dataset],
        output_paths=[str(out / "sweep_results.json"), str(out / "sweep_table.md"), str(out / "runs")],
        warnings=[first["notice"], BANNER],
    )  # fmt: skip
    (out / "manifest.json").write_text(manifest.to_json() + "\n", encoding="utf-8")
    write_sweep_report(out)
    return out
