"""Pure-function tests for scripts/inspect_instance_sample.py.

The CSV below is FABRICATED (synthetic): invented station codes, times and values. It only exercises parsing code
and says nothing about the real INSTANCE dataset.
"""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.inspect_instance_sample import (
    noise_partner_counts,
    p_sample_offsets,
    parse_utc,
    read_csv_rows,
    split_trace_name,
    summarize_rows,
)

EVENTS = """trace_name,trace_dt_s,trace_npts,trace_eval_P,trace_P_arrival_sample,trace_P_arrival_time,trace_start_time,trace_deconvolved_units,source_type
1.XX.AAA..HH,0.01,12000,manual,1000,2000-01-01T00:00:20.00Z,2000-01-01T00:00:10.00Z,mps,earthquake
2.XX.BBB.00.HN,0.01,12000,manual,500,2000-01-01T00:00:15.01Z,2000-01-01T00:00:10.00Z,mps2,earthquake
3.YY.CCC..EH,0.01,12000,automatic,,2000-01-01T00:00:20.5Z,2000-01-01T00:00:10.00Z,mps,quarry blast
"""  # noqa: E501
NOISE = """trace_name,trace_dt_s,trace_npts
9.XX.AAA..HH,0.01,12000
9.ZZ.DDD..HH,0.01,12000
"""


class InspectInstanceTests(unittest.TestCase):
    def test_split_trace_name(self):
        self.assertEqual(split_trace_name("1.XX.AAA..HH"), ("1", "XX", "AAA", "", "HH"))
        self.assertEqual(split_trace_name("2.XX.BBB.00.HN").location, "00")
        for bad in ("1.XX.AAA.HH", "1.XX.AAA...HH", ".XX.AAA..HH", "1.XX.AAA..", ""):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                split_trace_name(bad)

    def test_parse_utc_variable_fraction(self):
        self.assertEqual(
            parse_utc("2000-01-01T00:00:20.5Z"), datetime(2000, 1, 1, 0, 0, 20, 500000, tzinfo=timezone.utc)
        )
        self.assertEqual(parse_utc("2000-01-01T00:00:20Z").microsecond, 0)
        self.assertEqual(parse_utc("2016-12-04T16:23:14.510000Z").microsecond, 510000)
        for bad in ("2000-01-01T00:00:20", "2000-01-01T00:00:20.1234567Z", "2000-01-01T00:00:20.xZ"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_utc(bad)

    def _rows(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            path.write_text(text)
            return list(read_csv_rows(path))

    def test_summarize_rows(self):
        s = summarize_rows(self._rows(EVENTS))
        self.assertEqual(s["rows"], 3)
        self.assertEqual(s["channel_family"], {"HH": 1, "HN": 1, "EH": 1})
        self.assertEqual(s["networks"], {"XX": 2, "YY": 1})
        self.assertEqual(s["trace_eval_P"], {"manual": 2, "automatic": 1})
        self.assertEqual(s["rows_with_P_arrival_sample"], 2)  # the empty field does not count
        self.assertEqual(s["trace_deconvolved_units"], {"mps": 2, "mps2": 1})
        self.assertEqual(s["source_type"], {"earthquake": 2, "quarry blast": 1})
        self.assertEqual(s["n_unparseable_trace_names"], 0)

    def test_summarize_rows_reports_bad_names_instead_of_hiding_them(self):
        s = summarize_rows(self._rows("trace_name,trace_dt_s,trace_npts\nnot-a-name,0.01,1\n"))
        self.assertEqual(s["n_unparseable_trace_names"], 1)
        self.assertEqual(s["channel_family"], {})

    def test_p_sample_offsets(self):
        o = p_sample_offsets(
            self._rows(EVENTS.replace("3.YY.CCC..EH,0.01,12000,automatic,,", "3.YY.CCC..EH,0.01,12000,automatic,1050,"))
        )
        # row1: 10.00 s / 0.01 = 1000 -> 0; row2: 5.01/0.01 = 501 vs 500 -> +1; row3: 10.5/0.01 = 1050 -> 0
        self.assertEqual(o["implied_minus_stated_samples"], {"0.0": 2, "1.0": 1})
        self.assertEqual((o["P_sample_min"], o["P_sample_max"]), (500, 1050))

    def test_noise_partner_counts(self):
        c = noise_partner_counts(self._rows(EVENTS), self._rows(NOISE))
        self.assertEqual(c["event_traces"], 3)
        self.assertEqual(c["with_noise_trace_same_station"], 1)
        self.assertEqual(c["with_noise_trace_same_station_location_family"], 1)


if __name__ == "__main__":
    unittest.main()
