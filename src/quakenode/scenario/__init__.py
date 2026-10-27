"""SYNTHETIC scenario generators (not seismological models)."""

from quakenode.scenario.synthetic_network import (
    EventSpec,
    NetworkSpec,
    StationSpec,
    build_packets,
    generate_trace,
    p_arrival_time_s,
)

__all__ = ["EventSpec", "NetworkSpec", "StationSpec", "build_packets", "generate_trace", "p_arrival_time_s"]
