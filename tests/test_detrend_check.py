"""Pure-function tests for scripts/run_detrend_check.py. All arrays below are tiny SYNTHETIC examples."""

import math
import unittest

import numpy as np
from scripts.run_detrend_check import (
    EXCLUDED_CANDIDATES,
    VARIANTS,
    cast_int,
    draw_sample,
    is_approx,
    is_reproduced,
    linear_fit_subtract,
    mean_subtract,
    residual_stats,
    summarize_variant,
    variant_output,
    verdict,
    wilson_interval,
)


class TransformTests(unittest.TestCase):
    def test_linear_fit_subtract_exact_line_gives_zero(self):
        np.testing.assert_allclose(linear_fit_subtract([1, 3, 5, 7]), [0, 0, 0, 0], atol=1e-12)

    def test_linear_fit_subtract_hand_computed(self):
        # y = [1, 2, 4, 3], x = 0..3: slope = 4/5 = 0.8, intercept = 2.5 - 0.8*1.5 = 1.3,
        # fit = [1.3, 2.1, 2.9, 3.7], residual = [-0.3, -0.1, 1.1, -0.7].
        np.testing.assert_allclose(linear_fit_subtract([1, 2, 4, 3]), [-0.3, -0.1, 1.1, -0.7], atol=1e-12)

    def test_mean_subtract(self):
        np.testing.assert_allclose(mean_subtract([1, 2, 6]), [-2, -1, 3])

    def test_cast_modes_hand_computed(self):
        x = [-1.5, -0.5, 0.5, 1.5, 2.5, -2.5, 1.9, -1.9]
        self.assertEqual(cast_int(x, "rint").tolist(), [-2, 0, 0, 2, 2, -2, 2, -2])  # half to even
        self.assertEqual(cast_int(x, "trunc").tolist(), [-1, 0, 0, 1, 2, -2, 1, -1])
        self.assertEqual(cast_int(x, "floor").tolist(), [-2, -1, 0, 1, 2, -3, 1, -2])
        with self.assertRaises(ValueError):
            cast_int(x, "ceil")

    def test_variant_output_combines_transform_and_cast(self):
        w = np.array([1, 2, 4, 3])
        # T1 residual [-0.3, -0.1, 1.1, -0.7]: rint -> [0, 0, 1, -1], trunc -> [0, 0, 1, 0], floor -> [-1, -1, 1, -1]
        self.assertEqual(variant_output(w, "T1-rint").tolist(), [0, 0, 1, -1])
        self.assertEqual(variant_output(w, "T1-trunc").tolist(), [0, 0, 1, 0])
        self.assertEqual(variant_output(w, "T1-floor").tolist(), [-1, -1, 1, -1])
        # T2: mean 2.5 -> [-1.5, -0.5, 1.5, 0.5]: rint -> [-2, 0, 2, 0]
        self.assertEqual(variant_output(w, "T2-rint").tolist(), [-2, 0, 2, 0])
        self.assertEqual(len(VARIANTS), 6)

    def test_residual_stats(self):
        s = residual_stats([3, 0, -2], [3, 1, 0])
        self.assertEqual(s["max_abs"], 2)
        self.assertEqual(s["n_nonzero"], 2)
        self.assertAlmostEqual(s["rms"], math.sqrt((0 + 1 + 4) / 3))


class StatsTests(unittest.TestCase):
    def test_wilson_known_values(self):
        lo, hi = wilson_interval(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.2775, places=3)
        lo, hi = wilson_interval(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)
        lo, hi = wilson_interval(10, 10)
        self.assertAlmostEqual(lo, 0.7225, places=3)
        self.assertAlmostEqual(hi, 1.0)
        self.assertTrue(math.isnan(wilson_interval(0, 0)[0]))

    def test_criteria(self):
        self.assertTrue(is_reproduced({"max_abs": 1, "rms": 9}))
        self.assertFalse(is_reproduced({"max_abs": 2, "rms": 0.1}))
        self.assertTrue(is_approx({"max_abs": 2, "rms": 1.5}))
        self.assertFalse(is_approx({"max_abs": 3, "rms": 0.1}))
        self.assertFalse(is_approx({"max_abs": 2, "rms": 1.6}))

    def _rows(self, maxabs_by_variant, n=20):
        rows = []
        for i in range(n):
            row = {}
            for v in VARIANTS:
                m = maxabs_by_variant[v][i]
                row.update({f"{v}_max_abs": m, f"{v}_rms": float(m) / 2})
            rows.append(row)
        return rows

    def test_summarize_and_verdict(self):
        good = [0] * 19 + [3]  # 19 of 20 = 95% reproduce
        bad = [0] * 18 + [3, 3]  # 18 of 20 = 90%
        per = {v: bad for v in VARIANTS}
        per["T1-trunc"] = good
        rows = self._rows(per)
        pooled = {v: summarize_variant(rows, v) for v in VARIANTS}
        self.assertEqual(pooled["T1-trunc"]["reproduces_max_abs_le_1"]["k"], 19)
        self.assertEqual(pooled["T1-rint"]["reproduces_max_abs_le_1"]["k"], 18)
        v = verdict(pooled)
        self.assertEqual(v["variants_that_explain_the_release"], ["T1-trunc"])
        self.assertEqual(v["preferred_variant"], "T1-trunc")
        self.assertIn("reproduced transform T1-trunc", v["offline_arm_decision"])
        none = {v_: summarize_variant(self._rows({x: bad for x in VARIANTS}), v_) for v_ in VARIANTS}
        verdict_none = verdict(none)
        self.assertEqual(verdict_none["variants_that_explain_the_release"], [])
        self.assertIn("released HDF5 array itself", verdict_none["offline_arm_decision"])


class SampleTests(unittest.TestCase):
    NAMES = [f"{i}.IV.S{i:03d}..{fam}" for i in range(300) for fam in ("HH", "HN")] + ["9.MN.AAA..HH", "8.IV.ZZZ..EH"]

    def test_draw_is_deterministic_sorted_pool_and_excludes(self):
        a = draw_sample(self.NAMES, ("HH", "HN"), [], 1, 10)
        b = draw_sample(list(reversed(self.NAMES)), ("HH", "HN"), [], 1, 10)
        self.assertEqual(a, b)  # input order does not matter: the pool is sorted first
        for fam, names in a.items():
            self.assertEqual(len(names), 10)
            self.assertTrue(all(n.split(".")[1] == "IV" and n.endswith("." + fam) for n in names))
        c = draw_sample(self.NAMES, ("HH",), a["HH"], 1, 10)
        self.assertTrue(set(c["HH"]).isdisjoint(a["HH"]))
        with self.assertRaises(ValueError):
            draw_sample(self.NAMES, ("EH",), [], 1, 10)

    def test_previously_inspected_traces_are_listed(self):
        self.assertEqual(len(EXCLUDED_CANDIDATES), 11)


if __name__ == "__main__":
    unittest.main()
