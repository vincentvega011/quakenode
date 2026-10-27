"""Strict YAML config validation: errors name the file and the key. Configs are SYNTHETIC scenarios."""

import copy
import tempfile
import unittest
from pathlib import Path

from quakenode.config import ConfigError, apply_overrides, load_config, parse_config, set_path

BASE = {
    "schema_version": 1,
    "name": "t",
    "scenario": {
        "stations": [{"id": "A", "x_km": 0, "y_km": 0}, {"id": "B", "x_km": 10, "y_km": 5}],
        "event": {"origin_time_s": 10, "x_km": 5, "y_km": 5},
        "duration_s": 30,
    },
    "faults": [{"type": "packet_loss", "p": 0.1}],
}


def cfg(**changes):
    raw = copy.deepcopy(BASE)
    for dotted, value in changes.items():
        node = raw
        parts = dotted.split("__")
        for part in parts[:-1]:
            node = node[int(part)] if isinstance(node, list) else node[part]
        last = parts[-1]
        if isinstance(node, list):
            node[int(last)] = value
        else:
            node[last] = value
    return raw


def error_for(raw, file="my.yaml"):
    with unittest.TestCase().assertRaises(ConfigError) as cm:
        parse_config(raw, file)
    return str(cm.exception)


class ValidationTests(unittest.TestCase):
    def test_minimal_valid_config_fills_defaults(self):
        c = parse_config(BASE, "x.yaml")
        self.assertEqual(
            (c.detector.name, c.pipeline.order_policy, c.fusion.k, c.output_dir), ("sta_lta_rms", "reject", 3, "runs")
        )
        self.assertEqual(c.seeds, list(range(1, 11)))
        self.assertEqual(c.scenario.sample_rate_hz, 50.0)

    def test_unknown_keys_are_rejected_with_file_and_path(self):
        self.assertRegex(error_for({**BASE, "surprise": 1}), r"my\.yaml: <root>: unknown key\(s\) \['surprise'\]")
        msg = error_for(cfg(scenario__bogus=1))
        self.assertIn("my.yaml: scenario: unknown key(s) ['bogus']", msg)
        self.assertIn(
            "my.yaml: scenario.stations[1]: unknown key(s) ['z']",
            error_for(cfg(scenario__stations__1={"id": "B", "x_km": 1, "y_km": 1, "z": 3})),
        )

    def test_missing_required_keys(self):
        raw = copy.deepcopy(BASE)
        del raw["scenario"]["stations"]
        self.assertIn("scenario.stations: needs at least one station", error_for(raw))
        raw = copy.deepcopy(BASE)
        del raw["name"]
        self.assertIn("missing required key 'name'", error_for(raw))

    def test_ranges_and_types_name_the_key_and_value(self):
        self.assertIn(
            "scenario.sample_rate_hz: must be > 0 (got -5",
            error_for(cfg(scenario__sample_rate_hz=-5)).replace("-5.0", "-5"),
        )
        self.assertIn(
            "scenario.packet_len_samples: must be an integer (got 2.5)",
            error_for(cfg(scenario__packet_len_samples=2.5)),
        )
        self.assertIn("scenario.duration_s: must be a number (got 'long')", error_for(cfg(scenario__duration_s="long")))
        self.assertIn(
            "scenario.event.origin_time_s: must be < duration_s",
            error_for(cfg(scenario__event={"origin_time_s": 40, "x_km": 0, "y_km": 0})),
        )
        self.assertIn("schema_version: unsupported", error_for(cfg(schema_version=2)))
        self.assertIn("seeds: needs at least one seed, all different", error_for(cfg(seeds=[1, 1])))
        self.assertIn(
            "pipeline.max_wait_s: must be > 0 when order_policy is 'buffer'",
            error_for(cfg(pipeline={"order_policy": "buffer"})),
        )
        self.assertIn("pipeline.order_policy: must be one of", error_for(cfg(pipeline={"order_policy": "later"})))
        self.assertIn("fusion.window_clock: must be one of", error_for(cfg(fusion={"window_clock": "sample"})))
        self.assertIn(
            "scenario.stations: station ids must be unique",
            error_for(cfg(scenario__stations=[{"id": "A", "x_km": 0, "y_km": 0}] * 2)),
        )

    def test_detector_errors(self):
        self.assertIn("unknown detector 'magic'", error_for(cfg(detector={"name": "magic"})))
        self.assertIn(
            "unknown parameter(s) ['x']", error_for(cfg(detector={"name": "sta_lta_rms", "params": {"x": 1}}))
        )
        self.assertIn(
            "'threshold' must be > 0.0", error_for(cfg(detector={"name": "sta_lta_rms", "params": {"threshold": -1}}))
        )

    def test_fault_errors(self):
        self.assertIn(
            "faults[0].p: must be between 0 and 1 (got 1.5)",
            error_for(cfg(faults__0={"type": "packet_loss", "p": 1.5})),
        )
        self.assertIn("faults[0].type: unknown fault type 'storm'", error_for(cfg(faults__0={"type": "storm"})))
        self.assertIn(
            "faults[0]: unknown key(s) ['delay'] for fault 'packet_loss'",
            error_for(cfg(faults__0={"type": "packet_loss", "delay": 1})),
        )
        self.assertIn(
            "faults[0]: fault 'fixed_delay' requires key 'delay_s'", error_for(cfg(faults__0={"type": "fixed_delay"}))
        )
        self.assertIn(
            "faults[0].targets: unknown station id(s) ['Z']",
            error_for(cfg(faults__0={"type": "station_outage", "targets": ["Z"]})),
        )
        self.assertIn(
            "faults[0].end_s: must be greater than start_s",
            error_for(cfg(faults__0={"type": "station_outage", "start_s": 5, "end_s": 5})),
        )
        self.assertIn(
            "faults[0].model: must be one of", error_for(cfg(faults__0={"type": "packet_loss", "model": "x"}))
        )
        self.assertIn(
            "gilbert_elliott needs p_gb > 0 and p_bg > 0",
            error_for(cfg(faults__0={"type": "packet_loss", "model": "gilbert_elliott"})),
        )
        self.assertIn(
            "faults[0].mean_s: must be > 0 for the exponential",
            error_for(cfg(faults__0={"type": "jitter", "distribution": "exponential"})),
        )
        self.assertIn(
            "faults[0].n_samples: must be an integer >= 1",
            error_for(cfg(faults__0={"type": "missing_samples", "p": 0.1, "n_samples": 0})),
        )
        self.assertIn("faults[0]: must be a mapping", error_for(cfg(faults__0="packet_loss")))

    def test_sweep_section(self):
        ok = cfg(sweep={"parameters": [{"path": "faults.0.p", "values": [0.1, 0.2]}]})
        self.assertEqual(parse_config(ok).sweep.parameters[0].values, [0.1, 0.2])
        self.assertIn("sweep.parameters: give one or two sweep parameters", error_for(cfg(sweep={"parameters": []})))
        self.assertIn(
            "sweep.parameters[0].values: needs at least one value",
            error_for(cfg(sweep={"parameters": [{"path": "a", "values": []}]})),
        )


