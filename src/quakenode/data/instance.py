"""Adapters for the INSTANCE release arrays and the original INGV miniSEED (needs the `data` extra).

h5py, numpy and obspy are imported inside functions, so `import quakenode` and `import quakenode.data` work
without them; calling a loader without the extra raises MissingExtraError with the install command.

Documented facts the code relies on (see docs/instance_access.md, docs/instance_preprocessing_facts.md):
  * release HDF5 `data/<trace_name>` has shape (3, 12000), int32, component order ENZ (file-level
    `data_format/component_order`), so row 2 is Z;
  * `trace_start_time` is a UTC string with two decimals (a 10 ms rounded value); the window is aligned to the
    NEAREST raw sample to that time, with no shifting; the sub-sample offset is reported, never applied;
  * `trace_P_arrival_sample` is used as the authoritative P sample. It differs by one sample (10 ms) from the
    sample implied by `trace_P_arrival_time` in about 22% of the sample's rows; that is negligible against the
    stated P-pick uncertainty (1 s in the rows inspected) but is a sensitivity item for the protocol.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quakenode.replay import Packet, ReplayEngine, Trace

EXCLUSION_REASONS = (
    "fetch_failed",
    "native_rate_not_100hz",
    "gaps_or_overlaps",
    "raw_does_not_cover_window",
)
Z_INDEX = 2
EXPECTED_COMPONENT_ORDER = "ENZ"


class MissingExtraError(ImportError):
    """Raised when an optional dependency of the data adapters is not installed."""


def _require(module: str) -> Any:
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise MissingExtraError(
            f"{module!r} is required for this function; install the optional extra: pip install 'quakenode[data]'"
        ) from exc


def parse_utc_ns(text: str) -> int:
    """'2016-12-04T16:23:14.51Z' (0 to 9 fractional digits, trailing Z) -> integer nanoseconds since the epoch."""
    if not text.endswith("Z"):
        raise ValueError(f"expected a trailing Z: {text!r}")
    base, _, frac = text[:-1].partition(".")
    if frac and (not frac.isdigit() or len(frac) > 9):
        raise ValueError(f"bad fractional seconds: {text!r}")
    dt = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp()) * 1_000_000_000 + int(frac.ljust(9, "0") or 0)


def load_release_z(hdf5_path: str | Path, trace_name: str) -> Any:
    """Z component of a release trace as an int32 numpy array (row 2 of the (3, N) array, order ENZ).

    Raises ValueError if the file's component order is not ENZ, the shape is not (3, N) or the dtype is not int32;
    KeyError if the trace is missing.
    """
    h5py = _require("h5py")
    with h5py.File(hdf5_path, "r") as h5:
        order = h5["data_format/component_order"][()]
        order = order.decode() if isinstance(order, bytes) else str(order)
        if order != EXPECTED_COMPONENT_ORDER:
            raise ValueError(f"unexpected component_order {order!r} in {hdf5_path}")
        if trace_name not in h5["data"]:
            raise KeyError(f"trace {trace_name!r} not in {hdf5_path}")
        ds = h5["data"][trace_name]
        if ds.ndim != 2 or ds.shape[0] != 3:
            raise ValueError(f"expected shape (3, N), got {ds.shape} for {trace_name}")
        if str(ds.dtype) != "int32":
            raise ValueError(f"expected int32, got {ds.dtype} for {trace_name}")
        return ds[Z_INDEX].copy()


@dataclass(frozen=True)
class RawWindow:
    """Result of cutting the raw window. Exactly one of `samples` and `exclusion_reason` is set."""

    samples: Any | None  # numpy array on the raw grid, not modified
    exclusion_reason: str | None  # one of EXCLUSION_REASONS
    detail: str = ""
    first_raw_index: int | None = None  # index of the first window sample in the raw trace
    offset_samples: float | None = None  # (metadata start - raw grid point) / dt, in [-0.5, 0.5]; reported, not applied
    raw_start_ns: int | None = None
    n_traces_in_file: int | None = None

    def require(self) -> Any:
        if self.exclusion_reason is not None:
            raise ValueError(f"raw window excluded: {self.exclusion_reason} ({self.detail})")
        return self.samples


def _excluded(reason: str, detail: str = "", **kw: Any) -> RawWindow:
    return RawWindow(samples=None, exclusion_reason=reason, detail=detail, **kw)


def load_raw_window(mseed_path: str | Path, start_time_utc: str, n_samples: int, rate_hz: float) -> RawWindow:
    """Cut n_samples from a raw miniSEED file starting at the raw sample nearest to start_time_utc.

    Never silent: an unusable file yields a RawWindow with an explicit `exclusion_reason`:
      fetch_failed             file missing, empty or unreadable
      native_rate_not_100hz    any trace in the file has a sampling rate different from rate_hz
      gaps_or_overlaps         more than one trace and no single trace covers the whole window (or several do)
      raw_does_not_cover_window  a single trace that is too short at the start or end
    Segments outside the window do not matter. Samples are returned as stored (no scaling, no demeaning).
    """
    np = _require("numpy")
    obspy = _require("obspy")
    path = Path(mseed_path)
    if not path.exists() or path.stat().st_size == 0:
        return _excluded("fetch_failed", f"{path} missing or empty")
    try:
        st = obspy.read(str(path))
    except Exception as exc:
        return _excluded("fetch_failed", f"unreadable miniSEED: {type(exc).__name__}: {exc}")
    if len(st) == 0:
        return _excluded("fetch_failed", "no traces in file")
    rates = {float(tr.stats.sampling_rate) for tr in st}
    if rates != {float(rate_hz)}:
        return _excluded("native_rate_not_100hz", f"rates in file: {sorted(rates)}", n_traces_in_file=len(st))
    dt_ns = round(1e9 / rate_hz)
    start_ns = parse_utc_ns(start_time_utc)
    covering = []
    for tr in st:
        t0 = tr.stats.starttime.ns
        k0 = round((start_ns - t0) / dt_ns)
        if k0 >= 0 and k0 + n_samples <= tr.stats.npts:
            covering.append((tr, t0, k0))
    n_tr = len(st)
    if len(covering) == 1:
        tr, t0, k0 = covering[0]
        samples = np.array(tr.data[k0 : k0 + n_samples])
        return RawWindow(
            samples=samples,
            exclusion_reason=None,
            first_raw_index=k0,
            offset_samples=(start_ns - t0) / dt_ns - k0,
            raw_start_ns=t0,
            n_traces_in_file=n_tr,
        )
    if len(covering) > 1:
        return _excluded("gaps_or_overlaps", "several traces cover the window (overlap)", n_traces_in_file=n_tr)
    reason = "raw_does_not_cover_window" if n_tr == 1 else "gaps_or_overlaps"
    return _excluded(reason, f"{n_tr} trace(s); none covers the {n_samples}-sample window", n_traces_in_file=n_tr)


def make_stream_packets(
    samples: Any,
    *,
    station_id: str,
    channel_id: str,
    sample_rate_hz: float,
    packet_len_samples: int,
    delay_s: float = 0.0,
    first_sample_index: int = 0,
) -> list[Packet]:
    """Packetize window samples (sample 0 at window time 0) with the replay engine's packetizer.

    first_sample_index places the record on a shared multi-station timeline (default 0).
    Both arms of a comparison must call this with identical arguments so that packet boundaries and the sample,
    ready and arrival clocks are identical and only sample values differ.
    """
    values = tuple(float(x) for x in samples)
    trace = Trace(station_id, channel_id, sample_rate_hz, values, first_sample_index)
    return ReplayEngine.packetize(trace, packet_len_samples, delay_s)


@dataclass(frozen=True)
class TraceRecord:
    """Metadata of one cohort trace (from the INSTANCE events CSV) plus source hashes."""

    trace_name: str
    event_id: str
    network: str
    station: str
    location: str
    channel_family: str
    trace_start_time: str
    p_sample: int  # trace_P_arrival_sample, authoritative (see module docstring)
    p_arrival_time: str
    p_uncertainty_s: float | None
    magnitude: float | None
    epicentral_distance_km: float | None
    release_hdf5_sha256: str | None = None
    raw_mseed_sha256: str | None = None
    extra: dict[str, str] = field(default_factory=dict, compare=False)

    @property
    def p_time_in_window_s(self) -> float:
        return self.p_sample / 100.0

    @classmethod
    def from_metadata_row(
        cls, row: dict[str, str], release_hdf5_sha256: str | None = None, raw_mseed_sha256: str | None = None
    ) -> TraceRecord:
        def num(key: str) -> float | None:
            v = row.get(key, "")
            return float(v) if v not in ("", None) else None

        parts = row["trace_name"].split(".")
        if len(parts) != 5:
            raise ValueError(f"unexpected trace_name {row['trace_name']!r}")
        if not row.get("trace_P_arrival_sample"):
            raise ValueError(f"{row['trace_name']}: missing trace_P_arrival_sample")
        return cls(
            trace_name=row["trace_name"],
            event_id=row["source_id"],
            network=parts[1],
            station=parts[2],
            location=parts[3],
            channel_family=parts[4],
            trace_start_time=row["trace_start_time"],
            p_sample=int(float(row["trace_P_arrival_sample"])),
            p_arrival_time=row["trace_P_arrival_time"],
            p_uncertainty_s=num("trace_P_uncertainty_s"),
            magnitude=num("source_magnitude"),
            epicentral_distance_km=num("path_ep_distance_km"),
            release_hdf5_sha256=release_hdf5_sha256,
            raw_mseed_sha256=raw_mseed_sha256,
        )
