"""Built-in streaming detectors.

* StaLtaRmsDetector: causal one-pole baseline removal + RMS STA/LTA, first trigger only (the Phase 1 detector).
* RecursiveStaLtaDetector: recursive STA/LTA on squared samples, implemented from the public definition
  (Withers et al. 1998; the same recursion as ObsPy's `recursive_sta_lta_py`, read from the installed ObsPy), with
  threshold-on / threshold-off re-arming.
"""

from __future__ import annotations

from quakenode.preprocessing import one_pole_alpha
from quakenode.replay import Detection, Packet
from quakenode.streaming.onepole import StreamingOnePoleHighpass
from quakenode.streaming.sta_lta import DETECTOR_NAME, DETECTOR_VERSION, StreamingStaLta

RECURSIVE_NAME = "recursive_sta_lta"
RECURSIVE_VERSION = "1"
TINY = 2.2250738585072014e-308  # numpy.finfo(float).tiny, as in ObsPy's avoid-zero-division constant


def _detection(
    packet: Packet,
    k: int,
    *,
    processed_at_s: float,
    processing_delay_s: float,
    name: str,
    version: str,
    ratio: float,
    threshold: float,
    parameters: tuple[tuple[str, float | int], ...],
) -> Detection:
    sensor_latency_s = packet.ready_time_s - packet.sample_time_s(len(packet.samples) - 1)
    sample_time = packet.sample_time_s(k)
    return Detection(
        station_id=packet.station_id,
        channel_id=packet.channel_id,
        trigger_sample_index=packet.first_sample_index + k,
        trigger_sample_time_s=sample_time,
        trigger_ready_time_s=sample_time + sensor_latency_s,
        arrival_time_s=packet.arrival_time_s,
        emission_time_s=processed_at_s + processing_delay_s,
        processing_delay_s=processing_delay_s,
        detector_name=name,
        detector_version=version,
        ratio=ratio,
        threshold=threshold,
        parameters=parameters,
        reported_trigger_sample_time_s=packet.reported_sample_time_s(k),
    )


class StaLtaRmsDetector:
    """One-pole baseline removal, then RMS STA/LTA (preceding non-overlapping LTA). Emits once, never re-arms."""

    name = DETECTOR_NAME
    version = DETECTOR_VERSION

    def __init__(
        self,
        *,
        alpha: float,
        warmup_samples: int,
        sta_samples: int,
        lta_samples: int,
        threshold: float,
        processing_delay_s: float = 0.0,
        sample_rate_hz: float = 100.0,
    ) -> None:
        self._filt = StreamingOnePoleHighpass(alpha, warmup_samples)
        self._det = StreamingStaLta(sta_samples, lta_samples, threshold)
        self.processing_delay_s = processing_delay_s
        self.warmup_s = max(warmup_samples, sta_samples + lta_samples) / sample_rate_hz
        self._params = (
            ("sta_samples", sta_samples),
            ("lta_samples", lta_samples),
            ("alpha", alpha),
            ("warmup_samples", warmup_samples),
        )
        self.threshold = threshold
        self.last_filtered: tuple[float, ...] | None = None
        self.last_scorable: tuple[bool, ...] | None = None

    @property
    def warming_up(self) -> bool:
        return self._filt.warming_up or not self._det.buffer_full

    def reset(self) -> None:
        self._filt.reset()
        self._det.reset()  # `fired` is kept: first-trigger semantics, no re-arming even after a gap

    def process(self, packet: Packet, processed_at_s: float | None = None) -> list[Detection]:
        at = packet.arrival_time_s if processed_at_s is None else processed_at_s
        filtered, scorable = self._filt.process(packet.samples)
        self.last_filtered, self.last_scorable = tuple(filtered), tuple(scorable)
        found = []
        for k, (y, ok) in enumerate(zip(filtered, scorable, strict=True)):
            out = self._det.update(y, ok)
            if out.triggered:
                found.append(
                    _detection(
                        packet,
                        k,
                        processed_at_s=at,
                        processing_delay_s=self.processing_delay_s,
                        name=self.name,
                        version=self.version,
                        ratio=out.ratio,
                        threshold=self.threshold,
                        parameters=self._params,
                    )
                )
        return found


