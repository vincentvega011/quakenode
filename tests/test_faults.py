"""Fault injection: determinism (exact pinned patterns), records, semantics. Packets are SYNTHETIC."""

import random
import unittest

from quakenode.faults import (
    ClockOffset,
    Duplicate,
    FixedDelay,
    Jitter,
    MissingSamples,
    PacketLoss,
    Reorder,
    Selection,
    StationOutage,
    Stream,
    apply_faults,
    derive_seed,
)
from quakenode.replay import ReplayEngine, Trace


def packets_for(station, n=40):
    return ReplayEngine.packetize(Trace(station, "SYN", 10.0, tuple(float(i) for i in range(n * 10))), 10)


PACKETS = packets_for("A") + packets_for("B")


def names(keys):
    return [f"{k[0]}{k[2]}" for k in keys]


class RngTests(unittest.TestCase):
    def test_streams_are_pinned(self):
        # random.Random(42).random() is documented-stable; these values must never change.
        s = Stream(42)
        self.assertEqual(
            [s.uniform() for _ in range(3)], [0.6394267984578837, 0.025010755222666936, 0.27502931836911926]
        )
        self.assertEqual(Stream(42).normal(), 1.4107277054437621)
        self.assertEqual(Stream(42).exponential(2.0), 2.040120574549602)
        self.assertEqual(derive_seed(7, "fault", 0, "packet_loss"), 6053055168494029983)

    def test_stream_matches_stdlib_random(self):
        self.assertEqual(Stream(5).uniform(), random.Random(5).random())


class LossTests(unittest.TestCase):
    def test_bernoulli_pattern_is_pinned_and_repeatable(self):
        out, rec = PacketLoss("bernoulli", 0.3).apply(PACKETS, 123)
        again, rec2 = PacketLoss("bernoulli", 0.3).apply(PACKETS, 123)
        self.assertEqual((len(out), rec.packets_affected), (55, 25))
        self.assertEqual(names(rec.affected)[:12],
                         ["A0", "A1", "A3", "A5", "A9", "A12", "A13", "A15", "A17", "A21", "A22", "A24"])  # fmt: skip
        self.assertEqual([p.key for p in out], [p.key for p in again])
        self.assertEqual(rec, rec2)

    def test_record_matches_what_happened(self):
        out, rec = PacketLoss("bernoulli", 0.3).apply(PACKETS, 123)
        removed = {p.key for p in PACKETS} - {p.key for p in out}
        self.assertEqual(set(rec.affected), removed)
        self.assertEqual((rec.type, rec.seed, rec.targets, rec.status), ("packet_loss", 123, "all", "applied"))
        self.assertEqual(rec.packets_considered, 80)
        self.assertEqual(rec.parameters["p"], 0.3)

    def test_pattern_does_not_depend_on_input_order(self):
        shuffled = list(PACKETS)
        random.Random(1).shuffle(shuffled)
        a, _ = PacketLoss("bernoulli", 0.3).apply(PACKETS, 9)
        b, _ = PacketLoss("bernoulli", 0.3).apply(shuffled, 9)
        self.assertEqual({p.key for p in a}, {p.key for p in b})

    def test_zero_probability_is_skipped_not_applied(self):
        out, rec = PacketLoss("bernoulli", 0.0).apply(PACKETS, 1)
        self.assertEqual((len(out), rec.status, rec.packets_affected), (80, "skipped", 0))
        self.assertIn("no packet was affected", rec.note)

    def test_gilbert_elliott_pinned(self):
        out, rec = PacketLoss("gilbert_elliott", p_gb=0.1, p_bg=0.4).apply(PACKETS, 123)
        self.assertEqual((len(out), rec.packets_affected), (65, 15))
        self.assertEqual(names(rec.affected)[:12],
                         ["A1", "A3", "A7", "A9", "A10", "A24", "A31", "B16", "B24", "B25", "B26", "B27"])  # fmt: skip

    def test_gilbert_elliott_burst_logic_without_randomness(self):
        # p_gb=1: the chain enters the bad state after the first packet; p_bg=0: it never leaves. loss_bad=1.
        out, rec = PacketLoss("gilbert_elliott", p_gb=1.0, p_bg=1e-12).apply(PACKETS, 3)
        kept = {p.key for p in out}
        self.assertEqual(kept, {("A", "SYN", 0), ("B", "SYN", 0)})  # per-station chains start in the good state
        self.assertEqual(rec.packets_affected, 78)

    def test_target_and_interval_selection(self):
        # packet i of a station is ready at (10*i + 9)/10 s; interval [5, 10) selects i = 5..9 (ready 5.9 ... 9.9)
        sel = Selection(targets=("A",), start_s=5.0, end_s=10.0)
        out, rec = PacketLoss("bernoulli", 1.0, selection=sel).apply(PACKETS, 1)
        self.assertEqual(names(rec.affected), [f"A{i}" for i in range(5, 10)])
        self.assertEqual(rec.packets_considered, 5)
        self.assertEqual(rec.targets, ("A",))
        self.assertEqual(len(out), 75)


