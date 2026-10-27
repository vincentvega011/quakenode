"""YAML experiment configuration with strict validation.

Unknown keys are rejected, ranges are checked, and every error names the file and the key path, e.g.
`config.yaml: faults[0].p: must be between 0 and 1 (got 1.5)`.
"""

from __future__ import annotations

import copy
import types
import typing
from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
FAULT_COMMON = ("type", "targets", "start_s", "end_s")
COERCE_INT_TO_STR = {"event_id"}  # numeric-looking identifiers are accepted as integers and stored as strings


class ConfigError(ValueError):
    """Invalid configuration; the message names the file and the key."""


# ---- dataclasses ------------------------------------------------------------------------------------------------


@dataclass
class StationConfig:
    id: str
    x_km: float
    y_km: float


@dataclass
class EventConfig:
    origin_time_s: float
    x_km: float
    y_km: float
    depth_km: float = 10.0
    amplitude: float = 50.0


@dataclass
class InstanceEventConfig:
    """Real recorded event from the INSTANCE sample (needs the `data` extra and the user's own downloaded data)."""

    event_id: str
    input: str  # release_hdf5 | mseed
    data_dir: str = "data/instance_sample"
    raw_dir: str = "data/raw/dev"
    network: str = "IV"
    channel_family: str = "HH"
    packet_len_samples: int = 100
    min_stations: int = 3
    stations: list[str] | None = None  # optional subset of station codes


@dataclass
class ScenarioConfig:
    stations: list[StationConfig] = field(default_factory=list)
    source: str = "synthetic_network"  # synthetic_network | instance_event
    instance: InstanceEventConfig | None = None
    type: str = "synthetic_network"  # legacy alias of `source` for synthetic scenarios
    event: EventConfig | None = None
    duration_s: float = 60.0
    sample_rate_hz: float = 50.0
    packet_len_samples: int = 25
    velocity_km_s: float = 6.0
    noise_sigma: float = 1.0
    baseline_counts: float = 800.0
    amplitude_ref_km: float = 50.0
    coda_decay_per_s: float = 0.5
    pulse_freq_hz: float = 4.0


@dataclass
class DetectorConfig:
    name: str = "sta_lta_rms"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    order_policy: str = "reject"
    max_wait_s: float = 0.0
    gap_policy: str = "reset"  # reset | hold | zero_fill (docs/gap_policies.md)
    processing_delay_s: float = 0.0


@dataclass
class FusionSection:
    k: int = 3
    window_s: float = 10.0
    update_window_s: float = 5.0
    window_clock: str = "emission"
    exclude_filled_detections: bool = True  # detections triggered on zero-filled samples do not enter fusion


@dataclass
class MetricsSection:
    detection_pre_margin_s: float = 1.0
    detection_post_horizon_s: float = 10.0
    bootstrap_seed: int | None = 12345
    event_reference: str | None = None  # kth_p | earliest_p; default: kth_p (synthetic), earliest_p (real events)


@dataclass
class SweepParameter:
    path: str
    values: list[Any]  # numbers or strings (for example detector names)


@dataclass
class SweepSection:
    parameters: list[SweepParameter]
    headline_metric: str = "detection_fraction"


@dataclass
class ExperimentConfig:
    schema_version: int
    name: str
    scenario: ScenarioConfig
    seeds: list[int] = field(default_factory=lambda: list(range(1, 11)))
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    faults: list[dict[str, Any]] = field(default_factory=list)  # validated against FAULT_SPECS
    fusion: FusionSection = field(default_factory=FusionSection)
    metrics: MetricsSection = field(default_factory=MetricsSection)
    output_dir: str = "runs"
    sweep: SweepSection | None = None


# ---- per-fault parameter specs ----------------------------------------------------------------------------------

_PROB = ("prob", None)


@dataclass(frozen=True)
class FP:
    kind: str  # 'float', 'int', 'prob', 'choice', 'seconds'
    default: Any = None  # None = required
    choices: tuple[str, ...] = ()