class RecursiveStaLtaDetector:
    """Recursive STA/LTA on squared (baseline-removed) samples with threshold-on / threshold-off re-arming.

    Recursion (public definition): sta = sta + (x^2 - sta)/nsta, lta = lta + (x^2 - lta)/nlta in the equivalent
    form `sta = csta*x^2 + (1-csta)*sta`; ratio = sta/lta. As in ObsPy, the first sample after (re)start only
    advances the sample counter, and the ratio is treated as 0 for the first nlta samples (warm-up). A detection is
    emitted when the ratio rises to >= threshold_on while armed; the detector is disarmed until the ratio falls to
    <= threshold_off (set rearm=False for first trigger only).
    """

    name = RECURSIVE_NAME
    version = RECURSIVE_VERSION

    def __init__(
        self,
        *,
        nsta: int,
        nlta: int,
        threshold_on: float,
        threshold_off: float,
        rearm: bool = True,
        baseline_alpha: float | None = None,
        processing_delay_s: float = 0.0,
        sample_rate_hz: float = 100.0,
    ) -> None:
        if nsta < 1 or nlta <= nsta:
            raise ValueError("require 1 <= nsta < nlta")
        if not 0.0 < threshold_off < threshold_on:
            raise ValueError("require 0 < threshold_off < threshold_on")
        self.nsta, self.nlta = nsta, nlta
        self.threshold_on, self.threshold_off, self.rearm = threshold_on, threshold_off, rearm
        self.processing_delay_s = processing_delay_s
        self._filt = StreamingOnePoleHighpass(baseline_alpha, 0) if baseline_alpha is not None else None
        self.warmup_s = nlta / sample_rate_hz
        self._params = (
            ("nsta", nsta),
            ("nlta", nlta),
            ("threshold_off", threshold_off),
            ("baseline_alpha", baseline_alpha if baseline_alpha is not None else 0.0),
        )
        self.last_filtered: tuple[float, ...] | None = None
        self.last_scorable: tuple[bool, ...] | None = None
        self.last_ratios: tuple[float, ...] = ()
        self.fired_once = False
        self.reset()

    @property
    def warming_up(self) -> bool:
        return self._n < self.nlta

    def reset(self) -> None:
        self._sta, self._lta, self._n, self._armed = 0.0, TINY, 0, True
        if self._filt is not None:
            self._filt.reset()

    def process(self, packet: Packet, processed_at_s: float | None = None) -> list[Detection]:
        at = packet.arrival_time_s if processed_at_s is None else processed_at_s
        samples = self._filt.process(packet.samples)[0] if self._filt is not None else list(packet.samples)
        self.last_filtered = tuple(samples)
        csta, clta = 1.0 / self.nsta, 1.0 / self.nlta
        found, scorable, ratios = [], [], []
        for k, x in enumerate(samples):
            if self._n >= 1:  # the first sample after (re)start is not folded into the averages (as in ObsPy)
                sq = x * x
                self._sta = csta * sq + (1.0 - csta) * self._sta
                self._lta = clta * sq + (1.0 - clta) * self._lta
            ratio = self._sta / self._lta if self._n >= self.nlta else 0.0
            self._n += 1
            ratios.append(ratio)
            scorable.append(self._n > self.nlta)
            if ratio <= self.threshold_off:
                self._armed = True
            elif self._armed and ratio >= self.threshold_on and not (self.fired_once and not self.rearm):
                self._armed = False
                self.fired_once = True
                found.append(
                    _detection(
                        packet,
                        k,
                        processed_at_s=at,
                        processing_delay_s=self.processing_delay_s,
                        name=self.name,
                        version=self.version,
                        ratio=ratio,
                        threshold=self.threshold_on,
                        parameters=self._params,
                    )
                )
        self.last_scorable = tuple(scorable)
        self.last_ratios = tuple(ratios)
        return found


def alpha_from_cutoff(cutoff_hz: float, sample_rate_hz: float) -> float:
    return one_pole_alpha(cutoff_hz, sample_rate_hz)
