"""Real-event source: pure functions and an end-to-end run on FABRICATED INSTANCE-like files (synthetic fixtures).

Nothing here is INSTANCE data: the CSV, HDF5 and miniSEED files are tiny arrays invented for the tests, written to a
temporary directory. The integration test at the bottom runs only if the user's real data are present.
"""

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from quakenode.config import ConfigError, parse_config
from quakenode.data.instance_event import (
    INPUT_LABELS,
    load_instance_event,
    select_event_rows,
    station_metadata,
    timeline_indices,
)
from quakenode.experiment import run_experiment

HAVE_H5 = importlib.util.find_spec("h5py") is not None
HAVE_OBSPY = importlib.util.find_spec("obspy") is not None
N = 1200  # fabricated window length (samples at 100 Hz)
# station, start offset (s) from the earliest start, stated P uncertainty
STATIONS = [("AAA", 0.0, "0.1"), ("BBB", 1.0, "0.3"), ("CCC", 2.5, "0.6"), ("DDD", 3.0, "1.0")]
P_SAMPLE = 300
HEADER = ["source_id", "trace_name", "trace_start_time", "trace_P_arrival_sample", "trace_P_arrival_time",
          "trace_P_uncertainty_s", "station_latitude_deg", "station_longitude_deg", "station_elevation_m",
          "source_magnitude", "path_ep_distance_km", "trace_dt_s", "trace_npts"]  # fmt: skip


def row(event, station, start, unc, net="IV", fam="HH", lat="43.0"):
    return {
        "source_id": event, "trace_name": f"{event}.{net}.{station}..{fam}", "trace_start_time": start,
        "trace_P_arrival_sample": str(P_SAMPLE), "trace_P_arrival_time": start, "trace_P_uncertainty_s": unc,
        "station_latitude_deg": lat, "station_longitude_deg": "13.0", "station_elevation_m": "",
        "source_magnitude": "2.5", "path_ep_distance_km": "20.0", "trace_dt_s": "0.01", "trace_npts": str(N),
    }  # fmt: skip


def start_time(offset_s):
    cents = round(offset_s * 100)
    return f"2000-01-01T00:00:{10 + cents // 100:02d}.{cents % 100:02d}Z"


def fabricated_rows():
    rows = [row("E1", st, start_time(off), unc, lat=("" if st == "DDD" else "43.0")) for st, off, unc in STATIONS]
    rows += [row("E1", "ZZZ", start_time(0), "0.1", net="MN"), row("E1", "YYY", start_time(0), "0.1", fam="HN"),
             row("E2", "AAA", start_time(0), "0.1")]  # fmt: skip
    return rows


def signal():
    x = [100.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(N)]
    for i in range(P_SAMPLE, P_SAMPLE + 100):
        x[i] += 20.0
    return x


class PureFunctionTests(unittest.TestCase):
    def test_select_event_rows_filters_by_event_network_family_and_stations(self):
        rows = fabricated_rows()
        names = [r["trace_name"] for r in select_event_rows(rows, "E1", "IV", "HH")]
        self.assertEqual(names, [f"E1.IV.{s}..HH" for s in ("AAA", "BBB", "CCC", "DDD")])
        subset = select_event_rows(rows, "E1", "IV", "HH", ["CCC", "AAA"])
        self.assertEqual([r["trace_name"].split(".")[2] for r in subset], ["AAA", "CCC"])
        self.assertEqual(select_event_rows(rows, "NOPE", "IV", "HH"), [])

    def test_station_metadata_uses_none_with_a_reason_never_a_guess(self):
        info = station_metadata(fabricated_rows()[3])  # DDD has an empty latitude
        self.assertIsNone(info["latitude_deg"])
        self.assertIn("station_latitude_deg", info["latitude_deg_missing_reason"])
        self.assertEqual(info["longitude_deg"], 13.0)
        self.assertIsNone(info["elevation_m"])  # empty column in the fabricated rows
        self.assertEqual(station_metadata({})["longitude_deg"], None)

    def test_timeline_indices_zero_is_the_earliest_start(self):
        starts = ["2000-01-01T00:00:12.37Z", "2000-01-01T00:00:10.00Z", "2000-01-01T00:00:10.05Z"]
        self.assertEqual(timeline_indices(starts), [237, 0, 5])
        self.assertEqual(timeline_indices(["2000-01-01T00:00:10.00Z"]), [0])