FAULT_SPECS: dict[str, dict[str, FP]] = {
    "fixed_delay": {"delay_s": FP("seconds")},
    "jitter": {
        "distribution": FP("choice", choices=("uniform", "exponential")),
        "low_s": FP("seconds", 0.0),
        "high_s": FP("seconds", 0.0),
        "mean_s": FP("seconds", 0.0),
    },
    "packet_loss": {
        "model": FP("choice", "bernoulli", ("bernoulli", "gilbert_elliott")),
        "p": FP("prob", 0.0),
        "p_gb": FP("prob", 0.0),
        "p_bg": FP("prob", 0.0),
        "loss_good": FP("prob", 0.0),
        "loss_bad": FP("prob", 1.0),
    },
    "duplicate": {"p": FP("prob"), "extra_delay_s": FP("seconds", 0.0)},
    "reorder": {"p": FP("prob"), "hold_s": FP("seconds")},
    "station_outage": {},
    "clock_offset": {"offset_s": FP("float")},
    "missing_samples": {"p": FP("prob"), "n_samples": FP("int")},
}


# ---- generic strict builder -------------------------------------------------------------------------------------


class _Ctx:
    def __init__(self, file: str) -> None:
        self.file = file

    def err(self, path: str, msg: str) -> ConfigError:
        return ConfigError(f"{self.file}: {path or '<root>'}: {msg}")


def _is_number(v: Any) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool)


def _convert(tp: Any, value: Any, path: str, ctx: _Ctx) -> Any:
    origin = typing.get_origin(tp)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        if value is None:
            return None
        return _convert(args[0], value, path, ctx)
    if origin is list:
        if not isinstance(value, list):
            raise ctx.err(path, f"must be a list (got {type(value).__name__})")
        (item,) = typing.get_args(tp)
        return [_convert(item, v, f"{path}[{i}]", ctx) for i, v in enumerate(value)]
    if origin is dict:
        if not isinstance(value, dict):
            raise ctx.err(path, f"must be a mapping (got {type(value).__name__})")
        return dict(value)
    if tp is Any:
        return value
    if is_dataclass(tp):
        return _build(tp, value, path, ctx)
    if tp is bool:
        if not isinstance(value, bool):
            raise ctx.err(path, f"must be true or false (got {value!r})")
        return value
    if tp is int:
        if not _is_number(value) or float(value) != int(value):
            raise ctx.err(path, f"must be an integer (got {value!r})")
        return int(value)
    if tp is float:
        if not _is_number(value):
            raise ctx.err(path, f"must be a number (got {value!r})")
        return float(value)
    if tp is str:
        if not isinstance(value, str):
            raise ctx.err(path, f"must be a string (got {value!r})")
        return value
    raise ctx.err(path, f"unsupported type {tp}")  # pragma: no cover


