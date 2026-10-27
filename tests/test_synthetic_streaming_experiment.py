"""Smoke contracts for the synthetic streaming experiment (software invariants only)."""

import unittest

from experiments.synthetic_streaming import run_experiment, with_manifest


class SyntheticStreamingExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first = with_manifest(run_experiment())
        cls.second = with_manifest(run_experiment())

    def test_results_hash_stable_and_manifest_differs(self):
        self.assertEqual(self.first["results_sha256"], self.second["results_sha256"])
        self.assertNotEqual(self.first["manifest"]["run_id"], self.second["manifest"]["run_id"])

    def test_nominal_streaming_agrees_with_batch_at_every_packet_size(self):
        nominal = [r for r in self.first["results"].values() if r["scenario"] == "nominal"]
        self.assertEqual(len(nominal), 12)
        for r in nominal:
            self.assertEqual(r["first_trigger_agrees_with_batch"], r["n_seeds"])

    def test_dropped_packet_scenario_really_drops_one_packet_per_trace(self):
        dropped = [r for r in self.first["results"].values() if r["scenario"] == "dropped_packet_before_p"]
        for r in dropped:
            self.assertTrue(all(row["gap_events"] == 1 for row in r["per_seed"]))
        nominal = [r for r in self.first["results"].values() if r["scenario"] == "nominal"]
        self.assertTrue(all(row["gap_events"] == 0 for r in nominal for row in r["per_seed"]))

    def test_fixed_delay_scenario_adds_exactly_the_delay_to_latency(self):
        res = self.first["results"]
        for key, r in res.items():
            if r["scenario"] != "fixed_delay":
                continue
            base = res[key.replace("fixed_delay", "nominal")]
            for a, b in zip(base["per_seed"], r["per_seed"], strict=True):
                self.assertEqual(a["first_trigger_index"], b["first_trigger_index"])
                if a["emission_latency_s_from_p"] is not None:
                    self.assertAlmostEqual(
                        b["emission_latency_s_from_p"] - a["emission_latency_s_from_p"], 0.5, places=6
                    )


if __name__ == "__main__":
    unittest.main()
