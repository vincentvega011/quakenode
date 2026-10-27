"""Whole-chain streaming contracts. Synthetic data only; these test software invariants."""

import unittest

from experiments.synthetic_causality import (
    CASES,
    CAUSAL_CUTOFF_HZ,
    DETECTOR_THRESHOLD,
    FS_HZ,
    LTA_SAMPLES,
    P_INDEX,
    STA_SAMPLES,
    causal_baseline,
    fixed_sta_lta_first_trigger,
    generate_signal,
)

from quakenode.preprocessing import one_pole_alpha
from quakenode.replay import Packet, ReplayEngine, Trace, with_fixed_delay
from quakenode.streaming import (
    StreamingOnePoleHighpass,
    StreamingPipeline,
    StreamingStaLta,
    StreamOrderError,
)

ALPHA = one_pole_alpha(CAUSAL_CUTOFF_HZ, FS_HZ)
EVENT = CASES[0]


def make_pipeline(warmup=0, delay=0.0):
    return StreamingPipeline(ALPHA, warmup, STA_SAMPLES, LTA_SAMPLES, DETECTOR_THRESHOLD, delay)


def trace_of(case, seed, station="STA1"):
    return Trace(station, "HHZ", FS_HZ, tuple(generate_signal(case, seed)))


def run(packets, warmup=0, delay=0.0, times=None):
    engine = ReplayEngine()
    engine.schedule(packets)
    return make_pipeline(warmup, delay).run(engine, times)


class EquivalenceTests(unittest.TestCase):
    def test_a_streaming_first_trigger_equals_batch_for_all_packet_sizes(self):
        for case in CASES:
            for seed in (202601, 202605, 202612):
                raw = generate_signal(case, seed)
                batch = fixed_sta_lta_first_trigger(causal_baseline(raw)[0])
                for size in (1, 7, 50, 100, 2000):
                    with self.subTest(case=case.name, seed=seed, size=size):
                        result = run(ReplayEngine.packetize(trace_of(case, seed), size))
                        got = [d.trigger_sample_index for d in result.detections]
                        self.assertEqual(got, [] if batch is None else [batch])
        # The event case must actually produce triggers, or the comparison is vacuous.
        self.assertIsNotNone(fixed_sta_lta_first_trigger(causal_baseline(generate_signal(EVENT, 202601))[0]))

    def test_streaming_filter_matches_batch_filter_bitwise(self):
        raw = generate_signal(EVENT, 202601)
        batch, _ = causal_baseline(raw)
        filt = StreamingOnePoleHighpass(ALPHA, 0)
        out = []
        for start in range(0, len(raw), 33):
            out.extend(filt.process(raw[start : start + 33])[0])
        self.assertEqual(out, batch)

    def test_h_hand_computed_sta_lta_fixture(self):
        # sta=2, lta=4, threshold=3. Window after 6 samples: lta=[1,1,1,1], sta=[3,3].
        # sta_rms = sqrt((9+9)/2) = 3, lta_rms = sqrt(4/4) = 1, ratio = 3 >= 3 -> trigger at index 5.
        det = StreamingStaLta(2, 4, 3.0)
        outs = [det.update(x) for x in (1.0, 1.0, 1.0, 1.0, 3.0, 3.0)]
        self.assertEqual([o.ratio for o in outs[:5]], [None] * 5)
        self.assertEqual(outs[5].ratio, 3.0)
        self.assertTrue(outs[5].triggered)
        self.assertEqual([o.triggered for o in outs[:5]], [False] * 5)
        # No re-arming: later large samples never trigger again.
        self.assertFalse(det.update(100.0).triggered)
        # Below threshold: sta=[2,2] -> ratio 2 < 3.
        det2 = StreamingStaLta(2, 4, 3.0)
        outs2 = [det2.update(x) for x in (1.0, 1.0, 1.0, 1.0, 2.0, 2.0)]
        self.assertEqual(outs2[5].ratio, 2.0)
        self.assertFalse(outs2[5].triggered)
        # Zero LTA: no ratio, no trigger.
        det3 = StreamingStaLta(2, 4, 3.0)
        self.assertEqual([det3.update(x).triggered for x in (0.0, 0.0, 0.0, 0.0, 5.0, 5.0)], [False] * 6)
        # Batch function agrees on the triggering fixture.
        from quakenode.detectors import rms_sta_lta_first_trigger

        self.assertEqual(rms_sta_lta_first_trigger([1.0, 1.0, 1.0, 1.0, 3.0, 3.0], 2, 4, 3.0), 5)