def _build(cls: type, data: Any, path: str, ctx: _Ctx) -> Any:
    if not isinstance(data, dict):
        raise ctx.err(path, f"must be a mapping (got {type(data).__name__})")
    hints = typing.get_type_hints(cls)
    known = {f.name for f in fields(cls)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ctx.err(path, f"unknown key(s) {unknown}; allowed: {sorted(known)}")
    kwargs = {}
    for f in fields(cls):
        child = f"{path}.{f.name}" if path else f.name
        if f.name in data:
            value = data[f.name]
            if f.name in COERCE_INT_TO_STR and isinstance(value, int) and not isinstance(value, bool):
                value = str(value)  # ids such as 11061071 are read as numbers by YAML and by --set
            kwargs[f.name] = _convert(hints[f.name], value, child, ctx)
        elif f.default is MISSING and f.default_factory is MISSING:  # type: ignore[misc]
            raise ctx.err(path, f"missing required key {f.name!r}")
    obj = cls(**kwargs)
    check = getattr(obj, "_check", None)
    if check is not None:
        check(path, ctx)
    return obj


# ---- range checks (attached as methods) -------------------------------------------------------------------------


def _need(cond: bool, ctx: _Ctx, path: str, key: str, msg: str, value: Any) -> None:
    if not cond:
        raise ctx.err(f"{path}.{key}" if path else key, f"{msg} (got {value!r})")


def _station_check(self: StationConfig, path: str, ctx: _Ctx) -> None:
    _need(bool(self.id.strip()), ctx, path, "id", "must be a non-empty string", self.id)


def _event_check(self: EventConfig, path: str, ctx: _Ctx) -> None:
    _need(self.origin_time_s >= 0, ctx, path, "origin_time_s", "must be >= 0", self.origin_time_s)
    _need(self.depth_km >= 0, ctx, path, "depth_km", "must be >= 0", self.depth_km)
    _need(self.amplitude > 0, ctx, path, "amplitude", "must be > 0", self.amplitude)


def _instance_check(self: InstanceEventConfig, path: str, ctx: _Ctx) -> None:
    _need(bool(self.event_id.strip()), ctx, path, "event_id", "must be non-empty", self.event_id)
    _need(self.input in ("release_hdf5", "mseed"), ctx, path, "input", "must be 'release_hdf5' or 'mseed'", self.input)
    _need(self.packet_len_samples >= 1, ctx, path, "packet_len_samples", "must be >= 1", self.packet_len_samples)
    _need(self.min_stations >= 1, ctx, path, "min_stations", "must be >= 1", self.min_stations)
    if self.stations is not None:
        _need(len(self.stations) >= 1, ctx, path, "stations", "must be a non-empty list or omitted", self.stations)


def _scenario_check(self: ScenarioConfig, path: str, ctx: _Ctx) -> None:
    sources = ("synthetic_network", "instance_event")
    _need(self.source in sources, ctx, path, "source", f"must be one of {list(sources)}", self.source)
    if self.source == "instance_event":
        _need(self.instance is not None, ctx, path, "instance", "is required when source is 'instance_event'", None)
        _need(not self.stations, ctx, path, "stations", "not used with source 'instance_event'", len(self.stations))
        _need(self.event is None, ctx, path, "event", "not used with source 'instance_event'", self.event)
        return
    _need(self.instance is None, ctx, path, "instance", "only valid with source 'instance_event'", self.instance)
    _need(self.type == "synthetic_network", ctx, path, "type", "only 'synthetic_network' is supported", self.type)
    _need(len(self.stations) >= 1, ctx, path, "stations", "needs at least one station", len(self.stations))
    ids = [s.id for s in self.stations]
    _need(len(set(ids)) == len(ids), ctx, path, "stations", "station ids must be unique", ids)
    for key, lo in (
        ("duration_s", 0),
        ("sample_rate_hz", 0),
        ("velocity_km_s", 0),
        ("pulse_freq_hz", 0),
        ("amplitude_ref_km", 0),
    ):
        v = getattr(self, key)
        _need(v > lo, ctx, path, key, f"must be > {lo}", v)
    _need(self.packet_len_samples >= 1, ctx, path, "packet_len_samples", "must be >= 1", self.packet_len_samples)
    _need(self.noise_sigma >= 0, ctx, path, "noise_sigma", "must be >= 0", self.noise_sigma)
    _need(self.coda_decay_per_s >= 0, ctx, path, "coda_decay_per_s", "must be >= 0", self.coda_decay_per_s)
    if self.event is not None:
        _need(
            self.event.origin_time_s < self.duration_s,
            ctx,
            path,
            "event.origin_time_s",
            "must be < duration_s",
            self.event.origin_time_s,
        )


def _detector_check(self: DetectorConfig, path: str, ctx: _Ctx) -> None:
    from quakenode.streaming import DetectorConfigError, validate_params

    try:
        validate_params(self.name, self.params)
    except DetectorConfigError as exc:
        raise ctx.err(path, str(exc)) from None


def _pipeline_check(self: PipelineConfig, path: str, ctx: _Ctx) -> None:
    from quakenode.streaming import GAP_POLICIES, ORDER_POLICIES

    _need(
        self.order_policy in ORDER_POLICIES,
        ctx,
        path,
        "order_policy",
        f"must be one of {list(ORDER_POLICIES)}",
        self.order_policy,
    )
    _need(
        self.gap_policy in GAP_POLICIES,
        ctx,
        path,
        "gap_policy",
        f"must be one of {list(GAP_POLICIES)}",
        self.gap_policy,
    )
    _need(self.max_wait_s >= 0, ctx, path, "max_wait_s", "must be >= 0", self.max_wait_s)
    _need(self.processing_delay_s >= 0, ctx, path, "processing_delay_s", "must be >= 0", self.processing_delay_s)
    if self.order_policy == "buffer":
        _need(
            self.max_wait_s > 0, ctx, path, "max_wait_s", "must be > 0 when order_policy is 'buffer'", self.max_wait_s
        )


def _fusion_check(self: FusionSection, path: str, ctx: _Ctx) -> None:
    from quakenode.fusion.kofn import WINDOW_CLOCKS

    _need(self.k >= 1, ctx, path, "k", "must be >= 1", self.k)
    _need(self.window_s > 0, ctx, path, "window_s", "must be > 0", self.window_s)
    _need(self.update_window_s >= 0, ctx, path, "update_window_s", "must be >= 0", self.update_window_s)
    _need(
        self.window_clock in WINDOW_CLOCKS,
        ctx,
        path,
        "window_clock",
        f"must be one of {list(WINDOW_CLOCKS)}",
        self.window_clock,
    )


def _metrics_check(self: MetricsSection, path: str, ctx: _Ctx) -> None:
    if self.event_reference is not None:
        _need(self.event_reference in ("kth_p", "earliest_p"), ctx, path, "event_reference",
              "must be 'kth_p' or 'earliest_p'", self.event_reference)  # fmt: skip
    _need(
        self.detection_pre_margin_s >= 0,
        ctx,
        path,
        "detection_pre_margin_s",
        "must be >= 0",
        self.detection_pre_margin_s,
    )
    _need(
        self.detection_post_horizon_s > 0,
        ctx,
        path,
        "detection_post_horizon_s",
        "must be > 0",
        self.detection_post_horizon_s,
    )


def _sweep_check(self: SweepSection, path: str, ctx: _Ctx) -> None:
    _need(
        1 <= len(self.parameters) <= 2,
        ctx,
        path,
        "parameters",
        "give one or two sweep parameters",
        len(self.parameters),
    )
    for i, p in enumerate(self.parameters):
        _need(len(p.values) >= 1, ctx, f"{path}.parameters[{i}]", "values", "needs at least one value", p.values)
        _need(
            bool(p.path.strip()),
            ctx,
            f"{path}.parameters[{i}]",
            "path",
            "must be a non-empty path like faults.0.p",
            p.path,
        )


def _experiment_check(self: ExperimentConfig, path: str, ctx: _Ctx) -> None:
    _need(
        self.schema_version == SCHEMA_VERSION,
        ctx,
        path,
        "schema_version",
        f"unsupported (this version reads {SCHEMA_VERSION})",
        self.schema_version,
    )
    _need(bool(self.name.strip()), ctx, path, "name", "must be non-empty", self.name)
    _need(
        len(self.seeds) >= 1 and len(set(self.seeds)) == len(self.seeds),
        ctx,
        path,
        "seeds",
        "needs at least one seed, all different",
        self.seeds,
    )
    station_ids = {s.id for s in self.scenario.stations} if self.scenario.source == "synthetic_network" else None
    for i, f in enumerate(self.faults):
        validate_fault(f, f"faults[{i}]", ctx, station_ids)


InstanceEventConfig._check = _instance_check  # type: ignore[attr-defined]
StationConfig._check = _station_check  # type: ignore[attr-defined]
EventConfig._check = _event_check  # type: ignore[attr-defined]
ScenarioConfig._check = _scenario_check  # type: ignore[attr-defined]
DetectorConfig._check = _detector_check  # type: ignore[attr-defined]
PipelineConfig._check = _pipeline_check  # type: ignore[attr-defined]
FusionSection._check = _fusion_check  # type: ignore[attr-defined]
MetricsSection._check = _metrics_check  # type: ignore[attr-defined]
SweepSection._check = _sweep_check  # type: ignore[attr-defined]
ExperimentConfig._check = _experiment_check  # type: ignore[attr-defined]


def validate_fault(f: Any, path: str, ctx: _Ctx, station_ids: set[str] | None) -> None:
    if not isinstance(f, dict):
        raise ctx.err(path, f"must be a mapping (got {type(f).__name__})")
    if "type" not in f:
        raise ctx.err(path, "missing required key 'type'")
    spec = FAULT_SPECS.get(f["type"])
    if spec is None:
        raise ctx.err(f"{path}.type", f"unknown fault type {f['type']!r}; allowed: {sorted(FAULT_SPECS)}")
    unknown = sorted(set(f) - set(FAULT_COMMON) - set(spec))
    if unknown:
        raise ctx.err(
            path, f"unknown key(s) {unknown} for fault {f['type']!r}; allowed: {sorted(set(FAULT_COMMON) | set(spec))}"
        )
    targets = f.get("targets", "all")
    if targets != "all":
        if not isinstance(targets, list) or not targets or not all(isinstance(t, str) for t in targets):
            raise ctx.err(f"{path}.targets", f"must be 'all' or a non-empty list of station ids (got {targets!r})")
        bad = [t for t in targets if station_ids is not None and t not in station_ids]
        if bad:
            raise ctx.err(f"{path}.targets", f"unknown station id(s) {bad}; scenario stations: {sorted(station_ids)}")
    for key in ("start_s", "end_s"):
        if key in f and f[key] is not None and not (_is_number(f[key]) and f[key] >= 0):
            raise ctx.err(f"{path}.{key}", f"must be a number >= 0 (got {f[key]!r})")
    if f.get("end_s") is not None and f.get("end_s") <= f.get("start_s", 0.0):
        raise ctx.err(f"{path}.end_s", f"must be greater than start_s (got {f['end_s']!r})")
    for key, fp in spec.items():
        if key not in f:
            if fp.default is None:
                raise ctx.err(path, f"fault {f['type']!r} requires key {key!r}")
            continue
        v = f[key]
        where = f"{path}.{key}"
        if fp.kind == "choice":
            if v not in fp.choices:
                raise ctx.err(where, f"must be one of {list(fp.choices)} (got {v!r})")
        elif fp.kind == "prob":
            if not (_is_number(v) and 0.0 <= v <= 1.0):
                raise ctx.err(where, f"must be between 0 and 1 (got {v!r})")
        elif fp.kind == "seconds":
            if not (_is_number(v) and v >= 0):
                raise ctx.err(where, f"must be a number >= 0 (got {v!r})")
        elif fp.kind == "int":
            if not (_is_number(v) and float(v) == int(v) and v >= 1):
                raise ctx.err(where, f"must be an integer >= 1 (got {v!r})")
        elif fp.kind == "float" and not _is_number(v):
            raise ctx.err(where, f"must be a number (got {v!r})")
    if f["type"] == "jitter":
        if f.get("distribution") == "uniform" and f.get("high_s", 0.0) < f.get("low_s", 0.0):
            raise ctx.err(f"{path}.high_s", "must be >= low_s")
        if f.get("distribution") == "exponential" and not f.get("mean_s", 0.0) > 0:
            raise ctx.err(f"{path}.mean_s", "must be > 0 for the exponential distribution")
    if f["type"] == "packet_loss" and f.get("model", "bernoulli") == "gilbert_elliott":
        if not (f.get("p_gb", 0.0) > 0 and f.get("p_bg", 0.0) > 0):
            raise ctx.err(path, "gilbert_elliott needs p_gb > 0 and p_bg > 0")


# ---- loading ----------------------------------------------------------------------------------------------------


def parse_config(data: Any, file: str = "<config>") -> ExperimentConfig:
    """Validate a raw mapping (already loaded from YAML) and return an ExperimentConfig."""
    return _build(ExperimentConfig, data, "", _Ctx(file))


def load_raw(path: str | Path) -> dict[str, Any]:
    import yaml

    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"{p}: cannot read file ({exc})") from None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{p}: invalid YAML ({exc})") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{p}: top level must be a mapping")
    return data