class DelayJitterTests(unittest.TestCase):
    def test_fixed_delay_shifts_arrival_only(self):
        out, rec = FixedDelay(0.25).apply(PACKETS, 1)
        for a, b in zip(PACKETS, out, strict=True):
            self.assertEqual(b.arrival_time_s, a.arrival_time_s + 0.25)
            self.assertEqual(
                (b.ready_time_s, b.first_sample_time_s, b.samples), (a.ready_time_s, a.first_sample_time_s, a.samples)
            )
        self.assertEqual(rec.packets_affected, 80)

    def test_jitter_pinned_and_bounded(self):
        out, rec = Jitter("uniform", low_s=0.0, high_s=0.5).apply(PACKETS, 5)
        deltas = [round(p.arrival_time_s - q.arrival_time_s, 6) for p, q in zip(out[:3], PACKETS[:3], strict=True)]
        self.assertEqual(deltas, [0.311451, 0.370893, 0.397597])
        self.assertTrue(
            all(0.0 <= p.arrival_time_s - q.arrival_time_s <= 0.5 for p, q in zip(out, PACKETS, strict=True))
        )
        out, _ = Jitter("exponential", mean_s=0.2).apply(PACKETS, 5)
        deltas = [round(p.arrival_time_s - q.arrival_time_s, 6) for p, q in zip(out[:3], PACKETS[:3], strict=True)]
        self.assertEqual(deltas, [0.19505, 0.270794, 0.317138])
        self.assertTrue(all(p.arrival_time_s >= p.ready_time_s for p in out))


