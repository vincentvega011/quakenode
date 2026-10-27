"""Gap policies (reset / hold / zero_fill) on hand-built streams, determinism, counterfactual, reporting.

All streams and scenarios here are SYNTHETIC.
"""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from quakenode.config import parse_config
from quakenode.experiment import build_fault, run_experiment, run_seed
from quakenode.faults import apply_faults
from quakenode.fusion import FusionConfig, fuse
from quakenode.replay import ReplayEngine, Trace
from quakenode.scenario import build_packets
from quakenode.scenario.loader import network_spec
from quakenode.streaming import GAP_POLICIES, StreamingPipeline, create_detector_factory

RATE = 10.0
BASE = 5.0  # baseline offset: zeros inserted by zero_fill are a step of -5 against it


def stream(n=100):
    x = [BASE + (0.1 if i % 2 == 0 else -0.1) for i in range(n)]
    for i in range(41, 51):  # burst starts one sample after the gap (packet 3 = samples 30..39 is missing)
        x[i] += 5.0
    return x


def packets_without_3():
    pks = ReplayEngine.packetize(Trace("S", "SYN", RATE, tuple(stream())), 10)
    return [p for p in pks if p.sequence_number != 3]


def run(policy, pks=None):
    engine = ReplayEngine()
    engine.schedule(pks if pks is not None else packets_without_3())
    pipe = StreamingPipeline(
        alpha=0.99, warmup_samples=0, sta_samples=2, lta_samples=6, threshold=3.0, gap_policy=policy
    )
    return pipe.run(engine)


class PolicyBehaviourTests(unittest.TestCase):
    def test_every_policy_logs_the_gap_with_sample_counts(self):
        for policy in GAP_POLICIES:
            with self.subTest(policy=policy):
                pipe = run(policy)
                (g,) = pipe.gap_events
                self.assertEqual(
                    (g.expected_index, g.received_index, g.missing_samples, g.policy), (30, 40, 10, policy)
                )
                self.assertEqual(g.filled_samples, 10 if policy == "zero_fill" else 0)
                self.assertEqual(g.state_kept, policy != "reset")
                self.assertEqual(pipe.samples_processed("S", "SYN"), 90)  # recorded samples only
                self.assertEqual(pipe.samples_filled("S", "SYN"), 10 if policy == "zero_fill" else 0)

    def test_reset_rewarms_and_misses_the_burst_that_follows_the_gap(self):
        pipe = run("reset")
        self.assertEqual(pipe.detections, [])  # LTA window after the reset already contains the burst
        self.assertFalse(pipe.warming_up("S", "SYN"))  # re-warmed by the end of the stream

    def test_reset_is_the_previous_default_behaviour(self):
        engine = ReplayEngine()
        engine.schedule(packets_without_3())
        legacy = StreamingPipeline(alpha=0.99, warmup_samples=0, sta_samples=2, lta_samples=6, threshold=3.0).run(
            engine
        )
        explicit = run("reset")
        self.assertEqual(legacy.gap_policy, "reset")
        self.assertEqual((legacy.detections, legacy.gap_events, legacy.processed),
                         (explicit.detections, explicit.gap_events, explicit.processed))  # fmt: skip

    def test_hold_keeps_state_and_detects_the_burst_immediately(self):
        pipe = run("hold")
        (d,) = pipe.detections
        self.assertEqual(d.trigger_sample_index, 41)  # state kept: the LTA still holds pre-gap quiet samples
        self.assertFalse(d.on_filled_samples)
        self.assertEqual(pipe.samples_filled("S", "SYN"), 0)

    def test_zero_fill_inserts_labeled_zeros_that_can_trigger_the_detector(self):
        pipe = run("zero_fill")
        (d,) = pipe.detections
        # zeros against a baseline of 5 are a step of -5: the trigger happens on the first FILLED sample (index 30)
        self.assertEqual(d.trigger_sample_index, 30)
        self.assertTrue(d.on_filled_samples)
        self.assertEqual(d.trigger_sample_time_s, 3.0)
        self.assertGreaterEqual(d.emission_time_s, d.arrival_time_s)
        self.assertEqual(pipe.samples_filled("S", "SYN"), 10)
        # filled samples are not logged as processed recorded packets
        self.assertEqual(len(pipe.processed), 9)

    def test_no_interpolation_ever(self):
        pipe = run("zero_fill")
        fill = [p for p in pipe.processed if p.sequence_number == 4]
        self.assertTrue(fill)  # the recorded packet after the gap is processed as itself
        engine = ReplayEngine()
        engine.schedule(packets_without_3())
        seen = []
        original = StreamingPipeline._process

        def spy(self, stream_, packet, at_s, filled=False):
            if filled:
                seen.append(packet.samples)
            return original(self, stream_, packet, at_s, filled)

        StreamingPipeline._process = spy
        try:
            StreamingPipeline(alpha=0.99, warmup_samples=0, sta_samples=2, lta_samples=6, threshold=3.0,
                              gap_policy="zero_fill").run(engine)  # fmt: skip
        finally:
            StreamingPipeline._process = original
        self.assertEqual(seen, [(0.0,) * 10])

    def test_policies_are_deterministic(self):
        for policy in GAP_POLICIES:
            a, b = run(policy), run(policy)
            self.assertEqual((a.detections, a.gap_events, a.processed), (b.detections, b.gap_events, b.processed))

    def test_policies_agree_when_there_is_no_gap(self):
        full = ReplayEngine.packetize(Trace("S", "SYN", RATE, tuple(stream())), 10)
        results = [run(p, full) for p in GAP_POLICIES]
        for r in results[1:]:
            self.assertEqual((r.detections, r.gap_events), (results[0].detections, results[0].gap_events))
        self.assertEqual(results[0].gap_events, [])

    def test_invalid_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            StreamingPipeline(
                alpha=0.5, warmup_samples=0, sta_samples=2, lta_samples=6, threshold=3.0, gap_policy="interpolate"
            )

    def test_gap_at_the_buffer_deadline_also_follows_the_policy(self):
        engine = ReplayEngine()
        engine.schedule(packets_without_3())
        pipe = StreamingPipeline(alpha=0.99, warmup_samples=0, sta_samples=2, lta_samples=6, threshold=3.0,
                                 gap_policy="zero_fill", order_policy="buffer", max_wait_s=1.5)  # fmt: skip
        pipe.run(engine)
        (g,) = pipe.gap_events
        self.assertEqual((g.missing_samples, g.filled_samples, g.policy), (10, 10, "zero_fill"))
        self.assertGreater(g.declared_time_s, g.arrival_time_s)  # declared at the deadline


