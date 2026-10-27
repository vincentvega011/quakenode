"""Streaming (causal, packet-driven) preprocessing, detection and the pipeline tying them to replay."""

from quakenode.streaming.detectors import RecursiveStaLtaDetector, StaLtaRmsDetector
from quakenode.streaming.onepole import StreamingOnePoleHighpass
from quakenode.streaming.pipeline import (
    GAP_POLICIES,
    ORDER_POLICIES,
    DroppedPacket,
    GapEvent,
    ProcessedPacket,
    StreamingPipeline,
    StreamOrderError,
)
from quakenode.streaming.protocol import DetectorFactory, StreamDetector
from quakenode.streaming.registry import (
    DetectorConfigError,
    DetectorSpec,
    Param,
    available_detectors,
    create_detector_factory,
    register_detector,
    validate_params,
)
from quakenode.streaming.sta_lta import DETECTOR_NAME, DETECTOR_VERSION, StaLtaOutput, StreamingStaLta

__all__ = [
    "DETECTOR_NAME",
    "DETECTOR_VERSION",
    "GAP_POLICIES",
    "ORDER_POLICIES",
    "DetectorConfigError",
    "DetectorFactory",
    "DetectorSpec",
    "DroppedPacket",
    "GapEvent",
    "Param",
    "ProcessedPacket",
    "RecursiveStaLtaDetector",
    "StaLtaOutput",
    "StaLtaRmsDetector",
    "StreamDetector",
    "StreamOrderError",
    "StreamingOnePoleHighpass",
    "StreamingPipeline",
    "StreamingStaLta",
    "available_detectors",
    "create_detector_factory",
    "register_detector",
    "validate_params",
]
