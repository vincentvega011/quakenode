"""SYNTHETIC network scenario generator."""

import math
import unittest

from quakenode.scenario import EventSpec, NetworkSpec, StationSpec, build_packets, generate_trace, p_arrival_time_s
from quakenode.scenario.synthetic_network import SYNTHETIC_LABEL

ST = (StationSpec("A", 3.0, 4.0), StationSpec("B", 0.0, -30.0))
SPEC = NetworkSpec(ST, EventSpec(origin_time_s=2.0, x_km=0.0, y_km=0.0, depth_km=0.0, amplitude=10.0),
                   duration_s=20.0, sample_rate_hz=20.0, packet_len_samples=10, velocity_km_s=5.0, noise_sigma=0.0,
                   baseline_counts=100.0, amplitude_ref_km=5.0, coda_decay_per_s=0.0, pulse_freq_hz=1.0)  # fmt: skip


class ScenarioTests(unittest.TestCase):
    def test_label(self):
        self.assertEqual(SYNTHETIC_LABEL, "SYNTHETIC")

    def test_p_arrival_is_origin_plus_distance_over_velocity(self):
        self.assertAlmostEqual(p_arrival_time_s(SPEC, ST[0]), 2.0 + 5.0 / 5.0)  # 3-4-5 triangle, v = 5 km/s
        self.assertAlmostEqual(p_arrival_time_s(SPEC, ST[1]), 2.0 + 30.0 / 5.0)

    def test_noise_free_signal_follows_the_formulas(self):
        trace = generate_trace(SPEC, ST[0], seed=1)
        self.assertEqual(len(trace), 400)
        self.assertEqual(trace[0], 100.0)  # baseline only before P (no noise)
        amp = 10.0 / (1.0 + 5.0 / 5.0)  # A(r) = amplitude / (1 + r/r0) = 5
        i = 80  # t = 4.0 s, tau = 1.0 s after P at 3.0 s
        self.assertAlmostEqual(trace[i], 100.0 + amp * math.sin(2 * math.pi * 1.0 * 1.0), places=9)
        i = 65  # tau = 0.25 s
        self.assertAlmostEqual(trace[i], 100.0 + amp * math.sin(2 * math.pi * 0.25), places=9)
        self.assertEqual(trace[59], 100.0)  # t = 2.95 s < P

    def test_seeded_noise_is_repeatable_and_differs_by_seed_and_station(self):
        noisy = NetworkSpec(ST, None, duration_s=5.0, sample_rate_hz=20.0, noise_sigma=2.0)
        a1, a2 = generate_trace(noisy, ST[0], 7), generate_trace(noisy, ST[0], 7)
        self.assertEqual(a1, a2)
        self.assertNotEqual(a1, generate_trace(noisy, ST[0], 8))
        self.assertNotEqual(a1, generate_trace(noisy, ST[1], 7))
        mean = sum(a1) / len(a1)
        self.assertAlmostEqual(mean, 800.0, delta=1.0)  # baseline 800, sigma 2, 100 samples

    def test_packets_share_timing_across_stations_and_cover_the_trace(self):
        packets = build_packets(SPEC, seed=1)
        self.assertEqual(len(packets), 2 * 40)
        a = [p for p in packets if p.station_id == "A"]
        b = [p for p in packets if p.station_id == "B"]
        self.assertEqual([p.ready_time_s for p in a], [p.ready_time_s for p in b])
        self.assertEqual(sum(len(p.samples) for p in a), 400)
        self.assertTrue(all(p.arrival_time_s == p.ready_time_s for p in packets))

    def test_no_event_means_no_p_time(self):
        noisy = NetworkSpec(ST, None)
        with self.assertRaises(ValueError):
            p_arrival_time_s(noisy, ST[0])


if __name__ == "__main__":
    unittest.main()
