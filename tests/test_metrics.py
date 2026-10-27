"""Metrics with hand-computed expectations (docs/metrics.md). Detections and truth are SYNTHETIC toy values."""

import math
import unittest

from quakenode.evaluation import (
    MetricsConfig,
    StationTruth,
    bootstrap_ci_median,
    distribution,
    event_metrics,
    paired_difference,
    quantile,
    seed_summary,
    station_metrics,
    wilson_interval,
)
from quakenode.fusion import Candidate
from quakenode.replay import Detection

CFG = MetricsConfig(detection_pre_margin_s=1.0, detection_post_horizon_s=10.0)


def det(station, sample_t, emission_t, reported=None):
    arrival = emission_t - 0.1
    return Detection(
        station,
        "SYN",
        int(sample_t * 10),
        sample_t,
        sample_t,
        arrival,
        emission_t,
        0.0,
        "t",
        "1",
        5.0,
        3.0,
        (),
        reported,
    )


class StationMetricTests(unittest.TestCase):
    def test_latencies_false_triggers_and_completeness(self):
        truth = StationTruth("S1", p_time_s=20.0, n_samples_total=100, warmup_s=5.0, duration_s=40.0)
        dets = [
            det("S1", 15.0, 15.4),
            det("S1", 20.3, 20.8, reported=20.8),
            det("S1", 25.0, 25.2),
            det("S2", 20.1, 20.2),
        ]
        m = station_metrics(truth, dets, samples_processed=90, cfg=CFG)
        self.assertTrue(m["detected"])
        self.assertAlmostEqual(m["sample_latency_s"], 0.3)  # first hit 20.3 - 20.0
        self.assertAlmostEqual(m["emission_latency_s"], 0.8)  # 20.8 - 20.0
        self.assertAlmostEqual(m["reported_timestamp_error_s"], 0.5)  # reported 20.8 - true 20.3
        self.assertEqual(m["false_triggers"], 1)  # 15.0 < P - 1.0 = 19.0; the S2 detection is not this station's
        self.assertAlmostEqual(m["scored_pre_event_s"], 14.0)  # 20 - 1 - 5
        self.assertAlmostEqual(m["completeness"], 0.9)

    def test_pre_margin_boundary_and_undetected(self):
        truth = StationTruth("S1", 20.0, 100, 0.0, 40.0)
        self.assertTrue(station_metrics(truth, [det("S1", 19.0, 19.2)], 100, CFG)["detected"])  # exactly P - margin
        self.assertFalse(station_metrics(truth, [det("S1", 30.5, 30.6)], 100, CFG)["detected"])  # beyond the horizon
        none = station_metrics(truth, [], 100, CFG)
        self.assertEqual((none["detected"], none["sample_latency_s"], none["emission_latency_s"]), (False, None, None))

    def test_noise_only_scenario_counts_every_detection_as_false(self):
        truth = StationTruth("S1", None, 400, 5.0, 40.0)
        m = station_metrics(truth, [det("S1", 12.0, 12.1)], 400, CFG)
        self.assertEqual((m["detected"], m["false_triggers"]), (None, 1))
        self.assertAlmostEqual(m["scored_pre_event_s"], 35.0)


class EventMetricTests(unittest.TestCase):
    def setUp(self):
        self.truths = [
            StationTruth(s, p, 100, 0.0, 40.0) for s, p in (("S1", 10.0), ("S2", 12.0), ("S3", 15.0), ("S4", 20.0))
        ]

    def test_reference_is_the_kth_true_arrival_and_candidates_are_judged_by_their_hits(self):
        good = [det("S1", 10.2, 10.5), det("S2", 12.1, 12.9), det("S3", 15.3, 17.5)]
        weak = [det("S1", 3.0, 3.5), det("S2", 4.0, 4.5), det("S4", 20.2, 20.5)]  # two pre-event false triggers
        cands = [Candidate(1, 17.5, good), Candidate(2, 20.5, weak)]
        m = event_metrics(self.truths, good + weak, cands, k=3, cfg=CFG)
        self.assertEqual(m["reference_time_s"], 15.0)  # 3rd smallest P: 10, 12, 15
        self.assertEqual((m["n_candidates"], m["true_candidates"], m["false_candidates"]), (2, 1, 1))
        self.assertTrue(m["event_detected"])
        self.assertAlmostEqual(m["association_latency_s"], 2.5)  # 17.5 - 15.0

    def test_no_true_candidate_means_not_detected(self):
        weak = [det("S1", 3.0, 3.5), det("S2", 4.0, 4.5), det("S3", 5.0, 5.5)]
        m = event_metrics(self.truths, weak, [Candidate(1, 5.5, weak)], 3, CFG)
        self.assertEqual((m["event_detected"], m["association_latency_s"], m["false_candidates"]), (False, None, 1))

    def test_fewer_stations_than_k_is_undefined(self):
        m = event_metrics(self.truths[:2], [], [], 3, CFG)
        self.assertIsNone(m["event_detected"])


