"""`quakenode compare`: pairing with hand-computed expectations (fabricated, SYNTHETIC fixtures), mismatch, CLI."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from quakenode.cli import BANNER, main
from quakenode.compare import pair_arms, split_arm
from quakenode.config import ConfigError

DATA = {"source": "synthetic_network", "input_kind": "synthetic"}


def _st(sid, detected, lat=None, emit=None, unc=0.1):
    return {
        "station_id": sid, "detected": detected, "sample_latency_s": lat, "emission_latency_s": emit,
        "p_uncertainty_s": unc,
    }  # fmt: skip


def _arm(stations_by_seed, events_by_seed, seeds=(1, 2), kind="synthetic"):
    return {
        "seeds": list(seeds),
        "synthetic": True,
        "data": {**DATA, "input_kind": kind},
        "detector": "d",
        "gap_policy": "reset",
        "order_policy": "drop_late",
        "results_sha256": "x",
        "per_seed": {
            str(sd): {
                "stations": stations_by_seed[i],
                "event": {"association_latency_s": events_by_seed[i][0], "event_detected": events_by_seed[i][1]},
            }
            for i, sd in enumerate(seeds)
        },
    }


# Hand-built toy: stations X, Y, Z; seeds 1, 2.
#  X: both detected, latency A 1.0/1.2, B 1.5/1.4 -> diffs +0.5, +0.2 (emission diffs +0.5, +0.2)
#  Y: seed 1 only A detects, seed 2 neither
#  Z: seed 1 only B detects, seed 2 both: A 2.0 / B 2.25 -> diff +0.25
A = _arm(
    [
        [_st("X", True, 1.0, 1.5), _st("Y", True, 3.0, 3.5), _st("Z", False)],
        [_st("X", True, 1.2, 1.7), _st("Y", False), _st("Z", True, 2.0, 2.5)],
    ],
    [(1.0, True), (None, False)],
)
B = _arm(
    [
        [_st("X", True, 1.5, 2.0), _st("Y", False), _st("Z", True, 4.0, 4.5)],
        [_st("X", True, 1.4, 1.9), _st("Y", False), _st("Z", True, 2.25, 2.75)],
    ],
    [(1.5, True), (2.0, True)],
)


class PairArms(unittest.TestCase):
    def test_hand_computed_expectations(self):
        r = pair_arms(A, B)
        self.assertEqual(r["stations_paired"], ["X", "Y", "Z"])
        self.assertEqual(r["station_seed_pairs"], {"both": 3, "only_a": 1, "only_b": 1, "neither": 1, "undefined": 0})
        rows = {x["station_id"]: x for x in r["per_station"]}
        self.assertEqual((rows["X"]["both"], rows["X"]["median_sample_latency_diff_s"]), (2, 0.35))
        self.assertEqual((rows["Y"]["only_a"], rows["Y"]["neither"]), (1, 1))
        self.assertIsNone(rows["Y"]["median_sample_latency_diff_s"])
        self.assertEqual((rows["Z"]["only_b"], rows["Z"]["both"]), (1, 1))
        self.assertEqual(rows["Z"]["median_sample_latency_a_s"], 2.0)
        self.assertEqual(rows["Z"]["median_sample_latency_b_s"], 3.125)
        # pooled diffs: +0.5, +0.2, +0.25 -> median 0.25, n 3
        d = r["paired_sample_latency_diff_s"]
        self.assertEqual((d["n_defined"], d["median"]), (3, 0.25))
        self.assertEqual(r["paired_emission_latency_diff_s"]["median"], 0.25)
        ev = r["event"]["per_seed"]
        self.assertEqual(ev[0]["association_latency_diff_s"], 0.5)
        self.assertIsNone(ev[1]["association_latency_diff_s"])  # A did not detect the event in seed 2
        self.assertEqual(r["event"]["association_latency_diff_s"]["n_defined"], 1)

    def test_station_mismatch_is_reported_not_silent(self):
        b = _arm([[_st("X", True, 1.5, 2.0), _st("W", True, 1.0, 1.5)]] * 2, [(1.0, True)] * 2)
        r = pair_arms(A, b)
        self.assertEqual(r["stations_paired"], ["X"])
        self.assertEqual(r["stations_dropped_only_in_a"], ["Y", "Z"])
        self.assertEqual(r["stations_dropped_only_in_b"], ["W"])

    def test_dropped_lists_and_match_mode_can_be_supplied(self):
        r = pair_arms(A, B, ["Q"], [], "rerun_with_common_stations")
        self.assertEqual(r["stations_dropped_only_in_a"], ["Q"])
        self.assertEqual(r["station_match"], "rerun_with_common_stations")

    def test_no_common_station_fails(self):
        b = _arm([[_st("Q", True, 1.0, 1.5)]] * 2, [(1.0, True)] * 2)
        with self.assertRaises(ConfigError):
            pair_arms(A, b)

    def test_different_seeds_fail(self):
        with self.assertRaises(ConfigError):
            pair_arms(A, _arm(B_ST, [(1.0, True)] * 2, seeds=(1, 3)))

    def test_deterministic_and_carries_input_kind(self):
        a = _arm(B_ST, [(1.0, True)] * 2, kind="release_hdf5")
        r1, r2 = pair_arms(a, B), pair_arms(a, B)
        self.assertEqual(json.dumps(r1, sort_keys=True), json.dumps(r2, sort_keys=True))
        self.assertEqual((r1["arm_a"]["input_kind"], r1["arm_b"]["input_kind"]), ("release_hdf5", "synthetic"))


B_ST = [[_st("X", True, 1.0, 1.5)], [_st("X", True, 1.0, 1.5)]]


class SplitArm(unittest.TestCase):
    def test_top_level_commas_only(self):
        self.assertEqual(split_arm("a.b=1, c=[x,y],d='p,q'"), ["a.b=1", "c=[x,y]", "d='p,q'"])

    def test_empty_fails(self):
        with self.assertRaises(ConfigError):
            split_arm(" , ")


class CompareCli(unittest.TestCase):
    CONFIG = Path(__file__).resolve().parent.parent / "examples" / "synthetic_network" / "config.yaml"

    def _run(self, out_dir, *extra):
        out, err = io.StringIO(), io.StringIO()
        argv = ["compare", str(self.CONFIG), "--a", "pipeline.gap_policy=reset", "--b", "pipeline.gap_policy=hold"]
        with redirect_stdout(out), redirect_stderr(err):
            code = main([*argv, "--set", "seeds=[1,2]", "--out-dir", str(out_dir), *extra])
        return code, out.getvalue(), err.getvalue()

    def test_outputs_banner_labels_manifest_and_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            code, text, _ = self._run(d)
            code2, _, _ = self._run(d)
            self.assertEqual((code, code2), (0, 0))
            self.assertIn(BANNER, text)
            self.assertIn("SYNTHETIC", text)
            dirs = sorted(p for p in Path(d).iterdir() if p.is_dir())
            self.assertEqual(len(dirs), 2)  # unique, never overwritten
            for name in ("compare.md", "compare.csv", "compare.json", "manifest.json"):
                self.assertTrue((dirs[0] / name).exists(), name)
            j = [json.loads((p / "compare.json").read_text()) for p in dirs]
            self.assertEqual(j[0]["results_sha256"], j[1]["results_sha256"])
            cfg = j[0]["manifest"]["config"]
            self.assertEqual(cfg["arm_a_overrides"], ["pipeline.gap_policy=reset"])
            self.assertEqual(cfg["arm_b_overrides"], ["pipeline.gap_policy=hold"])
            self.assertEqual(j[0]["arm_b"]["gap_policy"], "hold")

    def test_invalid_override_fails_loudly(self):
        with tempfile.TemporaryDirectory() as d:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["compare", str(self.CONFIG), "--a", "pipeline.gap_policy=nope", "--b", "seeds=[1]",
                             "--out-dir", d])  # fmt: skip
            self.assertEqual(code, 2)
            self.assertEqual(list(Path(d).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