def load_config(path: str | Path) -> ExperimentConfig:
    return parse_config(load_raw(path), str(path))


def set_path(data: dict[str, Any], dotted: str, value: Any, create: bool = False) -> dict[str, Any]:
    """Return a deep copy of `data` with data[a][b][0][c] = value for the path 'a.b.0.c'.

    The path must exist, except that create=True may add missing KEYS of mappings (never list items); unknown keys
    are then rejected by the strict schema when the config is parsed.
    """
    out = copy.deepcopy(data)
    node: Any = out
    parts = dotted.split(".")
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if isinstance(node, list):
            if not part.isdigit() or int(part) >= len(node):
                raise ConfigError(f"sweep path {dotted!r}: no list index {part!r}")
            key: Any = int(part)
        else:
            if not isinstance(node, dict):
                raise ConfigError(f"sweep path {dotted!r}: no key {part!r}")
            if part not in node:
                if not create:
                    raise ConfigError(f"sweep path {dotted!r}: no key {part!r}")
                node[part] = {} if not last else None
            key = part
        if last:
            node[key] = value
        else:
            if create and isinstance(node, dict) and node[key] is None:
                node[key] = {}
            node = node[key]
    return out


def apply_overrides(raw: dict[str, Any], overrides: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Apply `key=value` strings (dotted paths, YAML-typed values). Returns the new mapping and the applied list."""
    import yaml

    applied = []
    for item in overrides:
        if "=" not in item:
            raise ConfigError(f"--set {item!r}: expected key=value")
        key, _, text = item.partition("=")
        key = key.strip()
        if not key:
            raise ConfigError(f"--set {item!r}: empty key")
        try:
            value = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ConfigError(f"--set {item!r}: value is not valid YAML ({exc})") from None
        raw = set_path(raw, key, value, create=True)
        applied.append({"path": key, "value": value, "source": "cli"})
    return raw, applied