class SeedSummaryTests(unittest.TestCase):
    def test_seed_level_scalars(self):
        stations = [
            {"detected": True, "sample_latency_s": 0.2, "emission_latency_s": 0.6, "completeness": 1.0,
             "false_triggers": 1, "scored_pre_event_s": 1800.0},
            {"detected": True, "sample_latency_s": 0.4, "emission_latency_s": 1.0, "completeness": 0.8,
             "false_triggers": 0, "scored_pre_event_s": 1800.0},
            {"detected": False, "sample_latency_s": None, "emission_latency_s": None, "completeness": 0.6,
             "false_triggers": 0, "scored_pre_event_s": 0.0},
        ]  # fmt: skip
        event = {"event_detected": True, "association_latency_s": 2.0, "false_candidates": 0}
        s = seed_summary(stations, event)
        self.assertAlmostEqual(s["detection_fraction"], 2 / 3)
        self.assertAlmostEqual(s["median_sample_latency_s"], 0.3)
        self.assertAlmostEqual(s["median_emission_latency_s"], 0.8)
        self.assertAlmostEqual(s["mean_completeness"], 0.8)
        self.assertEqual(s["false_triggers"], 1)
        self.assertAlmostEqual(s["false_trigger_rate_per_station_hour"], 1.0)  # 1 false trigger / (3600 s = 1 h)
        self.assertEqual((s["event_detected"], s["association_latency_s"]), (1.0, 2.0))


class StatisticsTests(unittest.TestCase):
    def test_quantile_is_type_7(self):
        self.assertEqual(quantile([1, 2, 3, 4], 0.25), 1.75)
        self.assertEqual(quantile([1, 2, 3, 4], 0.5), 2.5)
        self.assertEqual(quantile([5], 0.9), 5)
        with self.assertRaises(ValueError):
            quantile([], 0.5)

    def test_distribution_counts_undefined_values(self):
        d = distribution([1.0, None, 3.0, 2.0])
        self.assertEqual(
            (d["n"], d["n_defined"], d["median"], d["q1"], d["q3"], d["min"], d["max"]), (4, 3, 2.0, 1.5, 2.5, 1.0, 3.0)
        )
        self.assertEqual(distribution([None])["median"], None)

    def test_float_means_use_exactly_rounded_sums(self):
        # built-in sum([0.1] * 10) is 0.9999999999999999 before Python 3.12 and 1.0 from 3.12; fsum is 1.0 on both
        self.assertEqual(distribution([0.1] * 10)["mean"], 0.1)
        stations = [{"detected": True, "sample_latency_s": 0.0, "emission_latency_s": 0.0, "completeness": 0.1,
                     "false_triggers": 0, "scored_pre_event_s": 0.1} for _ in range(10)]  # fmt: skip
        event = {"event_detected": None, "association_latency_s": None, "false_candidates": 0}
        self.assertEqual(seed_summary(stations, event)["mean_completeness"], 0.1)

    def test_wilson_known_values(self):
        lo, hi = wilson_interval(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)
        self.assertTrue(math.isnan(wilson_interval(0, 0)[0]))

    def test_paired_difference(self):
        r = paired_difference({1: 2.0, 2: 3.0, 3: None, 4: 5.0}, {1: 1.0, 2: 3.0, 3: 4.0, 4: 1.0})
        self.assertEqual((r["n_seeds"], r["n_paired"], r["n_undefined"]), (4, 3, 1))
        self.assertEqual((r["n_positive"], r["n_negative"], r["n_zero"]), (2, 0, 1))
        self.assertEqual(r["differences"]["median"], 1.0)  # diffs 1, 0, 4
        self.assertIsNone(r["bootstrap_ci95_median"])

    def test_bootstrap_is_seeded_and_inside_the_data_range(self):
        values = [0.1, 0.4, 0.2, 0.9, 0.3, 0.5]
        a = bootstrap_ci_median(values, seed=3)
        self.assertEqual(a, bootstrap_ci_median(values, seed=3))
        self.assertTrue(min(values) <= a[0] <= a[1] <= max(values))
        r = paired_difference({i: v for i, v in enumerate(values)}, {i: 0.0 for i in range(6)}, bootstrap_seed=3)
        self.assertEqual(r["bootstrap_ci95_median"], list(a))


if __name__ == "__main__":
    unittest.main()
