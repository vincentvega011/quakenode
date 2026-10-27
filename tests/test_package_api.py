"""Input validation and public API checks for the quakenode package."""

import unittest

import quakenode
from quakenode.detectors import rms_sta_lta_first_trigger
from quakenode.preprocessing import causal_one_pole_highpass, chunked_one_pole_highpass, one_pole_alpha


class PackageApiTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(quakenode.__version__, "0.2.0")

    def test_invalid_filter_config_fails_loudly(self):
        with self.assertRaises(ValueError):
            causal_one_pole_highpass([1.0], alpha=1.0)
        with self.assertRaises(ValueError):
            one_pole_alpha(0.0, 100.0)
        with self.assertRaises(ValueError):
            chunked_one_pole_highpass([1.0, 2.0], [3], alpha=0.5)

    def test_invalid_detector_config_fails_loudly(self):
        with self.assertRaises(ValueError):
            rms_sta_lta_first_trigger([0.0] * 10, sta_samples=0, lta_samples=5, threshold=3.0)
        with self.assertRaises(ValueError):
            rms_sta_lta_first_trigger([0.0] * 10, sta_samples=2, lta_samples=5, threshold=0.0)

    def test_detector_trigger_is_causal_wrt_future_samples(self):
        quiet = [0.1, -0.1] * 20
        burst = quiet + [5.0] * 4
        changed_future = burst + [-50.0, 80.0, 0.0]
        first = rms_sta_lta_first_trigger(burst, 4, 20, 3.0)
        self.assertIsNotNone(first)
        self.assertEqual(first, rms_sta_lta_first_trigger(changed_future, 4, 20, 3.0))
        # Scanning only up to the trigger index must reproduce the decision.
        self.assertEqual(first, rms_sta_lta_first_trigger(changed_future, 4, 20, 3.0, stop_index=first))


if __name__ == "__main__":
    unittest.main()
