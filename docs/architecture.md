# Architecture

Research testbed, not an operational warning system. The scenario generator is **SYNTHETIC** and is not a seismological model.

## Data flow

```
 YAML config --(strict validation)--> ExperimentConfig
        |
        v   per seed
 scenario.synthetic_network   traces per station (SYNTHETIC)
        |  ReplayEngine.packetize: identical timing rules for every station
        v
 packets [Packet: sample time, ready time, arrival time]
        |
        v  faults.apply_faults (declared order, per-fault seeds)  ----> FaultRecord per fault
 faulted packets (delay, jitter, loss, duplicate, reorder, outage, clock offset, missing samples)
        |
        v  ReplayEngine.schedule + advance_to(t): only packets with arrival_time <= t are delivered
 delivered packets
        |
        v  streaming.StreamingPipeline (order policy: reject | drop_late | buffer)
 per-station StreamDetector.process(packet)  ----> Detection [sample, ready, arrival, emission times]
        |                                      ----> GapEvent / DroppedPacket
        v
 fusion.fuse (k-of-n on the emission clock)  ----> Candidate + FusionDecision per step
        |
        v
 evaluation (metrics vs synthetic truth) --> metrics.json / metrics.csv / report.md / plots
 everything logged to events.jsonl; manifest.json records config, seeds, git commit, versions
```

A detector never receives the full trace: the receiver view only holds delivered packets, and the pipeline only calls
a detector with in-order packets.

## Clocks (never merged)

| clock | meaning | where |
|---|---|---|
| **sample** | time of a sample at the sensor: `index / sample_rate` | `Packet.first_sample_time_s`, `Detection.trigger_sample_time_s` |
| **ready** | when the last sample of a packet exists at the sensor (>= its sample time) | `Packet.ready_time_s`, `Detection.trigger_ready_time_s` |
| **arrival** | simulated arrival of the packet at the receiver (>= ready time); faults move it | `Packet.arrival_time_s`, `Detection.arrival_time_s` |
| **emission** | simulated time the detector emitted: processing time + processing delay, where processing time is the packet's arrival, or later if a reordering buffer held it | `Detection.emission_time_s` |

`clock_offset` models a mis-set sensor clock without touching the true sample clock: the shifted timestamp is stored in
`Packet.reported_first_sample_time_s` and `Detection.reported_trigger_sample_time_s`; truth-based metrics use the true
sample time and report the difference as `reported_timestamp_error_s`.

## Scenario sources

`scenario.source` is `synthetic_network` (generated in-process) or `instance_event` (a real recorded INSTANCE event,
extra `data`; the user supplies the data). Both produce the same packets, truths and labels, so faults, pipeline,
fusion and metrics are identical. Real events place all stations on one clock (zero = earliest trace start) and use
the catalog P sample per station as the reference; the input kind (`release_hdf5` = full-window processed release
product, NOT causal input; `mseed` = raw INGV miniSEED) is carried into every output.

## Assumptions that matter

- **Fusion clock.** The k-of-n window is measured on the emission clock (default) or the arrival clock, never on the
  sample clock. A fusion centre only knows when detections reach it; a delayed detection counts late. Candidate
  creation time is on the emission clock.
- **Gap policy** (`pipeline.gap_policy`, `docs/gap_policies.md`). A packet that starts after the next expected sample
  leaves a gap and a `GapEvent` is always recorded. `reset` (default) resets the detector, which then re-warms (for a
  detector with an LTA, loss is expensive: it is blind for one warm-up length after every gap); `hold` keeps state and
  inserts nothing; `zero_fill` inserts labeled zeros. Nothing is interpolated.
- **Out-of-order policy** (`pipeline.order_policy`): `reject` raises on duplicate/late packets; `drop_late` drops them
  and records `DroppedPacket`; `buffer` holds packets that start after the expected index for up to `max_wait_s` of
  simulated time. If the missing packet arrives in time the data are released in order (emission is delayed by the
  wait, exactly the arrival difference); otherwise a gap is declared at the deadline. A packet arriving after its gap
  was declared is dropped.
- **Fault intervals** are on the ready clock; random choices come from per-fault seeds derived from the run seed, the
  fault index and type, using only `random.Random(seed).random()` (identical on Python 3.10 to 3.12).
- **Packet loss models.** `bernoulli`: independent loss. `gilbert_elliott`: a two-state Markov chain per station stream
  advanced once per packet in sequence order, starting good; mean burst length is `1 / p_bg` packets when `loss_bad = 1`.
- **Missing samples** remove the last `n_samples` of a packet (a digitizer dropout); the pipeline then sees a gap.
- **Control scenario.** An explicit run with `faults: []` and the same seeds; sweeps pair every point with it.

## Extending

- **Detector:** implement `quakenode.streaming.StreamDetector` (`name`, `version`, `warmup_s`, `warming_up`,
  `reset()`, `process(packet, processed_at_s)` returning `Detection`s) and register a `DetectorSpec` with a parameter
  table (see `streaming/registry.py`); then name it in the config. Built in: `sta_lta_rms`, `recursive_sta_lta`.
- **Fault:** a frozen dataclass with `type` and `apply(packets, seed) -> (packets, FaultRecord)`, built with
  `faults.base.make_record`; add its parameter spec to `config.FAULT_SPECS` and a branch in
  `experiment.build_fault`.
