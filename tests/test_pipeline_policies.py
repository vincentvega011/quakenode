"""Out-of-order policies, detector protocol/registry and the recursive STA/LTA. All signals are SYNTHETIC."""

import importlib.util
import unittest
from dataclasses import replace

from quakenode.replay import Packet, ReplayEngine, Trace
from quakenode.streaming import (
    DetectorConfigError,
    RecursiveStaLtaDetector,
    StaLtaRmsDetector,
    StreamDetector,
    StreamingPipeline,
    StreamOrderError,
    available_detectors,
    create_detector_factory,
    validate_params,
)

HAVE_OBSPY = importlib.util.find_spec("obspy") is not None
RATE = 10.0
BURST_AT = 48  # first sample of the burst (index), inside packet 4 (samples 40..49)


def signal(n=100, burst_at=BURST_AT):
    x = [0.1 if i % 2 == 0 else -0.1 for i in range(n)]
    for i in range(burst_at, burst_at + 10):
        x[i] += 5.0
    return x


def packets(n=100):
    return ReplayEngine.packetize(Trace("S", "SYN", RATE, tuple(signal(n))), 10)


def pipeline(policy="reject", max_wait=0.0):
    return StreamingPipeline(
        alpha=0.5,
        warmup_samples=0,
        sta_samples=2,
        lta_samples=6,
        threshold=3.0,
        order_policy=policy,
        max_wait_s=max_wait,
    )


def run(pks, **kw):
    engine = ReplayEngine()
    engine.schedule(pks)
    return pipeline(**kw).run(engine)


def delayed(pks, seq, by):
    return [replace(p, arrival_time_s=p.arrival_time_s + by) if p.sequence_number == seq else p for p in pks]


class InOrderTests(unittest.TestCase):
    def test_all_policies_agree_on_in_order_data(self):
        results = [run(packets(), policy=pol, max_wait=1.0) for pol in ("reject", "drop_late", "buffer")]
        for r in results:
            self.assertEqual(len(r.detections), 1)
            self.assertEqual(r.detections[0].trigger_sample_index, BURST_AT)
            self.assertEqual((r.gap_events, r.dropped), ([], []))
        self.assertEqual(results[0].detections, results[1].detections)
        self.assertEqual(results[0].detections, results[2].detections)