def write_fixture(tmp: Path, with_mseed: bool = False):
    import h5py
    import numpy as np

    (tmp / "metadata").mkdir()
    (tmp / "data").mkdir()
    rows = fabricated_rows()
    with open(tmp / "metadata/metadata_Instance_events_10k.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    x = np.array(signal())
    with h5py.File(tmp / "data/Instance_events_counts_10k.hdf5", "w") as h5:
        h5.create_group("data_format").create_dataset("component_order", data=b"ENZ")
        g = h5.create_group("data")
        for r in rows:
            g.create_dataset(r["trace_name"], data=np.stack([x * 0, x * 0, np.round(x)]).astype("int32"))
    if with_mseed:
        import obspy

        raw = tmp / "raw"
        raw.mkdir()
        for r in rows:
            if r["trace_name"].split(".")[2] in ("CCC", "DDD"):
                continue  # not fetched: these stations must be reported as excluded
            tr = obspy.Trace(np.round(x).astype("int32"))
            tr.stats.sampling_rate = 100.0
            tr.stats.starttime = obspy.UTCDateTime(r["trace_start_time"])
            tr.write(str(raw / f"{r['trace_name'].replace('..', '.')}.Z.mseed"), format="MSEED")
    return raw if with_mseed else None


def raw_config(tmp, input_kind, **over):
    inst = {"event_id": "E1", "input": input_kind, "data_dir": str(tmp), "raw_dir": str(tmp / "raw"),
            "packet_len_samples": 100, "min_stations": 3}  # fmt: skip
    return {
        "schema_version": 1, "name": "fab", "seeds": [1, 2], "scenario": {"source": "instance_event", "instance": inst},
        "detector": {"name": "recursive_sta_lta", "params": {"sta_s": 0.3, "lta_s": 2.0}},
        "faults": [], "fusion": {"k": 3, "window_s": 10, "update_window_s": 4}, **over,
    }  # fmt: skip


@unittest.skipUnless(HAVE_H5, "h5py not installed (extra `data`)")
class FabricatedEventTests(unittest.TestCase):
    def test_release_hdf5_event_end_to_end_with_labels_and_earliest_p_reference(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            write_fixture(tmp)
            cfg = parse_config(raw_config(tmp, "release_hdf5"), "f.yaml")
            scen = load_instance_event(cfg.scenario.instance, n_samples=N)
            self.assertEqual([s["station_id"] for s in scen.stations], ["AAA", "BBB", "CCC", "DDD"])
            self.assertEqual([s["start_time_s"] for s in scen.stations], [0.0, 1.0, 2.5, 3.0])
            self.assertEqual([s["p_time_s"] for s in scen.stations], [3.0, 4.0, 5.5, 6.0])  # (offset + 300)/100
            self.assertEqual([s["p_uncertainty_s"] for s in scen.stations], [0.1, 0.3, 0.6, 1.0])
            self.assertEqual(scen.default_event_reference, "earliest_p")
            self.assertIn("NOT causal input", scen.label["input_description"])
            self.assertEqual(scen.label["network_dois"], {"IV": "10.13127/sd/x0fxnh7qfy"})
            self.assertEqual(scen.label["license"], "CC BY 4.0 (INGV INSTANCE page)")
            self.assertTrue(any("NOT causal input" in w for w in scen.warnings))
            self.assertEqual(scen.station_info["DDD"]["latitude_deg"], None)

            run = run_experiment(raw_config(tmp, "release_hdf5"), "f.yaml", out_root=tmp / "runs")
            m = json.loads((run / "metrics.json").read_text())
            self.assertEqual((m["data"]["input_kind"], m["synthetic"]), ("release_hdf5", False))
            self.assertEqual(m["summary_over_seeds"]["detection_fraction"]["median"], 1.0)
            self.assertEqual(m["per_station"]["BBB"]["p_uncertainty_s"], 0.3)
            seed1 = m["per_seed"]["1"]
            self.assertEqual(seed1["event"]["reference_time_s"], 3.0)  # earliest catalog P, not the 3rd (5.5 s)
            events = [json.loads(x) for x in (run / "events.jsonl").read_text().splitlines()]
            cand = next(e for e in events if e["kind"] == "candidate" and e["seed"] == 1)
            self.assertAlmostEqual(seed1["event"]["association_latency_s"], cand["created_time_s"] - 3.0)
            self.assertTrue(all(e["input_kind"] == "release_hdf5" for e in events))
            # latency relative to the catalog P on the sample clock (burst starts exactly at the P sample)
            for s in seed1["stations"]:
                self.assertTrue(s["detected"])
                self.assertGreaterEqual(s["sample_latency_s"], 0.0)  # the burst starts exactly at the P sample
                self.assertLess(s["sample_latency_s"], 0.3)
                self.assertGreater(s["emission_latency_s"], s["sample_latency_s"])
            report = (run / "report.md").read_text()
            self.assertIn("REAL RECORDED EVENT E1", report)
            self.assertIn("NOT causal input", report)
            self.assertIn("TOOL DEMONSTRATION", report)
            man = json.loads((run / "manifest.json").read_text())
            self.assertTrue(any(d["sha256"] and d["doi"] == "10.13127/instance" for d in man["datasets"]))
            self.assertTrue(any("tool demonstration" in w.lower() for w in man["warnings"]))

    @unittest.skipUnless(HAVE_OBSPY, "obspy not installed (extra `data`)")
    def test_mseed_input_reports_stations_without_data_as_exclusions(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            write_fixture(tmp, with_mseed=True)
            raw = raw_config(tmp, "mseed")
            raw["scenario"]["instance"]["min_stations"] = 2
            cfg = parse_config(raw, "f.yaml")
            scen = load_instance_event(cfg.scenario.instance, n_samples=N)
            self.assertEqual([s["station_id"] for s in scen.stations], ["AAA", "BBB"])
            self.assertEqual([(e["station"], e["reason"]) for e in scen.exclusions],
                             [("CCC", "fetch_failed"), ("DDD", "fetch_failed")])  # fmt: skip
            self.assertEqual(scen.label["input_description"], INPUT_LABELS["mseed"])
            self.assertTrue(any("raw" in k for k in scen.file_hashes))
            strict = parse_config(raw_config(tmp, "mseed"), "f.yaml")  # min_stations is 3
            with self.assertRaisesRegex(ValueError, "only 2 usable station"):
                load_instance_event(strict.scenario.instance, n_samples=N)

    def test_missing_data_and_unknown_event_fail_loudly(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            cfg = parse_config(raw_config(tmp, "release_hdf5"), "f.yaml")
            with self.assertRaisesRegex(FileNotFoundError, "INSTANCE sample"):
                load_instance_event(cfg.scenario.instance, n_samples=N)
            write_fixture(tmp)
            raw = raw_config(tmp, "release_hdf5")
            raw["scenario"]["instance"]["event_id"] = "NOPE"
            bad = parse_config(raw, "f.yaml")
            with self.assertRaisesRegex(ValueError, "no IV.HH traces for event 'NOPE'"):
                load_instance_event(bad.scenario.instance, n_samples=N)


class ConfigTests(unittest.TestCase):
    def test_instance_event_config_validation(self):
        instance = {"event_id": "1", "input": "mseed"}
        base = {"schema_version": 1, "name": "x", "scenario": {"source": "instance_event", "instance": instance}}
        self.assertEqual(parse_config(base, "x.yaml").scenario.instance.packet_len_samples, 100)
        for change, message in (
            ({"input": "hdf5"}, "scenario.instance.input: must be 'release_hdf5' or 'mseed'"),
            ({"event_id": True}, "scenario.instance.event_id: must be a string"),
            ({"bogus": 1}, "unknown key(s) ['bogus']"),
            ({"stations": []}, "must be a non-empty list or omitted"),
        ):
            raw = json.loads(json.dumps(base))
            raw["scenario"]["instance"].update(change)
            with self.subTest(change=change), self.assertRaises(ConfigError) as cm:
                parse_config(raw, "x.yaml")
            self.assertIn(message, str(cm.exception))
        numeric = json.loads(json.dumps(base))
        numeric["scenario"]["instance"]["event_id"] = 11061071  # YAML / --set read unquoted ids as numbers
        self.assertEqual(parse_config(numeric, "x.yaml").scenario.instance.event_id, "11061071")
        no_instance = {"schema_version": 1, "name": "x", "scenario": {"source": "instance_event"}}
        with self.assertRaisesRegex(ConfigError, "scenario.instance: is required"):
            parse_config(no_instance, "x.yaml")
        mixed = json.loads(json.dumps(base))
        mixed["scenario"]["stations"] = [{"id": "A", "x_km": 0, "y_km": 0}]
        with self.assertRaisesRegex(ConfigError, "scenario.stations: not used with source 'instance_event'"):
            parse_config(mixed, "x.yaml")


REAL_HDF5 = Path("data/instance_sample/data/Instance_events_counts_10k.hdf5")
DEV_RAW = Path("data/raw/dev")


@unittest.skipUnless(HAVE_H5 and REAL_HDF5.exists(), "real INSTANCE sample not present (gitignored data/)")
class RealDataIntegrationTests(unittest.TestCase):
    def test_development_event_release_hdf5_loads_on_one_timeline(self):
        raw = raw_config(Path("data/instance_sample"), "release_hdf5")
        raw["scenario"]["instance"].update(event_id="11061071", data_dir="data/instance_sample")
        cfg = parse_config(raw, "f.yaml")
        scen = load_instance_event(cfg.scenario.instance)
        self.assertEqual(len(scen.stations), 16)
        self.assertEqual(min(s["start_time_s"] for s in scen.stations), 0.0)
        self.assertTrue(all(s["n_samples_total"] == 12000 for s in scen.stations))
        self.assertTrue(all(s["p_time_s"] > s["start_time_s"] for s in scen.stations))

    @unittest.skipUnless(HAVE_OBSPY and any(DEV_RAW.glob("*.mseed")), "fetched development miniSEED not present")
    def test_development_event_mseed_loads_or_reports_exclusions(self):
        raw = raw_config(Path("data/instance_sample"), "mseed")
        raw["scenario"]["instance"].update(event_id="11061071", data_dir="data/instance_sample", raw_dir=str(DEV_RAW))
        cfg = parse_config(raw, "f.yaml")
        scen = load_instance_event(cfg.scenario.instance)
        self.assertEqual(len(scen.stations) + len(scen.exclusions), 16)


if __name__ == "__main__":
    unittest.main()
