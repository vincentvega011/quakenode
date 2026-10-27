"""Synthetic experiment JSON: results hash is stable across runs while the manifest is not."""

import unittest

from experiments.synthetic_causality import run_experiment, with_manifest


class ExperimentJsonTests(unittest.TestCase):
    def test_results_sha256_stable_across_runs(self):
        first = with_manifest(run_experiment())
        second = with_manifest(run_experiment())
        self.assertNotEqual(first["manifest"]["run_id"], second["manifest"]["run_id"])
        self.assertEqual(first["results_sha256"], second["results_sha256"])
        self.assertEqual(len(first["results_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
