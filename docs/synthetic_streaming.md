# Synthetic streaming experiment

Research prototype, not an operational warning system. Everything below uses **synthetic** signals and supports **software-invariant claims only**. Nothing here says anything about real seismic data, detector performance, or warning time.

## What was run

```bash
python experiments/synthetic_streaming.py          # text table
python experiments/synthetic_streaming.py --json   # JSON with manifest, provenance, results_sha256
```

- Signals: the four cases of `experiments/synthetic_causality.py` (trended_event, flat_event, quiet_noise_control, trend_only_control), the same 12 seeds (202601 to 202612), 20 s at 100 Hz, P at sample 800 (8.0 s).
- Path: only the causal arm. `ReplayEngine.packetize` -> `ReplayEngine.schedule` -> `StreamingPipeline.run` (streaming one-pole high-pass, alpha from fc = 0.5 Hz, followed by streaming RMS STA/LTA: STA 10 samples, preceding LTA 100 samples, threshold 3.0, first trigger only, warm-up 0, processing delay 0.0).
- Packet sizes: 1, 10 and 100 samples. Packets are ready at the time of their last sample and arrive at that time (no delay) unless a scenario says otherwise.
- Scenarios:
  - `nominal`: no faults.
  - `dropped_packet_before_p`: the single packet containing sample 500 (5.0 s) is removed. Software stress test, not a network model.
  - `fixed_delay`: every packet's arrival is shifted by 0.5 s. Software stress test, not a network model.
- Metrics (definition label `synthetic_streaming_v1`):
  - hit: the first emitted detection has `trigger_sample_index` in [P, P + 2 s]; miss: an event trace without a hit (this includes a first trigger before P, matching the batch script); false trigger: any detection on a no-event trace.
  - `=batch`: the streaming first-trigger index equals the first-trigger index of the batch path (`causal_baseline` on the whole trace, then `fixed_sta_lta_first_trigger`) on the same raw signal.
  - emission latency: `emission_time_s - 8.0 s` over hit traces. This is **synthetic detector delay** (sample-clock detection delay plus packetization wait plus any fixed delay), not warning time.

## Measured results

Run on Python 3.11.17 from the committed code. `results_sha256` of the JSON results: `de8d6a9bc8b1f33f87adbdcf588b3411d0a122e1ba82d16ca077fe41a4dbefe3` (it excludes the manifest and provenance, so it stays the same across repeated runs of the same code).

| scenario | packet size | hits (both event cases) | misses | false triggers (both controls) | = batch | emission latency, mean (min to max), s |
|---|---|---|---|---|---|---|
| nominal | 1 | 12/12 each | 0 | 0/12 each | 12/12 in all four cases | 0.024 (0.020 to 0.030) |
| nominal | 10 | 12/12 each | 0 | 0/12 each | 12/12 | 0.090 (0.090 to 0.090) |
| nominal | 100 | 12/12 each | 0 | 0/12 each | 12/12 | 0.990 (0.990 to 0.990) |
| dropped_packet_before_p | 1, 10, 100 | 12/12 each | 0 | 0/12 each | 12/12 | identical to nominal |
| fixed_delay (0.5 s) | 1 | 12/12 each | 0 | 0/12 each | 12/12 | 0.524 (0.520 to 0.530) |
| fixed_delay (0.5 s) | 10 | 12/12 each | 0 | 0/12 each | 12/12 | 0.590 |
| fixed_delay (0.5 s) | 100 | 12/12 each | 0 | 0/12 each | 12/12 | 1.490 |

Both event cases give the same latency numbers at each packet size. Per-case and per-seed rows are in the `--json` output.

## Reading the results

- Streaming through the replay engine reproduces the batch causal first-trigger index exactly at all tested packet sizes (also tested at 7, 50 and 2000 samples in `tests/test_streaming.py`). This is the check that the aggregate experiment now runs through chunked delivery.
- The latency grows with packet size because a trigger cannot be emitted before the packet holding the triggering sample has arrived: with 100-sample packets, P (sample 800) falls at the start of a packet that is only complete at 8.99 s.
- A fixed delay changes only the arrival and emission clocks; the trigger sample index and sample time are unchanged (also asserted bit-for-bit in the tests).
- The dropped packet had **no effect on the outcome** here. This is expected, not a robustness finding: the gap is 3 s before P, the filter and the STA/LTA buffer re-warm within about 1.1 s plus the filter's transient, and the controls stay quiet. The tests in `tests/test_streaming.py` show that a gap that removes the pulse, or its onset, produces a miss (the detector needs 110 samples after the reset).

## Gap and ordering policy (as implemented)

A gap is never filled or interpolated. It records a `GapEvent`, resets the filter and the detector buffer, and re-warms from the next packet; a detector that already fired stays fired. Duplicate, overlapping or out-of-order packets raise `StreamOrderError` (no reordering buffer), so a packet that arrives after a later one is first seen as a gap and then rejected.

## Limitations

- Synthetic signals with a hand-designed pulse; one detector configuration chosen in Phase 1; no real waveforms.
- The stress scenarios are single, fixed software faults. They are not models of any real network, and no jitter, loss rate, reordering or clock error is modelled.
- **Assumption:** `trigger_ready_time_s` is defined as the trigger sample's time plus (packet `ready_time_s` minus the packet's last-sample time), i.e. it assumes sensor latency is constant within a packet. It is a modelling assumption, not a measurement. In these runs it equals the sample time, because the packetizer sets ready time to the last sample's time.
- Latency numbers are properties of this toy signal and packetization, not of earthquake early warning.
- Equivalence with the batch path is bit-for-bit only because the streaming STA/LTA recomputes its window sums from a ring buffer in the same order as the batch code; it is O(window) per sample.
