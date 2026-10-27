"""Detector registry: build detector factories by name from validated config parameters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quakenode.streaming.detectors import RecursiveStaLtaDetector, StaLtaRmsDetector, alpha_from_cutoff
from quakenode.streaming.protocol import DetectorFactory


class DetectorConfigError(ValueError):
    """Unknown detector name, unknown parameter, or a parameter out of range."""


@dataclass(frozen=True)
class Param:
    kind: type  # float, int or bool
    default: Any
    minimum: float | None = None
    exclusive_min: bool = False
    doc: str = ""


@dataclass(frozen=True)
class DetectorSpec:
    name: str
    params: dict[str, Param]
    build: Callable[[dict[str, Any], float], DetectorFactory]  # (validated params, processing_delay_s) -> factory
    doc: str = ""


_REGISTRY: dict[str, DetectorSpec] = {}


def register_detector(spec: DetectorSpec) -> None:
    """Register a detector spec. Names must be unique."""
    if spec.name in _REGISTRY:
        raise ValueError(f"detector {spec.name!r} is already registered")
    _REGISTRY[spec.name] = spec


def available_detectors() -> list[str]:
    return sorted(_REGISTRY)


def validate_params(name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Return params with defaults filled; raise DetectorConfigError naming the bad key."""
    spec = _REGISTRY.get(name)
    if spec is None:
        raise DetectorConfigError(f"unknown detector {name!r}; available: {available_detectors()}")
    unknown = sorted(set(params) - set(spec.params))
    if unknown:
        raise DetectorConfigError(f"detector {name!r}: unknown parameter(s) {unknown}; allowed: {sorted(spec.params)}")
    out: dict[str, Any] = {}
    for key, p in spec.params.items():
        value = params.get(key, p.default)
        if p.kind is bool:
            if not isinstance(value, bool):
                raise DetectorConfigError(f"detector {name!r}: parameter {key!r} must be true/false, got {value!r}")
        else:
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise DetectorConfigError(f"detector {name!r}: parameter {key!r} must be a number, got {value!r}")
            if p.kind is int and float(value) != int(value):
                raise DetectorConfigError(f"detector {name!r}: parameter {key!r} must be an integer, got {value!r}")
            value = p.kind(value)
            if p.minimum is not None and (value < p.minimum or (p.exclusive_min and value == p.minimum)):
                op = ">" if p.exclusive_min else ">="
                raise DetectorConfigError(f"detector {name!r}: parameter {key!r} must be {op} {p.minimum}, got {value}")
        out[key] = value
    return out


def create_detector_factory(name: str, params: dict[str, Any], processing_delay_s: float = 0.0) -> DetectorFactory:
    checked = validate_params(name, params)
    return _REGISTRY[name].build(checked, processing_delay_s)


def _build_rms(p: dict[str, Any], delay: float) -> DetectorFactory:
    def factory(station_id: str, channel_id: str, rate_hz: float):
        return StaLtaRmsDetector(
            alpha=alpha_from_cutoff(p["highpass_cutoff_hz"], rate_hz),
            warmup_samples=round(p["warmup_s"] * rate_hz),
            sta_samples=round(p["sta_s"] * rate_hz),
            lta_samples=round(p["lta_s"] * rate_hz),
            threshold=p["threshold"],
            processing_delay_s=delay,
            sample_rate_hz=rate_hz,
        )

    return factory


def _build_recursive(p: dict[str, Any], delay: float) -> DetectorFactory:
    def factory(station_id: str, channel_id: str, rate_hz: float):
        cutoff = p["baseline_cutoff_hz"]
        return RecursiveStaLtaDetector(
            nsta=round(p["sta_s"] * rate_hz),
            nlta=round(p["lta_s"] * rate_hz),
            threshold_on=p["threshold_on"],
            threshold_off=p["threshold_off"],
            rearm=p["rearm"],
            baseline_alpha=alpha_from_cutoff(cutoff, rate_hz) if cutoff > 0 else None,
            processing_delay_s=delay,
            sample_rate_hz=rate_hz,
        )

    return factory


register_detector(
    DetectorSpec(
        "sta_lta_rms",
        {
            "highpass_cutoff_hz": Param(float, 0.5, 0.0, True, "one-pole baseline removal cutoff"),
            "warmup_s": Param(float, 0.0, 0.0, False, "extra scoring warm-up (s)"),
            "sta_s": Param(float, 0.5, 0.0, True, "STA window (s)"),
            "lta_s": Param(float, 5.0, 0.0, True, "preceding LTA window (s)"),
            "threshold": Param(float, 3.0, 0.0, True, "ratio threshold (first trigger only)"),
        },
        _build_rms,
        "Causal one-pole baseline removal + RMS STA/LTA, first trigger only.",
    )
)
register_detector(
    DetectorSpec(
        "recursive_sta_lta",
        {
            "sta_s": Param(float, 0.5, 0.0, True),
            "lta_s": Param(float, 5.0, 0.0, True),
            "threshold_on": Param(float, 3.0, 0.0, True),
            "threshold_off": Param(float, 1.5, 0.0, True),
            "rearm": Param(bool, True),
            "baseline_cutoff_hz": Param(float, 0.5, 0.0, False, "one-pole baseline removal cutoff; 0 disables"),
        },
        _build_recursive,
        "Recursive STA/LTA on squared samples with on/off thresholds (public definition).",
    )
)
