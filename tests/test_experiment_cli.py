"""End-to-end: CLI, run directory contents, determinism, sweep pairing, whole-chain counterfactual with faults.

Everything runs on the SYNTHETIC network scenario.
"""

import copy
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from pathlib import Path

from quakenode.cli import BANNER, main
from quakenode.config import parse_config
from quakenode.experiment import build_fault, network_spec, run_experiment, run_seed
from quakenode.faults import apply_faults
from quakenode.fusion import FusionConfig, fuse
from quakenode.manifest import RunManifest
from quakenode.replay import ReplayEngine
from quakenode.scenario import build_packets
from quakenode.streaming import StreamingPipeline, create_detector_factory

HAVE_MPL = importlib.util.find_spec("matplotlib") is not None

RAW = {
    "schema_version": 1,
    "name": "unit",
    "seeds": [1, 2, 3],
    "scenario": {
        "stations": [
            {"id": f"S{i}", "x_km": x, "y_km": y} for i, (x, y) in enumerate([(0, 0), (40, 5), (20, 45), (-30, 30)], 1)
        ],
        "event": {"origin_time_s": 8.0, "x_km": 15, "y_km": 20, "amplitude": 60},
        "duration_s": 25,
        "sample_rate_hz": 20,
        "packet_len_samples": 10,
    },
    "detector": {"name": "sta_lta_rms", "params": {"sta_s": 0.5, "lta_s": 3.0}},
    "faults": [{"type": "fixed_delay", "delay_s": 0.2}, {"type": "packet_loss", "p": 0.05}],
    "fusion": {"k": 2, "window_s": 10, "update_window_s": 4},
}


def cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main([str(a) for a in argv])
    return code, out.getvalue(), err.getvalue()


def write_cfg(tmp, raw, name="cfg.yaml"):
    import yaml

    path = Path(tmp) / name
    path.write_text(yaml.safe_dump(raw))
    return path


