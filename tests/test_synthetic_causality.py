"""Focused contracts for the synthetic causality proof of concept."""

import unittest

from experiments.synthetic_causality import (
    CASES,
    PREFIX_CUTOFF_INDEX,
    SEEDS,
    _first_prefix_trigger,
    causal_baseline,
    causal_baseline_chunked,
    fixed_sta_lta_first_trigger,
    future_perturbation,
    generate_signal,
    offline_linear_detrend,
    offline_mean_remove,
)


class SyntheticCausalityTests(unittest.TestCase):
    def test_future_changes_affect_offline_prefix_but_not_causal_prefix_or_decision(self):
        case = CASES[0]
        raw = generate_signal(case, SEEDS[0])
        changed = future_perturbation(raw, PREFIX_CUTOFF_INDEX)
        prefix = slice(0, PREFIX_CUTOFF_INDEX)

        self.assertEqual(raw[prefix], changed[prefix])
        self.assertGreater(
            max(abs(a - b) for a, b in zip(offline_mean_remove(raw)[prefix], offline_mean_remove(changed)[prefix])), 0.0
        )
        self.assertGreater(
            max(
                abs(a - b) for a, b in zip(offline_linear_detrend(raw)[prefix], offline_linear_detrend(changed)[prefix])
            ),
            0.0,
        )

        causal, _ = causal_baseline(raw)
        causal_changed, _ = causal_baseline(changed)
        self.assertEqual(causal[prefix], causal_changed[prefix])
        self.assertEqual(_first_prefix_trigger(causal), _first_prefix_trigger(causal_changed))

    def test_causal_filter_chunk_boundaries_preserve_samples_and_final_state(self):
        samples = [0.1, -0.2, 0.8, 0.5, -0.4, 1.2, 0.0, -0.6, 0.3] * 19
        whole, whole_state = causal_baseline(samples)
        chunked = causal_baseline_chunked(samples, [1, 13, 0, 27, 2, 44, 9])
        self.assertEqual(whole, chunked)
        self.assertEqual(whole_state, causal_baseline(samples)[1])

    def test_filter_initializes_baseline_from_first_observed_sample(self):
        output, state = causal_baseline([4.25])
        self.assertEqual(output, [0.0])
        self.assertEqual(state, 4.25)

    def test_empty_chunk_does_not_reset_carried_filter_state(self):
        first, state = causal_baseline([1.0, 1.5])
        empty, state_after_empty = causal_baseline([], state)
        tail, _ = causal_baseline([2.0, 2.5], state_after_empty)
        whole, _ = causal_baseline([1.0, 1.5, 2.0, 2.5])
        self.assertEqual(empty, [])
        self.assertEqual(first + tail, whole)

    def test_fixed_detector_has_no_triggers_in_control_cases_for_all_seeds(self):
        controls = [case for case in CASES if not case.has_event]
        for case in controls:
            for seed in SEEDS:
                self.assertIsNone(fixed_sta_lta_first_trigger(generate_signal(case, seed)))


if __name__ == "__main__":
    unittest.main()