class OverrideTests(unittest.TestCase):
    def test_overrides_are_yaml_typed_and_recorded(self):
        raw, applied = apply_overrides(
            copy.deepcopy(BASE), ["faults.0.p=0.02", "detector.name=recursive_sta_lta", "pipeline.gap_policy=hold",
                                  "fusion.exclude_filled_detections=false", "seeds=[1, 2]"])  # fmt: skip
        self.assertEqual(raw["faults"][0]["p"], 0.02)
        self.assertEqual(raw["detector"]["name"], "recursive_sta_lta")  # key did not exist: created
        self.assertEqual(raw["pipeline"], {"gap_policy": "hold"})
        self.assertIs(raw["fusion"]["exclude_filled_detections"], False)
        self.assertEqual(raw["seeds"], [1, 2])
        self.assertEqual(applied[0], {"path": "faults.0.p", "value": 0.02, "source": "cli"})
        cfg = parse_config(raw, "x.yaml")
        self.assertEqual((cfg.pipeline.gap_policy, cfg.detector.name), ("hold", "recursive_sta_lta"))
        self.assertEqual(BASE["faults"][0]["p"], 0.1)  # input untouched

    def test_overrides_go_through_the_strict_schema(self):
        raw, _ = apply_overrides(copy.deepcopy(BASE), ["pipeline.gap_policy=interpolate"])
        self.assertIn("pipeline.gap_policy: must be one of ['reset', 'hold', 'zero_fill']", error_for(raw))
        raw, _ = apply_overrides(copy.deepcopy(BASE), ["pipeline.nope=1"])
        self.assertIn("pipeline: unknown key(s) ['nope']", error_for(raw))
        raw, _ = apply_overrides(copy.deepcopy(BASE), ["faults.0.p=3"])
        self.assertIn("faults[0].p: must be between 0 and 1 (got 3)", error_for(raw))

    def test_malformed_overrides_fail_loudly(self):
        for bad in ("noequals", "=1", "faults.5.p=0.1", "faults.0.p=[1"):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                apply_overrides(copy.deepcopy(BASE), [bad])


class LoadingTests(unittest.TestCase):
    def test_load_config_reports_file_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.yaml"
            good.write_text("schema_version: 1\nname: x\nscenario:\n  stations: [{id: A, x_km: 0, y_km: 0}]\n")
            self.assertEqual(load_config(good).name, "x")
            bad = Path(tmp) / "bad.yaml"
            bad.write_text("schema_version: [1\n")
            with self.assertRaisesRegex(ConfigError, r"bad\.yaml: invalid YAML"):
                load_config(bad)
            scalar = Path(tmp) / "scalar.yaml"
            scalar.write_text("42\n")
            with self.assertRaisesRegex(ConfigError, "top level must be a mapping"):
                load_config(scalar)
            with self.assertRaisesRegex(ConfigError, "cannot read file"):
                load_config(Path(tmp) / "missing.yaml")

    def test_shipped_examples_are_valid(self):
        for name in ("config.yaml", "sweep.yaml"):
            path = Path("examples/synthetic_network") / name
            if path.exists():
                self.assertTrue(load_config(path).scenario.stations)

    def test_set_path(self):
        raw = copy.deepcopy(BASE)
        out = set_path(raw, "faults.0.p", 0.5)
        self.assertEqual(out["faults"][0]["p"], 0.5)
        self.assertEqual(raw["faults"][0]["p"], 0.1)  # deep copy
        for bad in ("faults.3.p", "faults.0.q", "nope.x", "faults.x"):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                set_path(raw, bad, 1)


if __name__ == "__main__":
    unittest.main()