class CliRunTests(unittest.TestCase):
    def test_banner_version_and_validate(self):
        code, out, _ = cli("version")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], BANNER)
        self.assertIn("quakenode 0.", out)
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = cli("validate", write_cfg(tmp, RAW))
            self.assertEqual(code, 0)
            self.assertIn(": OK", out)
            bad = copy.deepcopy(RAW)
            bad["faults"][0]["delay_s"] = -1
            code, out, err = cli("validate", write_cfg(tmp, bad, "bad.yaml"))
            self.assertEqual(code, 2)
            self.assertIn("bad.yaml: faults[0].delay_s: must be a number >= 0", err)
            self.assertEqual(out.splitlines()[0], BANNER)

    def test_run_writes_all_outputs_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_cfg(tmp, RAW)
            dirs = []
            for _ in range(2):
                code, out, _ = cli("run", path, "--out-dir", Path(tmp) / "runs")
                self.assertEqual(code, 0)
                self.assertEqual(out.splitlines()[0], BANNER)
                dirs.append(
                    Path(next(line for line in out.splitlines() if line.startswith("run directory:")).split(": ", 1)[1])
                )
            self.assertNotEqual(dirs[0], dirs[1])
            self.assertTrue(all(d.is_dir() for d in dirs))
            run = dirs[0]
            for name in ("manifest.json", "events.jsonl", "metrics.json", "metrics.csv", "report.md"):
                self.assertTrue((run / name).stat().st_size > 0, name)
            if HAVE_MPL:
                self.assertTrue((run / "plots" / "latency_per_station.png").exists())
            manifest = RunManifest.from_json((run / "manifest.json").read_text())
            self.assertEqual(manifest.seeds, [1, 2, 3])
            self.assertEqual(manifest.config["experiment"]["name"], "unit")
            self.assertEqual(manifest.datasets[0].id, "SYNTHETIC:synthetic_network")
            self.assertTrue(any("SYNTHETIC" in w for w in manifest.warnings))
            self.assertIn("python_version", manifest.to_dict())
            metrics = json.loads((run / "metrics.json").read_text())
            self.assertTrue(metrics["synthetic"])
            self.assertEqual(metrics["n_seeds"], 3)
            lines = [json.loads(line) for line in (run / "events.jsonl").read_text().splitlines()]
            kinds = {e["kind"] for e in lines}
            self.assertTrue({"fault", "detection", "fusion", "candidate", "seed_summary"} <= kinds, kinds)
            fault_events = [e for e in lines if e["kind"] == "fault"]
            self.assertEqual([e["type"] for e in fault_events[:2]], ["fixed_delay", "packet_loss"])
            report = (run / "report.md").read_text()
            self.assertIn(BANNER, report)
            self.assertIn("SYNTHETIC", report)
            # determinism: identical results hash, different run directories
            self.assertEqual(
                json.loads((dirs[1] / "metrics.json").read_text())["results_sha256"], metrics["results_sha256"]
            )
            # the report command regenerates the report
            (run / "report.md").unlink()
            code, out, _ = cli("report", run)
            self.assertEqual(code, 0)
            self.assertTrue((run / "report.md").exists())
            code, _, err = cli("report", tmp)
            self.assertEqual(code, 2)
            self.assertIn("not a QuakeNode run or sweep directory", err)

    def test_control_scenario_has_no_fault_records_and_full_completeness(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = {**RAW, "faults": []}
            run = run_experiment(raw, "t.yaml", out_root=Path(tmp))
            m = json.loads((run / "metrics.json").read_text())
            self.assertTrue(all(v["faults"] == [] for v in m["per_seed"].values()))
            self.assertEqual(m["summary_over_seeds"]["mean_completeness"]["min"], 1.0)
            self.assertEqual(m["summary_over_seeds"]["detection_fraction"]["median"], 1.0)

    def test_reject_policy_with_reordering_fails_loudly(self):
        raw = {**RAW, "faults": [{"type": "reorder", "p": 0.5, "hold_s": 3.0}], "pipeline": {"order_policy": "reject"}}
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(Exception) as cm:
            run_experiment(raw, "t.yaml", out_root=Path(tmp))
        self.assertIn("out of order", str(cm.exception))
        ok = {**raw, "pipeline": {"order_policy": "buffer", "max_wait_s": 4.0}}
        with tempfile.TemporaryDirectory() as tmp:
            run = run_experiment(ok, "t.yaml", out_root=Path(tmp))
            events = [json.loads(x) for x in (run / "events.jsonl").read_text().splitlines()]
            self.assertFalse([e for e in events if e["kind"] == "gap"])  # 4 s of buffering absorbs a 3 s hold


class OverrideCliTests(unittest.TestCase):
    def test_set_overrides_change_the_run_and_are_recorded_in_the_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_cfg(tmp, RAW)
            code, out, _ = cli("run", path, "--out-dir", Path(tmp) / "runs", "--set", "detector.name=recursive_sta_lta",
                               "--set", "pipeline.gap_policy=hold", "--set", "faults.1.p=0.2")  # fmt: skip
            self.assertEqual(code, 0)
            self.assertIn(
                "overrides: detector.name='recursive_sta_lta', pipeline.gap_policy='hold', faults.1.p=0.2", out
            )
            run = Path(next(x for x in out.splitlines() if x.startswith("run directory:")).split(": ", 1)[1])
            man = json.loads((run / "manifest.json").read_text())
            self.assertEqual([o["path"] for o in man["config"]["overrides"]],
                             ["detector.name", "pipeline.gap_policy", "faults.1.p"])  # fmt: skip
            self.assertEqual(man["config"]["experiment"]["faults"][1]["p"], 0.2)
            m = json.loads((run / "metrics.json").read_text())
            self.assertEqual((m["detector"], m["gap_policy"]), ("recursive_sta_lta", "hold"))
            self.assertIn("Overrides applied", (run / "report.md").read_text())

    def test_invalid_override_is_a_config_error_with_exit_code_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_cfg(tmp, RAW)
            code, _, err = cli("run", path, "--set", "pipeline.gap_policy=magic")
            self.assertEqual(code, 2)
            self.assertIn("pipeline.gap_policy: must be one of", err)
            code, _, err = cli("validate", path, "--set", "nonsense")
            self.assertEqual(code, 2)
            self.assertIn("expected key=value", err)

    def test_sweep_over_a_categorical_parameter_uses_matched_controls(self):
        sweep = {"parameters": [{"path": "detector.name", "values": ["sta_lta_rms", "recursive_sta_lta"]}]}
        raw = {**RAW, "faults": [{"type": "packet_loss", "p": 0.2}], "sweep": sweep}
        raw["detector"] = {"name": "sta_lta_rms", "params": {"sta_s": 0.5, "lta_s": 3.0}}
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = cli("sweep", write_cfg(tmp, raw, "d.yaml"), "--out-dir", Path(tmp) / "runs")
            self.assertEqual(code, 0)
            sweep = Path(next(x for x in out.splitlines() if x.startswith("sweep directory:")).split(": ", 1)[1])
            res = json.loads((sweep / "sweep_results.json").read_text())
            self.assertEqual([c["key"] for c in res["controls"]],
                             [{"detector.name": "sta_lta_rms"}, {"detector.name": "recursive_sta_lta"}])  # fmt: skip
            self.assertEqual([p["control_index"] for p in res["points"]], [1, 2])
            for c in res["controls"]:
                m = json.loads((sweep / c["run_dir"] / "metrics.json").read_text())
                self.assertEqual(m["detector"], c["key"]["detector.name"])  # the control uses the point's detector
                self.assertTrue(all(v["faults"] == [] for v in m["per_seed"].values()))
            self.assertIn(
                "control (no faults) [detector.name=recursive_sta_lta]", (sweep / "sweep_table.md").read_text()
            )


class SweepTests(unittest.TestCase):
    def test_sweep_pairs_against_the_control_and_zero_fault_equals_control(self):
        raw = {**RAW, "faults": [{"type": "packet_loss", "p": 0.0}],
               "sweep": {"parameters": [{"path": "faults.0.p", "values": [0.0, 0.2, 0.6]}]}}  # fmt: skip
        with tempfile.TemporaryDirectory() as tmp:
            path = write_cfg(tmp, raw, "sweep.yaml")
            code, out, _ = cli("sweep", path, "--out-dir", Path(tmp) / "runs")
            self.assertEqual(code, 0)
            self.assertIn("| faults.0.p |", out)
            sweep = Path(
                next(line for line in out.splitlines() if line.startswith("sweep directory:")).split(": ", 1)[1]
            )
            res = json.loads((sweep / "sweep_results.json").read_text())
            self.assertEqual([p["parameters"]["faults.0.p"] for p in res["points"]], [0.0, 0.2, 0.6])
            zero = res["points"][0]["paired_vs_control"]["detection_fraction"]
            self.assertEqual(
                (zero["n_paired"], zero["n_zero"]), (3, 3)
            )  # p=0 is identical to the control, seed by seed
            lossy = res["points"][2]["paired_vs_control"]["detection_fraction"]
            self.assertGreater(lossy["n_negative"], 0)
            self.assertTrue((sweep / "sweep_table.md").exists())
            self.assertTrue((sweep / "sweep_table.csv").exists())
            self.assertTrue((sweep / "runs" / "control_01" / "metrics.json").exists())
            self.assertTrue((sweep / "runs" / "point_03" / "events.jsonl").exists())
            self.assertEqual(RunManifest.from_json((sweep / "manifest.json").read_text()).seeds, [1, 2, 3])
            if HAVE_MPL:
                self.assertTrue((sweep / "plots" / "sweep.png").exists())

    def test_sweep_requires_a_sweep_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                from quakenode.experiment import run_sweep

                run_sweep(copy.deepcopy(RAW), "t.yaml", out_root=Path(tmp))


class CounterfactualWithFaultsTests(unittest.TestCase):
    def test_whole_chain_ignores_packets_arriving_after_the_cutoff(self):
        raw = {**RAW, "faults": [{"type": "jitter", "distribution": "uniform", "low_s": 0.0, "high_s": 1.5},
                                 {"type": "reorder", "p": 0.2, "hold_s": 1.0},
                                 {"type": "packet_loss", "p": 0.05}],
               "pipeline": {"order_policy": "buffer", "max_wait_s": 2.0}}  # fmt: skip
        cfg = parse_config(raw, "t.yaml")
        spec = network_spec(cfg)
        packets = build_packets(spec, seed=4)
        faulted, _ = apply_faults(packets, [build_fault(f) for f in cfg.faults], 4)
        factory = create_detector_factory(cfg.detector.name, cfg.detector.params, 0.0)
        cutoff = 13.0
        mutated = [
            replace(p, samples=tuple(x + 1e3 for x in p.samples)) if p.arrival_time_s > cutoff else p for p in faulted
        ]
        self.assertTrue(any(a != b for a, b in zip(faulted, mutated, strict=True)))

        def through_cutoff(pks):
            engine = ReplayEngine()
            engine.schedule(pks, allow_duplicates=True)
            pipe = StreamingPipeline(detector_factory=factory, order_policy="buffer", max_wait_s=2.0)
            pipe.run(engine, [cutoff])
            fused = fuse(pipe.detections, FusionConfig(2, 10.0, 4.0))
            return pipe, fused

        a, fa = through_cutoff(faulted)
        b, fb = through_cutoff(mutated)
        self.assertGreater(len(a.processed), 0)
        self.assertEqual(a.detections, b.detections)
        self.assertEqual(a.gap_events, b.gap_events)
        self.assertEqual(a.dropped, b.dropped)
        self.assertEqual(a.processed, b.processed)
        self.assertEqual(fa.decisions, fb.decisions)
        # and the future does change what happens afterwards
        full_a, _ = through_cutoff(faulted)
        engine = ReplayEngine()
        engine.schedule(mutated, allow_duplicates=True)
        later = StreamingPipeline(detector_factory=factory, order_policy="buffer", max_wait_s=2.0).run(engine)
        engine = ReplayEngine()
        engine.schedule(faulted, allow_duplicates=True)
        earlier = StreamingPipeline(detector_factory=factory, order_policy="buffer", max_wait_s=2.0).run(engine)
        self.assertNotEqual(later.processed, earlier.processed)
        self.assertIsNotNone(full_a)

    def test_run_seed_is_deterministic_and_seeds_differ(self):
        cfg = parse_config(RAW, "t.yaml")
        a, b, c = run_seed(cfg, 1), run_seed(cfg, 1), run_seed(cfg, 2)
        self.assertEqual(a.events, b.events)
        self.assertEqual(a.summary, b.summary)
        self.assertNotEqual(a.events, c.events)

    def test_clock_offset_changes_reported_but_not_true_times(self):
        base = {**RAW, "faults": []}
        shifted = {**RAW, "faults": [{"type": "clock_offset", "offset_s": 2.5, "targets": ["S1"]}]}
        a = run_seed(parse_config(base, "t.yaml"), 1)
        b = run_seed(parse_config(shifted, "t.yaml"), 1)
        da = next(d for d in a.detections if d.station_id == "S1")
        db = next(d for d in b.detections if d.station_id == "S1")
        self.assertEqual(da.trigger_sample_time_s, db.trigger_sample_time_s)
        self.assertEqual(da.emission_time_s, db.emission_time_s)
        self.assertIsNone(da.reported_trigger_sample_time_s)
        self.assertEqual(db.reported_trigger_sample_time_s, db.trigger_sample_time_s + 2.5)
        s1 = next(s for s in b.stations if s["station_id"] == "S1")
        self.assertAlmostEqual(s1["reported_timestamp_error_s"], 2.5)
        self.assertEqual(a.summary["median_sample_latency_s"], b.summary["median_sample_latency_s"])


if __name__ == "__main__":
    unittest.main()
