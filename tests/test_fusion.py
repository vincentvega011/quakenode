"""k-of-n fusion with hand-built detection lists (hand-computed expectations). Detections are SYNTHETIC."""

import unittest

from quakenode.fusion import FusionConfig, fuse
from quakenode.replay import Detection


def det(station, emission, arrival=None, index=0):
    arrival = emission if arrival is None else arrival
    return Detection(station, "SYN", index, 0.0, 0.0, arrival, emission, 0.0, "t", "1", 5.0, 3.0, ())


CFG = FusionConfig(k=3, window_s=10.0, update_window_s=5.0)


def kinds(result):
    return [(d.kind, d.station_id, d.candidate_id) for d in result.decisions]


class FusionTests(unittest.TestCase):
    def test_candidate_created_when_k_distinct_stations_fall_in_the_window(self):
        r = fuse([det("S3", 15.0), det("S1", 10.0), det("S2", 12.0)], CFG)
        self.assertEqual(len(r.candidates), 1)
        c = r.candidates[0]
        self.assertEqual((c.created_time_s, c.station_ids, c.status), (15.0, ("S1", "S2", "S3"), "created"))
        self.assertEqual(kinds(r), [("detection_pending", "S1", None), ("detection_pending", "S2", None),
                                    ("detection_pending", "S3", None), ("candidate_created", "S3", 1)])  # fmt: skip

    def test_stale_pending_detection_expires_and_blocks_the_candidate(self):
        # S1 at 0 is older than window_s=10 when S2 arrives at 11, so only S2 and S3 are pending: 2 < 3.
        r = fuse([det("S1", 0.0), det("S2", 11.0), det("S3", 12.0)], CFG)
        self.assertEqual(r.candidates, [])
        self.assertIn(("pending_expired", "S1", None), kinds(r))

    def test_window_edge_is_inclusive(self):
        r = fuse([det("S1", 0.0), det("S2", 5.0), det("S3", 10.0)], CFG)  # S1 exactly window_s old at t=10
        self.assertEqual(len(r.candidates), 1)

    def test_repeated_detections_from_one_station_are_deduplicated(self):
        r = fuse([det("S1", 1.0), det("S1", 2.0, index=1), det("S2", 3.0), det("S3", 4.0)], CFG)
        self.assertEqual(len(r.candidates), 1)
        self.assertEqual(r.candidates[0].station_ids, ("S1", "S2", "S3"))
        self.assertEqual(sum(1 for d in r.decisions if d.kind == "duplicate_ignored"), 1)

    def test_late_detection_updates_the_candidate_within_the_update_window(self):
        dets = [det("S1", 10.0), det("S2", 12.0), det("S3", 15.0), det("S4", 18.0), det("S4", 19.0, index=1),
                det("S1", 19.5, index=1), det("S5", 21.0)]  # fmt: skip
        r = fuse(dets, CFG)
        c = r.candidates[0]
        self.assertEqual(c.station_ids, ("S1", "S2", "S3", "S4"))  # S4 at 18 <= 15 + 5 joins
        self.assertEqual((c.status, c.update_times_s), ("closed", [18.0]))
        self.assertEqual(c.closed_time_s, 20.0)
        self.assertEqual(len(r.candidates), 1)  # S5 at 21 starts a new pool; one pending station is not enough
        ks = kinds(r)
        self.assertIn(("candidate_updated", "S4", 1), ks)
        self.assertEqual(sum(1 for k in ks if k[0] == "duplicate_ignored"), 2)  # S4 again, S1 again (both in candidate)
        self.assertIn(("candidate_closed", None, 1), ks)

    def test_window_clock_choice_changes_the_outcome(self):
        # S3 is delayed on the emission clock (30 s) but arrived at 12 s.
        dets = [det("S1", 10.0), det("S2", 11.0), det("S3", 30.0, arrival=12.0)]
        by_emission = fuse(dets, FusionConfig(3, 10.0, 5.0, "emission"))
        by_arrival = fuse(dets, FusionConfig(3, 10.0, 5.0, "arrival"))
        self.assertEqual(by_emission.candidates, [])
        self.assertEqual(len(by_arrival.candidates), 1)
        self.assertEqual(by_arrival.candidates[0].created_time_s, 30.0)  # creation is always on the emission clock

    def test_k_equal_one_creates_a_candidate_per_first_detection(self):
        r = fuse([det("S1", 1.0)], FusionConfig(1, 10.0, 0.0))
        self.assertEqual([c.station_ids for c in r.candidates], [("S1",)])

    def test_invalid_configuration_is_rejected(self):
        for bad in ((0, 1.0, 1.0), (2, 0.0, 1.0), (2, 1.0, -1.0)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                FusionConfig(*bad)
        with self.assertRaises(ValueError):
            FusionConfig(2, 1.0, 1.0, "sample")


if __name__ == "__main__":
    unittest.main()