class CounterfactualTests(unittest.TestCase):
    def test_b_whole_chain_ignores_packets_arriving_after_cutoff(self):
        delay = 0.3
        for T, drop_seq in ((12.0, None), (12.0, 5), (5.0, None)):
            with self.subTest(T=T, drop=drop_seq):
                packets = ReplayEngine.packetize(trace_of(EVENT, 202601), 50, delay_s=delay)
                if drop_seq is not None:
                    packets = [p for p in packets if p.sequence_number != drop_seq]
                mutated = [
                    Packet(**{**p.__dict__, "samples": tuple(x + 1e3 for x in p.samples)})
                    if p.arrival_time_s > T
                    else p
                    for p in packets
                ]
                self.assertTrue(any(p.ready_time_s <= T < p.arrival_time_s for p in packets))
                a, b = run(packets, times=[T]), run(mutated, times=[T])
                self.assertEqual(a.detections, b.detections)
                self.assertEqual(a.gap_events, b.gap_events)
                self.assertEqual(a.processed, b.processed)
                self.assertGreater(len(a.processed), 0)
                if T > 8.0:
                    self.assertEqual(len(a.detections), 1)
                if drop_seq is not None:
                    self.assertEqual(len(a.gap_events), 1)
                # Running to the end, the mutated future does change the outputs.
                full_a, full_b = run(packets), run(mutated)
                self.assertNotEqual(full_a.processed, full_b.processed)


class ClockTests(unittest.TestCase):
    def test_c_fixed_delay_shifts_emission_only(self):
        base_packets = ReplayEngine.packetize(trace_of(EVENT, 202601), 50)
        base = run(base_packets).detections
        shifted = run(with_fixed_delay(base_packets, 0.25)).detections
        self.assertEqual(len(base), 1)
        self.assertEqual(len(shifted), 1)
        b, s = base[0], shifted[0]
        self.assertEqual(s.emission_time_s, b.emission_time_s + 0.25)
        self.assertEqual(s.arrival_time_s, b.arrival_time_s + 0.25)
        self.assertEqual(s.trigger_sample_index, b.trigger_sample_index)
        self.assertEqual(s.trigger_sample_time_s, b.trigger_sample_time_s)
        self.assertEqual(s.trigger_ready_time_s, b.trigger_ready_time_s)

    def test_d_emission_never_precedes_ready_or_arrival(self):
        seen = 0
        for seed in (202601, 202602, 202603):
            for size in (1, 10, 100):
                for proc in (0.0, 0.05):
                    for p_delay in (0.0, 0.4):
                        packets = ReplayEngine.packetize(trace_of(EVENT, seed), size, delay_s=p_delay)
                        for d in run(packets, delay=proc).detections:
                            seen += 1
                            self.assertGreaterEqual(d.emission_time_s, d.trigger_ready_time_s)
                            self.assertGreaterEqual(d.emission_time_s, d.arrival_time_s)
                            self.assertGreaterEqual(d.arrival_time_s, d.trigger_ready_time_s)
                            self.assertEqual(d.emission_time_s, d.arrival_time_s + proc)
                            self.assertEqual(d.processing_delay_s, proc)
                            self.assertEqual(d.trigger_sample_time_s, d.trigger_sample_index / FS_HZ)
        self.assertGreater(seen, 0)

    def test_detection_carries_detector_metadata(self):
        d = run(ReplayEngine.packetize(trace_of(EVENT, 202601), 100)).detections[0]
        self.assertEqual((d.detector_name, d.threshold), ("rms_sta_lta_first_trigger", DETECTOR_THRESHOLD))
        self.assertGreaterEqual(d.ratio, DETECTOR_THRESHOLD)
        self.assertIn(("sta_samples", STA_SAMPLES), d.parameters)
        self.assertGreaterEqual(d.trigger_sample_index, P_INDEX)


class WarmupTests(unittest.TestCase):
    def test_e_no_emission_before_warmup_ends(self):
        filt = StreamingOnePoleHighpass(ALPHA, 5)
        _, flags = filt.process([1.0] * 3)
        self.assertEqual(flags, [False] * 3)
        self.assertTrue(filt.warming_up)
        _, flags = filt.process([1.0] * 4)
        self.assertEqual(flags, [False, False, True, True])
        self.assertFalse(filt.warming_up)
        # Event case: warm-up covering the whole event suppresses every emission.
        packets = ReplayEngine.packetize(trace_of(EVENT, 202601), 50)
        self.assertEqual(len(run(packets, warmup=0).detections), 1)
        self.assertEqual(run(packets, warmup=1000).detections, [])
        # Warm-up ending inside the event: any emission is at or after the warm-up end.
        for w in (P_INDEX + 3, P_INDEX + 20):
            for d in run(packets, warmup=w).detections:
                self.assertGreaterEqual(d.trigger_sample_index, w)