class RejectDropLateBufferTests(unittest.TestCase):
    def setUp(self):
        # packet 3 (samples 30..39) arrives 0.3 s after packet 4 (arrival = ready: 4.9 s)
        self.late = delayed(packets(), 3, 1.2)  # packet 3 ready 3.9 -> arrives 5.1; packet 4 arrives 4.9

    def test_reject_raises(self):
        with self.assertRaisesRegex(StreamOrderError, "duplicate or out of order"):
            run(self.late, policy="reject")

    def test_drop_late_declares_the_gap_and_drops_the_late_packet(self):
        r = run(self.late, policy="drop_late")
        self.assertEqual([(g.expected_index, g.received_index) for g in r.gap_events], [(30, 40)])
        self.assertEqual(r.gap_events[0].declared_time_s, r.gap_events[0].arrival_time_s)
        self.assertEqual([(d.sequence_number, d.reason) for d in r.dropped], [(3, "late_or_duplicate")])

    def test_buffer_reorders_without_a_gap_and_matches_the_in_order_run(self):
        in_order = run(packets(), policy="reject")
        r = run(self.late, policy="buffer", max_wait=1.0)
        self.assertEqual((r.gap_events, r.dropped), ([], []))
        values = lambda res: [(p.sequence_number, p.filtered, p.scorable) for p in res.processed]  # noqa: E731
        self.assertEqual(values(r), values(in_order))  # same filtered samples, processed in index order
        self.assertEqual([p.sequence_number for p in r.processed], list(range(10)))
        a, b = in_order.detections[0], r.detections[0]
        self.assertEqual(
            (a.trigger_sample_index, a.trigger_sample_time_s), (b.trigger_sample_index, b.trigger_sample_time_s)
        )

    def test_buffering_delays_emission_by_exactly_the_documented_amount(self):
        in_order = run(packets(), policy="reject").detections[0]
        r = run(self.late, policy="buffer", max_wait=1.0).detections[0]
        arrive3 = self.late[3].arrival_time_s
        arrive4 = self.late[4].arrival_time_s
        self.assertEqual(in_order.emission_time_s, in_order.arrival_time_s)  # no buffering: emission = own arrival
        self.assertEqual(r.arrival_time_s, arrive4)  # the packet's own arrival is unchanged
        self.assertEqual(r.emission_time_s, arrive3)  # processed when the missing packet 3 arrived
        self.assertAlmostEqual(r.emission_time_s - in_order.emission_time_s, arrive3 - arrive4)
        self.assertGreaterEqual(r.emission_time_s, r.arrival_time_s)

    def test_buffer_expiry_declares_the_gap_at_the_deadline(self):
        lost = [p for p in packets() if p.sequence_number != 3]  # packet 3 never arrives
        r = run(lost, policy="buffer", max_wait=1.5)
        arrive4 = lost[3].arrival_time_s  # packet 4 is the first held packet (index 3 in the list)
        deadline = arrive4 + 1.5
        self.assertEqual([(g.expected_index, g.received_index) for g in r.gap_events], [(30, 40)])
        self.assertEqual(r.gap_events[0].arrival_time_s, arrive4)
        self.assertEqual(r.gap_events[0].declared_time_s, deadline)
        det = r.detections[0]  # detector reset at index 40; 8 samples re-warm it; burst at 48 is detected
        self.assertEqual(det.trigger_sample_index, BURST_AT)
        self.assertEqual(det.emission_time_s, deadline)  # held packet processed at the deadline
        self.assertEqual(det.arrival_time_s, arrive4)

    def test_packet_arriving_after_its_gap_was_declared_is_dropped(self):
        very_late = delayed(packets(), 3, 6.0)  # arrives long after the 1 s wait
        r = run(very_late, policy="buffer", max_wait=1.0)
        self.assertEqual([(g.expected_index, g.received_index) for g in r.gap_events], [(30, 40)])
        self.assertEqual([d.sequence_number for d in r.dropped], [3])

    def test_duplicate_packets_follow_the_policy(self):
        dup = packets() + [replace(packets()[2], arrival_time_s=packets()[2].arrival_time_s + 0.05)]
        engine = ReplayEngine()
        engine.schedule(dup, allow_duplicates=True)
        with self.assertRaises(StreamOrderError):
            pipeline("reject").run(engine)
        for pol in ("drop_late", "buffer"):
            engine = ReplayEngine()
            engine.schedule(dup, allow_duplicates=True)
            r = pipeline(pol, 1.0).run(engine)
            self.assertEqual(len(r.dropped), 1)
            self.assertEqual(len(r.processed), 10)

    def test_invalid_policy_configuration(self):
        for kw in ({"order_policy": "nope"}, {"order_policy": "buffer", "max_wait_s": 0.0}, {"max_wait_s": -1.0}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                StreamingPipeline(alpha=0.5, warmup_samples=0, sta_samples=2, lta_samples=6, threshold=3.0, **kw)


class RecursiveStaLtaTests(unittest.TestCase):
    def packet(self, samples, start=0, arrival=None):
        ready = (start + len(samples) - 1) / RATE
        return Packet(
            "S", "SYN", 0, RATE, start, start / RATE, tuple(samples), ready, ready if arrival is None else arrival
        )

    def test_hand_computed_toy_recursion(self):
        # nsta=2, nlta=4, no baseline filter. a^2 = [1,1,1,1,1,1,9]; csta=1/2, clta=1/4; sample 0 is not folded in.
        # i=1..5: sta -> .5, .75, .875, .9375, .96875 ; lta -> .25, .4375, .578125, .68359375, .7626953125
        # i=6 (x^2 = 9): sta = .5*9 + .5*.96875 = 4.984375, lta = .25*9 + .75*.7626953125 = 2.822021484375
        det = RecursiveStaLtaDetector(
            nsta=2, nlta=4, threshold_on=1.5, threshold_off=1.0, rearm=True, sample_rate_hz=RATE
        )
        found = det.process(self.packet([1, 1, 1, 1, 1, 1, 3]))
        self.assertEqual(det.last_ratios[:4], (0.0, 0.0, 0.0, 0.0))  # zeroed for the first nlta samples
        self.assertAlmostEqual(det.last_ratios[4], 0.9375 / 0.68359375)  # 1.3714...
        self.assertAlmostEqual(det.last_ratios[5], 0.96875 / 0.7626953125)
        self.assertAlmostEqual(det.last_ratios[6], 4.984375 / 2.822021484375)
        self.assertEqual(
            [d.trigger_sample_index for d in found], [6]
        )  # first ratio >= 1.5 (the earlier ones are < 1.5)
        self.assertAlmostEqual(found[0].ratio, 4.984375 / 2.822021484375)
        self.assertEqual(det.warmup_s, 0.4)

    def test_rearm_and_first_trigger_only(self):
        quiet = [0.1, -0.1] * 10
        burst = [5.0, -5.0] * 3
        x = quiet + burst + quiet + quiet + burst + quiet
        for rearm, expected in ((True, 2), (False, 1)):
            det = RecursiveStaLtaDetector(
                nsta=2, nlta=10, threshold_on=3.0, threshold_off=1.2, rearm=rearm, sample_rate_hz=RATE
            )
            found = det.process(self.packet(x))
            self.assertEqual(len(found), expected, rearm)

    def test_chunking_does_not_change_ratios_and_reset_rewarms(self):
        x = signal(100)
        whole = RecursiveStaLtaDetector(nsta=2, nlta=6, threshold_on=3.0, threshold_off=1.5, sample_rate_hz=RATE)
        whole.process(self.packet(x))
        parts = RecursiveStaLtaDetector(nsta=2, nlta=6, threshold_on=3.0, threshold_off=1.5, sample_rate_hz=RATE)
        ratios = []
        for s in range(0, 100, 7):
            parts.process(self.packet(x[s : s + 7], start=s))
            ratios += parts.last_ratios
        self.assertEqual(tuple(ratios), whole.last_ratios)
        parts.reset()
        self.assertTrue(parts.warming_up)

    @unittest.skipUnless(HAVE_OBSPY, "obspy not installed (extra `data`)")
    def test_matches_obspy_recursive_sta_lta(self):
        import numpy as np
        from obspy.signal.trigger import recursive_sta_lta_py

        rng = np.random.default_rng(0)
        x = rng.normal(size=400)
        x[200:230] *= 8.0
        reference = recursive_sta_lta_py(x, 5, 40)
        det = RecursiveStaLtaDetector(nsta=5, nlta=40, threshold_on=1e9, threshold_off=1e8, sample_rate_hz=RATE)
        ratios = []
        for s in range(0, 400, 33):
            det.process(self.packet([float(v) for v in x[s : s + 33]], start=s))
            ratios += det.last_ratios
        np.testing.assert_allclose(np.array(ratios), reference, rtol=1e-12, atol=1e-12)


class ProtocolRegistryTests(unittest.TestCase):
    def test_builtin_detectors_conform_and_are_registered(self):
        self.assertEqual(available_detectors(), ["recursive_sta_lta", "sta_lta_rms"])
        for name in available_detectors():
            det = create_detector_factory(name, {}, 0.0)("S", "SYN", 40.0)
            self.assertIsInstance(det, StreamDetector)
            self.assertGreater(det.warmup_s, 0.0)
            self.assertTrue(det.warming_up)
        self.assertIsInstance(
            StaLtaRmsDetector(alpha=0.5, warmup_samples=0, sta_samples=2, lta_samples=6, threshold=3.0), StreamDetector
        )

    def test_param_validation_names_the_problem(self):
        with self.assertRaisesRegex(DetectorConfigError, "unknown detector 'nope'"):
            validate_params("nope", {})
        with self.assertRaisesRegex(DetectorConfigError, r"unknown parameter\(s\) \['bogus'\]"):
            validate_params("sta_lta_rms", {"bogus": 1})
        with self.assertRaisesRegex(DetectorConfigError, "'threshold' must be > 0.0"):
            validate_params("sta_lta_rms", {"threshold": 0})
        with self.assertRaisesRegex(DetectorConfigError, "'rearm' must be true/false"):
            validate_params("recursive_sta_lta", {"rearm": 1})
        self.assertEqual(validate_params("sta_lta_rms", {"sta_s": 1})["sta_s"], 1.0)

    def test_custom_detector_plugs_into_the_pipeline(self):
        class EveryPacket:
            name, version, warmup_s = "every_packet", "0", 0.0
            warming_up = False

            def reset(self):
                pass

            def process(self, packet, processed_at_s=None):
                from quakenode.streaming.detectors import _detection

                at = packet.arrival_time_s if processed_at_s is None else processed_at_s
                return [_detection(packet, 0, processed_at_s=at, processing_delay_s=0.0, name=self.name, version="0",
                                   ratio=1.0, threshold=1.0, parameters=())]  # fmt: skip

        engine = ReplayEngine()
        engine.schedule(packets())
        pipe = StreamingPipeline(detector_factory=lambda s, c, r: EveryPacket()).run(engine)
        self.assertEqual(len(pipe.detections), 10)
        self.assertEqual(pipe.detections[0].detector_name, "every_packet")


if __name__ == "__main__":
    unittest.main()
