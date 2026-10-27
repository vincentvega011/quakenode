"""Synthetic contract tests; this filter is not a validated seismic recipe."""

import unittest

from quakenode.preprocessing import causal_one_pole_highpass


def process_one_pole_highpass(samples, alpha, baseline=None):
    """Process a chunk causally, returning its output and carried state."""
    return causal_one_pole_highpass(samples, alpha, baseline)


class StreamingPreprocessingContractTests(unittest.TestCase):
    def test_future_sample_changes_do_not_change_earlier_outputs(self):
        alpha = 0.91  # synthetic test value only; not a study parameter
        prefix = [0.0, 0.4, -0.2, 1.1, 0.3, -0.7, 0.8]
        original = prefix + [0.1, -0.4, 0.2, 0.5]
        perturbed = prefix + [40.0, -60.0, 20.0, -10.0]

        original_output, _ = process_one_pole_highpass(original, alpha)
        perturbed_output, _ = process_one_pole_highpass(perturbed, alpha)

        self.assertEqual(original_output[: len(prefix)], perturbed_output[: len(prefix)])

    def test_chunk_boundaries_preserve_outputs_and_final_state(self):
        alpha = 0.91  # synthetic test value only; not a study parameter
        samples = [0.1, -0.2, 0.8, 0.5, -0.4, 1.2, 0.0, -0.6, 0.3]
        whole, whole_state = process_one_pole_highpass(samples, alpha)

        chunked = []
        state = None
        for start, end in [(0, 1), (1, 4), (4, 4), (4, 7), (7, 9)]:
            output, state = process_one_pole_highpass(samples[start:end], alpha, state)
            chunked.extend(output)

        self.assertEqual(whole, chunked)
        self.assertEqual(whole_state, state)


if __name__ == "__main__":
    unittest.main()