class GapTests(unittest.TestCase):
    def packets(self, size=50):
        return ReplayEngine.packetize(trace_of(EVENT, 202601), size)

    def test_f_gap_before_p_resets_state_and_rewarms(self):
        pk = self.packets()
        nominal = run(pk, warmup=3).detections
        gapped_packets = [p for p in pk if p.sequence_number != 5]  # samples 250..299 missing
        result = run(gapped_packets, warmup=3)
        self.assertEqual([(g.expected_index, g.received_index) for g in result.gap_events], [(250, 300)])
        self.assertEqual(result.gap_events[0].arrival_time_s, pk[6].arrival_time_s)
        # No interpolation: the first processed packet after the gap starts at 300 and has the
        # filter's first-sample output 0.0 (state re-initialized), with warm-up flags restarted.
        after = next(p for p in result.processed if p.sequence_number == 6)
        self.assertEqual(after.filtered[0], 0.0)
        self.assertEqual(after.scorable[:4], (False, False, False, True))
        self.assertEqual(sum(len(p.filtered) for p in result.processed), 2000 - 50)
        # The detector re-warms (needs 110 samples) and still detects the later event.
        self.assertEqual(len(result.detections), 1)
        self.assertGreaterEqual(result.detections[0].trigger_sample_index, P_INDEX)
        self.assertEqual(len(nominal), 1)
        # Deterministic.
        again = run(gapped_packets, warmup=3)
        self.assertEqual((result.detections, result.gap_events, result.processed),
                         (again.detections, again.gap_events, again.processed))  # fmt: skip

    def test_gap_leaves_pipeline_rewarming_until_buffer_refills(self):
        pk = [p for p in self.packets(10) if p.sequence_number != 20]  # samples 200..209 missing
        engine = ReplayEngine()
        engine.schedule(pk)
        pipe = make_pipeline(warmup=0)
        pipe._feed_all(engine.advance_to(pk[20].arrival_time_s))  # through packet 21 (210..219)
        self.assertEqual(len(pipe.gap_events), 1)
        self.assertTrue(pipe.warming_up("STA1", "HHZ"))  # only 10 samples since the gap
        pipe._feed_all(engine.advance_to(10_000.0))
        self.assertFalse(pipe.warming_up("STA1", "HHZ"))

    def test_f_gap_spanning_p_can_cause_a_miss(self):
        pk = self.packets()
        self.assertEqual(len(run(pk).detections), 1)
        # P is sample 800 and the 0.8 s pulse covers 800..879. Dropping packets 16 and 17
        # (samples 800..899) removes the whole pulse: documented outcome is a MISS.
        no_pulse = run([p for p in pk if p.sequence_number not in (16, 17)])
        self.assertEqual([(g.expected_index, g.received_index) for g in no_pulse.gap_events], [(800, 900)])
        self.assertEqual(no_pulse.detections, [])
        # Dropping only packet 16 (800..849) also misses: the reset at 850 needs 110 more
        # samples to refill the detector, by which time the pulse (ends at 879) is over.
        onset_lost = run([p for p in pk if p.sequence_number != 16])
        self.assertEqual(len(onset_lost.gap_events), 1)
        self.assertEqual(onset_lost.detections, [])

    def test_gap_leaves_fired_detector_fired(self):
        pk = self.packets()
        result = run([p for p in pk if p.sequence_number != 30])  # gap at 1500..1549, after the pulse
        self.assertEqual(len(result.detections), 1)
        self.assertEqual(len(result.gap_events), 1)


class OrderingTests(unittest.TestCase):
    def test_g_out_of_order_packet_is_rejected(self):
        pk = ReplayEngine.packetize(trace_of(EVENT, 202601), 50)
        pk[3] = Packet(**{**pk[3].__dict__, "arrival_time_s": pk[4].arrival_time_s + 0.001})  # 3 arrives after 4
        engine = ReplayEngine()
        engine.schedule(pk)
        pipe = make_pipeline()
        with self.assertRaisesRegex(StreamOrderError, "duplicate or out of order"):
            pipe.run(engine)
        # Packet 4 had already been taken as a gap over the missing packet 3.
        self.assertEqual([(g.expected_index, g.received_index) for g in pipe.gap_events], [(150, 200)])

    def test_g_duplicate_data_is_rejected(self):
        pk = ReplayEngine.packetize(trace_of(EVENT, 202601), 50)
        pipe = make_pipeline()
        pipe.feed(pk[0])
        with self.assertRaises(StreamOrderError):
            pipe.feed(pk[0])
        # Same samples under a different sequence number, delivered through the engine.
        twin = Packet(**{**pk[1].__dict__, "sequence_number": 99})
        engine = ReplayEngine()
        engine.schedule([pk[1], twin])
        with self.assertRaises(StreamOrderError):
            make_pipeline().run(engine)

    def test_sample_rate_change_is_rejected(self):
        pk = ReplayEngine.packetize(trace_of(EVENT, 202601), 50)
        bad = Packet(**{**pk[1].__dict__, "sample_rate_hz": 200.0, "first_sample_time_s": 0.25, "ready_time_s": 0.745,
                        "arrival_time_s": 0.745})  # fmt: skip
        pipe = make_pipeline()
        pipe.feed(pk[0])
        with self.assertRaises(StreamOrderError):
            pipe.feed(bad)

    def test_run_with_explicit_times_only_delivers_up_to_last_time(self):
        pk = ReplayEngine.packetize(trace_of(EVENT, 202601), 100)
        engine = ReplayEngine()
        engine.schedule(pk)
        pipe = make_pipeline().run(engine, [3.0, 5.0])
        self.assertEqual(len(pipe.processed), 5)  # packets 0..4 ready at 0.99,...,4.99
        with self.assertRaises(ValueError):
            pipe.run(engine, [4.0])  # clock cannot go backwards


if __name__ == "__main__":
    unittest.main()