RAW = {
    "schema_version": 1,
    "name": "gap",
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
    "faults": [{"type": "packet_loss", "p": 0.15}],
    "fusion": {"k": 2, "window_s": 10, "update_window_s": 4},
}


def raw_with(policy, **fusion):
    raw = json.loads(json.dumps(RAW))
    raw["pipeline"] = {"gap_policy": policy}
    raw["fusion"].update(fusion)
    return raw


def _through(pks, factory, policy, cutoff):
    engine = ReplayEngine()
    engine.schedule(pks)
    pipe = StreamingPipeline(detector_factory=factory, gap_policy=policy)
    pipe.run(engine, [cutoff])
    return pipe, fuse([d for d in pipe.detections if not d.on_filled_samples], FusionConfig(2, 10.0, 4.0))


class WholeChainTests(unittest.TestCase):
    def test_future_mutation_counterfactual_holds_under_every_policy(self):
        for policy in GAP_POLICIES:
            with self.subTest(policy=policy):
                cfg = parse_config(raw_with(policy), "t.yaml")
                packets = build_packets(network_spec(cfg), seed=4)
                faulted, _ = apply_faults(packets, [build_fault(f) for f in cfg.faults], 4)
                factory = create_detector_factory(cfg.detector.name, cfg.detector.params, 0.0)
                cutoff = 12.0
                mutated = [
                    replace(p, samples=tuple(x + 1e3 for x in p.samples)) if p.arrival_time_s > cutoff else p
                    for p in faulted
                ]
                self.assertTrue(any(a != b for a, b in zip(faulted, mutated, strict=True)))

                a, fa = _through(faulted, factory, policy, cutoff)
                b, fb = _through(mutated, factory, policy, cutoff)
                self.assertGreater(len(a.gap_events), 0)
                self.assertEqual(
                    (a.detections, a.gap_events, a.dropped, a.processed),
                    (b.detections, b.gap_events, b.dropped, b.processed),
                )
                self.assertEqual(fa.decisions, fb.decisions)

    def test_metrics_report_the_policy_and_filled_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            for policy in GAP_POLICIES:
                run_dir = run_experiment(raw_with(policy), "t.yaml", out_root=Path(tmp))
                m = json.loads((run_dir / "metrics.json").read_text())
                self.assertEqual(m["gap_policy"], policy)
                self.assertIn(f"gap policy: **{policy}**", (run_dir / "report.md").read_text())
                events = [json.loads(x) for x in (run_dir / "events.jsonl").read_text().splitlines()]
                self.assertTrue(all(e["gap_policy"] == policy for e in events))
                gaps = [e for e in events if e["kind"] == "gap"]
                self.assertTrue(gaps)
                self.assertTrue(all(e["policy"] == policy and e["missing_samples"] >= 1 for e in gaps))
                filled = sum(e["filled_samples"] for e in gaps)
                self.assertEqual(filled > 0, policy == "zero_fill")
                self.assertEqual(m["summary_over_seeds"]["filled_samples_total"]["max"] > 0, policy == "zero_fill")
                self.assertGreater(m["summary_over_seeds"]["gap_events"]["min"], -1)

    def test_fusion_excludes_filled_detections_by_default_and_logs_it(self):
        cfg = parse_config(raw_with("zero_fill"), "t.yaml")
        results = [run_seed(cfg, s) for s in range(1, 6)]
        on_filled = sum(s["detections_on_filled_samples"] for r in results for s in r.stations)
        self.assertGreater(on_filled, 0)  # baseline 800 -> zeros is a huge step: fills trigger the detector
        excluded = [e for r in results for e in r.events if e.get("decision") == "excluded_filled_detection"]
        self.assertEqual(len(excluded), on_filled)
        # metrics: filled-triggered detections are not hits and not false triggers
        for r in results:
            for s in r.stations:
                n_det = len([d for d in r.detections if d.station_id == s["station_id"]])
                counted = s["false_triggers"] + (1 if s["detected"] else 0)
                self.assertLessEqual(counted, n_det - s["detections_on_filled_samples"] + 1)
        keep = parse_config(raw_with("zero_fill", exclude_filled_detections=False), "t.yaml")
        kept_events = [
            e for s in range(1, 6) for e in run_seed(keep, s).events if e.get("decision") == "excluded_filled_detection"
        ]
        self.assertEqual(kept_events, [])


if __name__ == "__main__":
    unittest.main()
