"""Replay core contracts. Synthetic data only; these test software invariants, not seismology."""

import math
import unittest

from quakenode.replay import (
    Detection,
    Packet,
    ReplayEngine,
    Trace,
    UndeliveredPacketError,
    VirtualClock,
    with_fixed_delay,
)

RATE = 100.0


def make_trace(station="STA1", n=1000, offset=0.0):
    return Trace(station, "HHZ", RATE, tuple(math.sin(0.01 * i) + offset for i in range(n)))


class PacketTests(unittest.TestCase):
    def _kwargs(self, **over):
        base = dict(
            station_id="S", channel_id="Z", sequence_number=0, sample_rate_hz=100.0, first_sample_index=10,
            first_sample_time_s=0.1, samples=[1.0, 2.0, 3.0], ready_time_s=0.12, arrival_time_s=0.2,
        )  # fmt: skip
        return {**base, **over}

    def test_valid_packet_samples_are_immutable_tuple(self):
        p = Packet(**self._kwargs())
        self.assertIsInstance(p.samples, tuple)
        with self.assertRaises(AttributeError):
            p.arrival_time_s = 0.0  # frozen

    def test_invalid_packets_rejected(self):
        for over in (
            {"arrival_time_s": 0.11},  # before ready
            {"ready_time_s": 0.11},  # before last sample time
            {"first_sample_time_s": 0.5},  # inconsistent with index and rate
            {"samples": []},
            {"sample_rate_hz": 0.0},
            {"samples": [float("nan")]},
        ):
            with self.subTest(over=over), self.assertRaises(ValueError):
                Packet(**self._kwargs(**over))


class ReplayTests(unittest.TestCase):
    def engine_with(self, packets):
        engine = ReplayEngine()
        engine.schedule(packets)
        return engine

    def test_a_no_delivered_packet_arrives_after_clock(self):
        packets = ReplayEngine.packetize(make_trace(), 37, delay_s=0.25)
        engine = self.engine_with(packets)
        for t in (0.0, 0.5, 1.7, 3.3, 5.0, 20.0):
            for p in engine.advance_to(t):
                self.assertLessEqual(p.arrival_time_s, t)
            self.assertTrue(all(p.arrival_time_s <= t for p in engine.receiver.delivered_packets()))
        self.assertEqual(len(engine.receiver.delivered_packets()), len(packets))

    def test_b_mutating_future_packets_leaves_seen_data_bit_identical(self):
        T = 4.0
        delay = 0.5
        packets = ReplayEngine.packetize(make_trace(), 25, delay_s=delay)
        # Includes packets whose data are ready before T but arrive after T.
        mutated = [
            Packet(**{**p.__dict__, "samples": tuple(x + 1e3 for x in p.samples)}) if p.arrival_time_s > T else p
            for p in packets
        ]
        self.assertTrue(any(p.ready_time_s <= T < p.arrival_time_s for p in packets))
        self.assertNotEqual(packets, mutated)
        e1, e2 = self.engine_with(packets), self.engine_with(mutated)
        self.assertEqual(e1.advance_to(T), e2.advance_to(T))
        self.assertEqual(e1.receiver.delivered_packets(), e2.receiver.delivered_packets())
        self.assertEqual(e1.receiver.contiguous_samples("STA1", "HHZ"), e2.receiver.contiguous_samples("STA1", "HHZ"))
        self.assertNotEqual(e1.advance_to(100.0), e2.advance_to(100.0))  # the future does differ

    def test_c_fixed_delay_shifts_arrival_only(self):
        base = ReplayEngine.packetize(make_trace(), 50)
        delayed = with_fixed_delay(base, 0.25)
        for a, b in zip(base, delayed, strict=True):
            self.assertEqual(b.arrival_time_s, a.arrival_time_s + 0.25)
            self.assertEqual(b.ready_time_s, a.ready_time_s)
            self.assertEqual(b.first_sample_time_s, a.first_sample_time_s)
            self.assertEqual(b.samples, a.samples)

    def test_d_packet_size_does_not_change_sample_timestamps(self):
        def stamps(size):
            return [
                p.sample_time_s(k)
                for p in ReplayEngine.packetize(make_trace(n=500), size)
                for k in range(len(p.samples))
            ]

        reference = stamps(1)
        self.assertEqual(reference, [i / RATE for i in range(500)])
        for size in (7, 50, 64, 500):
            self.assertEqual(stamps(size), reference)

    def test_e_delivery_order_is_deterministic_with_ties(self):
        def run():
            engine = ReplayEngine()
            # Two stations, identical timing: ties broken by sequence number, then station id.
            engine.schedule(ReplayEngine.packetize(make_trace("B"), 100))
            engine.schedule(ReplayEngine.packetize(make_trace("A"), 100))
            return [p.key for p in engine.advance_to(100.0)]

        first = run()
        self.assertEqual(first, run())
        self.assertEqual(first[:4], [("A", "HHZ", 0), ("B", "HHZ", 0), ("A", "HHZ", 1), ("B", "HHZ", 1)])

    def test_f_clock_cannot_go_backwards(self):
        engine = self.engine_with(ReplayEngine.packetize(make_trace(), 100))
        engine.advance_to(3.0)
        engine.advance_to(3.0)  # same time is fine
        with self.assertRaises(ValueError):
            engine.advance_to(2.9)
        with self.assertRaises(ValueError):
            VirtualClock(5.0).advance_to(4.0)

    def test_g_undelivered_packet_is_inaccessible_through_receiver(self):
        engine = self.engine_with(ReplayEngine.packetize(make_trace(), 100))
        engine.advance_to(1.0)  # packet 0 (ready 0.99) delivered; packet 1 (ready 1.99) not
        self.assertEqual(engine.receiver.get_packet("STA1", "HHZ", 0).sequence_number, 0)
        with self.assertRaises(UndeliveredPacketError):
            engine.receiver.get_packet("STA1", "HHZ", 1)
        self.assertEqual(len(engine.receiver.contiguous_samples("STA1", "HHZ")), 100)
        self.assertFalse(hasattr(engine.receiver, "_queue"))

    def test_late_scheduling_and_duplicates_rejected(self):
        packets = ReplayEngine.packetize(make_trace(), 100)
        engine = self.engine_with(packets)
        with self.assertRaises(ValueError):
            engine.schedule(packets[:1])  # duplicate
        engine.advance_to(5.0)
        with self.assertRaises(ValueError):
            engine.schedule(ReplayEngine.packetize(make_trace("X"), 100))  # arrives before clock

    def test_out_of_order_arrival_keeps_contiguous_prefix_only(self):
        packets = ReplayEngine.packetize(make_trace(n=300), 100)
        packets[0] = Packet(**{**packets[0].__dict__, "arrival_time_s": 10.0})  # first packet very late
        engine = self.engine_with(packets)
        engine.advance_to(5.0)
        self.assertEqual(len(engine.receiver.delivered_packets()), 2)
        self.assertEqual(engine.receiver.contiguous_samples("STA1", "HHZ"), ())
        engine.advance_to(10.0)
        self.assertEqual(len(engine.receiver.contiguous_samples("STA1", "HHZ")), 300)

    def test_detection_keeps_clocks_separate(self):
        d = Detection("S", "Z", 100, 1.0, 1.0, 1.2, 1.25, 0.05, "det", "v", 3.5, 3.0, (("a", 1),))
        self.assertEqual((d.trigger_sample_time_s, d.arrival_time_s, d.emission_time_s), (1.0, 1.2, 1.25))


if __name__ == "__main__":
    unittest.main()
