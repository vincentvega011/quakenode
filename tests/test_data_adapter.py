"""Tests for quakenode.data. All arrays and files below are tiny FABRICATED fixtures (synthetic), not INSTANCE data."""

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from quakenode.data import (
    MissingExtraError,
    TraceRecord,
    load_raw_window,
    load_release_z,
    make_stream_packets,
    parse_utc_ns,
)
from quakenode.data import instance as inst

HAVE_H5 = importlib.util.find_spec("h5py") is not None
HAVE_OBSPY = importlib.util.find_spec("obspy") is not None

ROW = {
    "trace_name": "1.IV.AAA..HH",
    "source_id": "1",
    "trace_start_time": "2000-01-01T00:00:10.00Z",
    "trace_P_arrival_sample": "1500",
    "trace_P_arrival_time": "2000-01-01T00:00:25.00Z",
    "trace_P_uncertainty_s": "1.0",
    "source_magnitude": "2.5",
    "path_ep_distance_km": "40.5",
}


class PureTests(unittest.TestCase):
    def test_import_does_not_pull_heavy_dependencies(self):
        code = (
            "import sys, quakenode.data; print(json_dumps([m for m in ('h5py','obspy','numpy') if m in sys.modules]))"
        )
        out = subprocess.run(
            [sys.executable, "-c", code.replace("json_dumps", "list")], capture_output=True, text=True, check=True
        )
        self.assertEqual(out.stdout.strip(), "[]")

    def test_missing_extra_gives_clear_error(self):
        with mock.patch.object(inst.importlib, "import_module", side_effect=ImportError("no module")):
            with self.assertRaisesRegex(MissingExtraError, r"quakenode\[data\]"):
                load_release_z("x.hdf5", "t")
            with self.assertRaisesRegex(MissingExtraError, r"quakenode\[data\]"):
                load_raw_window("x.mseed", "2000-01-01T00:00:00.00Z", 10, 100.0)

    def test_parse_utc_ns(self):
        base = parse_utc_ns("2000-01-01T00:00:00Z")
        self.assertEqual(base, 946684800 * 10**9)
        self.assertEqual(parse_utc_ns("2000-01-01T00:00:00.51Z") - base, 510_000_000)
        self.assertEqual(parse_utc_ns("2000-01-01T00:00:00.000000001Z") - base, 1)
        for bad in ("2000-01-01T00:00:00", "2000-01-01T00:00:00.1234567890Z", "2000-01-01T00:00:00.xZ"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_utc_ns(bad)

    def test_trace_record_from_row(self):
        r = TraceRecord.from_metadata_row(ROW, release_hdf5_sha256="abc")
        self.assertEqual((r.event_id, r.network, r.station, r.location, r.channel_family), ("1", "IV", "AAA", "", "HH"))
        self.assertEqual(r.p_sample, 1500)
        self.assertEqual(r.p_time_in_window_s, 15.0)
        self.assertEqual((r.p_uncertainty_s, r.magnitude, r.epicentral_distance_km), (1.0, 2.5, 40.5))
        self.assertEqual(r.release_hdf5_sha256, "abc")
        with self.assertRaises(ValueError):
            TraceRecord.from_metadata_row({**ROW, "trace_P_arrival_sample": ""})
        with self.assertRaises(ValueError):
            TraceRecord.from_metadata_row({**ROW, "trace_name": "bad.name"})
        self.assertIsNone(TraceRecord.from_metadata_row({**ROW, "source_magnitude": ""}).magnitude)

    def test_both_arms_get_identical_packet_timing(self):
        release = [(i * 7) % 11 - 5 for i in range(1000)]
        raw = [(i * 5) % 13 + 800 for i in range(1000)]
        kw = dict(station_id="AAA", channel_id="HHZ", sample_rate_hz=100.0, packet_len_samples=64)
        a, b = make_stream_packets(release, **kw), make_stream_packets(raw, **kw)
        self.assertEqual(len(a), len(b))
        for pa, pb in zip(a, b, strict=True):
            self.assertEqual(
                (pa.sequence_number, pa.first_sample_index, pa.first_sample_time_s, pa.ready_time_s, pa.arrival_time_s),
                (pb.sequence_number, pb.first_sample_index, pb.first_sample_time_s, pb.ready_time_s, pb.arrival_time_s),
            )
        self.assertNotEqual(a[0].samples, b[0].samples)
        self.assertEqual(sum(len(p.samples) for p in a), 1000)


@unittest.skipUnless(HAVE_H5, "h5py not installed (extra `data`)")
class ReleaseLoaderTests(unittest.TestCase):
    def _write(self, path, order=b"ENZ", dtype="int32", shape=(3, 20)):
        import h5py
        import numpy as np

        with h5py.File(path, "w") as h5:
            h5.create_group("data_format").create_dataset("component_order", data=order)
            g = h5.create_group("data")
            g.create_dataset("good", data=np.arange(shape[0] * shape[1]).reshape(shape).astype(dtype))

    def test_returns_row_2_as_int32(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.hdf5"
            self._write(p)
            z = load_release_z(p, "good")
        self.assertEqual(str(z.dtype), "int32")
        self.assertEqual(z.tolist(), list(range(40, 60)))  # row 2 of a 3x20 arange

    def test_checks_fail_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.hdf5"
            self._write(p)
            with self.assertRaises(KeyError):
                load_release_z(p, "missing")
            self._write(p, order=b"ZNE")
            with self.assertRaisesRegex(ValueError, "component_order"):
                load_release_z(p, "good")
            self._write(p, dtype="float32")
            with self.assertRaisesRegex(ValueError, "int32"):
                load_release_z(p, "good")
            self._write(p, shape=(2, 20))
            with self.assertRaisesRegex(ValueError, "shape"):
                load_release_z(p, "good")


@unittest.skipUnless(HAVE_OBSPY, "obspy not installed (extra `data`)")
class RawWindowTests(unittest.TestCase):
    T0 = "2000-01-01T00:00:00"

    def _trace(self, start_offset_s, n, rate=100.0, base=1000):
        import numpy as np
        import obspy

        tr = obspy.Trace(np.arange(base, base + n, dtype="int32"))
        tr.stats.sampling_rate = rate
        tr.stats.starttime = obspy.UTCDateTime(self.T0) + start_offset_s
        tr.stats.network, tr.stats.station, tr.stats.channel = "IV", "AAA", "HHZ"
        return tr

    def _file(self, tmp, traces):
        import obspy

        p = Path(tmp) / "x.mseed"
        obspy.Stream(traces).write(str(p), format="MSEED", encoding="STEIM1")
        return p

    def test_nearest_sample_alignment_and_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            # raw grid points at 0.0034 s + k*0.01; metadata start 0.51 s is nearest to raw index 51 (0.5134 s)
            p = self._file(tmp, [self._trace(0.0034, 200)])
            w = load_raw_window(p, "2000-01-01T00:00:00.51Z", 100, 100.0)
        self.assertIsNone(w.exclusion_reason)
        self.assertEqual(w.first_raw_index, 51)
        self.assertEqual(w.samples[0], 1051)  # values untouched, nothing shifted or demeaned
        self.assertEqual(len(w.samples), 100)
        self.assertAlmostEqual(w.offset_samples, (0.51 - 0.0034) / 0.01 - 51, places=6)
        self.assertLessEqual(abs(w.offset_samples), 0.5)

    def test_exclusions_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            short = self._file(tmp, [self._trace(0.0, 120)])
            self.assertEqual(load_raw_window(short, "2000-01-01T00:00:00.50Z", 100, 100.0).exclusion_reason,
                             "raw_does_not_cover_window")  # fmt: skip
            self.assertEqual(load_raw_window(short, "1999-12-31T23:59:59.00Z", 10, 100.0).exclusion_reason,
                             "raw_does_not_cover_window")  # fmt: skip
            fast = self._file(tmp, [self._trace(0.0, 1000, rate=200.0)])
            self.assertEqual(load_raw_window(fast, "2000-01-01T00:00:01.00Z", 100, 100.0).exclusion_reason,
                             "native_rate_not_100hz")  # fmt: skip
            missing = Path(tmp) / "nope.mseed"
            self.assertEqual(
                load_raw_window(missing, "2000-01-01T00:00:01.00Z", 10, 100.0).exclusion_reason, "fetch_failed"
            )
            empty = Path(tmp) / "empty.mseed"
            empty.write_bytes(b"")
            self.assertEqual(
                load_raw_window(empty, "2000-01-01T00:00:01.00Z", 10, 100.0).exclusion_reason, "fetch_failed"
            )
            garbage = Path(tmp) / "garbage.mseed"
            garbage.write_bytes(b"not miniseed" * 50)
            self.assertEqual(
                load_raw_window(garbage, "2000-01-01T00:00:01.00Z", 10, 100.0).exclusion_reason, "fetch_failed"
            )
            with self.assertRaises(ValueError):
                load_raw_window(short, "2000-01-01T00:00:00.50Z", 100, 100.0).require()

    def test_gap_only_matters_inside_the_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Segment A: 0.00..0.99 s (100 samples); gap; segment B: 2.00..4.99 s (300 samples).
            p = self._file(tmp, [self._trace(0.0, 100), self._trace(2.0, 300, base=5000)])
            inside_b = load_raw_window(p, "2000-01-01T00:00:02.50Z", 100, 100.0)
            spanning = load_raw_window(p, "2000-01-01T00:00:00.50Z", 100, 100.0)
        self.assertIsNone(inside_b.exclusion_reason)  # the earlier gap is outside the window
        self.assertEqual(inside_b.samples[0], 5050)
        self.assertEqual(spanning.exclusion_reason, "gaps_or_overlaps")
        self.assertEqual(spanning.n_traces_in_file, 2)


REAL_HDF5 = Path("data/instance_sample/data/Instance_events_counts_10k.hdf5")
REAL_CSV = Path("data/instance_sample/metadata/metadata_Instance_events_10k.csv")
REAL_RAW = Path("data/raw/cohort")
COHORT = Path("docs/cohort_stage1_traces.txt")


@unittest.skipUnless(
    HAVE_H5
    and HAVE_OBSPY
    and REAL_HDF5.exists()
    and REAL_CSV.exists()
    and COHORT.exists()
    and any(REAL_RAW.glob("*.mseed")),
    "real INSTANCE sample, cohort list and fetched cohort miniSEED not present (gitignored data/)",
)
class RealDataIntegrationTests(unittest.TestCase):
    def test_adapter_on_a_fetched_cohort_trace(self):
        import csv

        with open(REAL_CSV, newline="") as f:
            rows = {r["trace_name"]: r for r in csv.DictReader(f)}
        name = next(n for n in COHORT.read_text().split() if (REAL_RAW / f"{n.replace('..', '.')}.Z.mseed").exists())
        rec = TraceRecord.from_metadata_row(rows[name])
        z = load_release_z(REAL_HDF5, name)
        self.assertEqual((len(z), str(z.dtype)), (12000, "int32"))
        w = load_raw_window(REAL_RAW / f"{name.replace('..', '.')}.Z.mseed", rec.trace_start_time, 12000, 100.0)
        self.assertIn(w.exclusion_reason, (None, *inst.EXCLUSION_REASONS))
        if w.exclusion_reason is None:
            self.assertEqual(len(w.samples), 12000)
            kw = dict(station_id=rec.station, channel_id="HHZ", sample_rate_hz=100.0, packet_len_samples=100)
            a, b = make_stream_packets(z, **kw), make_stream_packets(w.samples, **kw)
            self.assertEqual([p.arrival_time_s for p in a], [p.arrival_time_s for p in b])
        json.dumps(rec.p_sample)


if __name__ == "__main__":
    unittest.main()