class StructuralFaultTests(unittest.TestCase):
    def test_duplicate_adds_copies_the_engine_can_deliver(self):
        out, rec = Duplicate(0.2, 0.05).apply(PACKETS, 123)
        self.assertEqual((len(out), rec.packets_affected), (100, 20))
        copies = out[80:]
        self.assertEqual({c.key for c in copies}, set(rec.affected))
        for c in copies:
            original = next(p for p in PACKETS if p.key == c.key)
            self.assertEqual(c.arrival_time_s, original.arrival_time_s + 0.05)
            self.assertEqual(c.samples, original.samples)
        engine = ReplayEngine()
        with self.assertRaises(ValueError):
            engine.schedule(out)  # duplicates rejected by default
        engine = ReplayEngine()
        engine.schedule(out, allow_duplicates=True)
        self.assertEqual(len(engine.advance_to(1000.0)), 100)
        self.assertEqual(len(engine.receiver.delivered_packets()), 80)  # receiver keeps the first copy of each key

    def test_reorder_rule_makes_held_packets_arrive_after_later_ones(self):
        out, rec = Reorder(0.2, 2.0).apply(PACKETS, 123)
        self.assertEqual(rec.packets_affected, 20)
        held = {k for k in rec.affected}
        for p, q in zip(out, PACKETS, strict=True):
            self.assertEqual(p.arrival_time_s, q.arrival_time_s + 2.0 if p.key in held else q.arrival_time_s)
        self.assertIn("arrive after a later packet", rec.note)
        # packets are 1 s long, so a 2 s hold lets later packets of the stream overtake a held one
        engine = ReplayEngine()
        engine.schedule(out)
        order = [p.key for p in engine.advance_to(1000.0) if p.station_id == "A"]
        self.assertNotEqual(order, sorted(order))

    def test_outage_drops_everything_in_the_interval(self):
        sel = Selection(targets=("B",), start_s=10.0, end_s=20.0)
        out, rec = StationOutage(sel).apply(PACKETS, 1)
        self.assertEqual(names(rec.affected), [f"B{i}" for i in range(10, 20)])
        self.assertEqual(len(out), 70)
        self.assertEqual(rec.parameters, {})

    def test_clock_offset_reports_shifted_time_and_keeps_true_time(self):
        out, rec = ClockOffset(-1.5, Selection(targets=("A",))).apply(PACKETS, 1)
        for p, q in zip(out, PACKETS, strict=True):
            self.assertEqual(p.first_sample_time_s, q.first_sample_time_s)
            self.assertEqual(p.ready_time_s, q.ready_time_s)
            self.assertEqual(p.arrival_time_s, q.arrival_time_s)
            if p.station_id == "A":
                self.assertEqual(p.reported_first_sample_time_s, q.first_sample_time_s - 1.5)
                self.assertEqual(p.reported_sample_time_s(3), q.first_sample_time_s - 1.5 + 0.3)
            else:
                self.assertIsNone(p.reported_first_sample_time_s)
        self.assertEqual(rec.packets_affected, 40)
        # offsets compose
        again, _ = ClockOffset(0.5).apply(out, 1)
        self.assertEqual(again[0].reported_first_sample_time_s, -1.0)

    def test_missing_samples_shortens_packets_and_skips_short_ones(self):
        out, rec = MissingSamples(0.2, 3).apply(PACKETS, 123)
        self.assertEqual(rec.packets_affected, 20)
        for p, q in zip(out, PACKETS, strict=True):
            self.assertEqual(len(p.samples), 7 if p.key in set(rec.affected) else 10)
            self.assertEqual(p.samples, q.samples[: len(p.samples)])
        out, rec = MissingSamples(1.0, 10).apply(PACKETS, 1)  # n_samples == packet length: nothing can be removed
        self.assertEqual((rec.status, len(out)), ("skipped", 80))


class ComposeTests(unittest.TestCase):
    def test_no_faults_is_an_identity_control(self):
        out, records = apply_faults(PACKETS, [], 5)
        self.assertEqual(out, PACKETS)
        self.assertEqual(records, [])

    def test_declared_order_and_per_fault_seeds(self):
        faults = [Duplicate(0.5), PacketLoss("bernoulli", 0.5)]
        out_a, rec_a = apply_faults(PACKETS, faults, 77)
        out_b, rec_b = apply_faults(PACKETS, list(reversed(faults)), 77)
        self.assertEqual([r.type for r in rec_a], ["duplicate", "packet_loss"])
        self.assertEqual([r.type for r in rec_b], ["packet_loss", "duplicate"])
        self.assertEqual(rec_a[0].seed, derive_seed(77, "fault", 0, "duplicate"))
        self.assertEqual(rec_a[1].seed, derive_seed(77, "fault", 1, "packet_loss"))
        self.assertNotEqual(len(out_a), len(out_b))  # order matters, and is the declared one
        again, rec_c = apply_faults(PACKETS, faults, 77)
        self.assertEqual([p.key for p in again], [p.key for p in out_a])
        self.assertEqual(rec_c, rec_a)


if __name__ == "__main__":
    unittest.main()
