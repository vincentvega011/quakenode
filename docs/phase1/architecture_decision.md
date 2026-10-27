# QuakeNode minimum experiment architecture

**Decision date:** 2026-10-26  
**Status:** design proposal; no application code exists and no implementation is performed by this decision.  
**Design target:** the preregistered HNZ packet-loss detector experiment in evaluation_protocol.md.

## 1. Repository evidence and design boundary

The inspected workspace contains context.md and Phase 1 documents/config only; there is no README, package metadata, source code, tests, CI, lockfile, or existing module architecture. There are no application modules to preserve or reuse. The workspace is also not a Git worktree, so a code revision cannot currently be recorded; initialize version control before implementation or define a source-tree digest, then require that identifier in each run manifest.

The project context proposes a Python research prototype, single process, modular adapters and explicit time semantics. It is not an existing runtime commitment. The data feasibility report identifies INSTANCE v3 as the primary candidate but leaves sample access, HNZ field coverage, exact schema, checksum and usable trace joins for pre-run verification. The architecture includes a hard validation gate for those unknowns and does not attempt the broader aspirational testbed.

## 2. Smallest end-to-end flow

    INSTANCE v3 sample + metadata
               |
               v
    schema/license/checksum validation
               |
               v
    eligible HNZ event/noise trace, one at a time
               |
               v
    trace-start-anchored 1 s packetizer
               |
               v
    deterministic fault plan -> packet arrivals on virtual clock
               |
               v
    causal STA/LTA consumes only arrived packets
               |
               v
    per-trace detections + explicit time fields
               |
               v
    P-pick matching / RDT / misses / noise false-trigger denominator
               |
               v
    run manifest + event-level CSV + summary JSON

Run traces independently and serially. No fusion, event association, alert state machine, async worker, message broker, web service, or distributed execution is needed.

## 3. Proposed repository structure

This follows the inspected repository, which has no code tree to extend. It adds only the package, tests, data-free fixtures, and outputs required by the protocol.

    quake/
    ├── context.md
    ├── docs/phase1/
    │   ├── architecture_decision.md
    │   ├── evaluation_protocol.md
    │   ├── dataset_feasibility.md
    │   ├── prior_art_audit.md
    │   ├── prior_art_matrix.csv
    │   ├── repository_reconnaissance.md
    │   ├── research_gap_decision.md
    │   └── adr/0001-minimum-research-prototype.md
    ├── experiments/
    │   ├── configs/phase1_protocol.yaml
    │   └── results/                 # local generated results; not committed by default
    ├── src/quakenode/
    │   ├── __init__.py
    │   ├── cli.py
    │   ├── config.py
    │   ├── types.py
    │   ├── data/instance.py
    │   ├── replay.py
    │   ├── faults.py
    │   ├── detectors/stalta.py
    │   ├── evaluation.py
    │   └── reporting.py
    ├── tests/
    │   ├── unit/
    │   ├── integration/
    │   └── fixtures/synthetic_case.json
    ├── pyproject.toml
    └── .gitignore

No fusion module should be created for this experiment. A future fusion adapter can be added only after a multi-station question and a validated join cohort exist. The fixture contains no third-party waveforms; it is a deterministic software fixture, not seismic validation data.

## 4. Module responsibilities and contracts

| Module | Responsibility; inputs → outputs | Invariants | Failure modes | Required tests | Status |
|---|---|---|---|---|---|
| config.py | Parse YAML; config file → immutable typed config | A runnable config has no unresolved values; values conform to protocol | Unknown keys, missing fields, invalid ranges, conflicting values | Valid parse; missing placeholders and invalid probabilities fail closed | Required |
| types.py | Shared immutable TraceRecord, Packet, Gap, Detection and result values | Stable IDs; read-only samples; recorded, arrival and emission clocks distinct | Invalid timestamps/IDs, mutable payload alias, invalid sample ranges | Timestamp relationships, immutability, serialization | Required |
| data/instance.py | Read INSTANCE v3 CSV/HDF5; map to canonical trace records | Never mix releases or counts/physical units; preserve source IDs/time/rate; no silent resampling/fill | Schema mismatch, unknown component order, missing pick, checksum/rights issue | Tiny synthetic HDF5 mapping; malformed schema fails visibly | Required |
| faults.py | Generate delivery plans for control, packet loss, outage and delay | Depends only on config, trace identity and seed; explicit dropped packets; no outcome-dependent fault | Invalid parameters, unstable seed, mask mismatch | p=0/p=1 behavior; same key same mask; order-independent seeds; F2 exact packet count | Required |
| replay.py | Packetize trace, apply delivery plan, advance virtual clock and call detector | Future samples are inaccessible; only delivered packets visible; no time rewriting; gaps explicit | Backward clock, invalid packet order, duplicate seq, hidden gap fill | Prefix causality; fixed-delay clock shift; dropped packet/gap; deterministic replay | Required |
| detectors/stalta.py | Causal STA/LTA; arrived packet/gap callbacks → trigger emissions | No full-trace handle; fixed windows/threshold; reset and rewarm after gaps; emission clock explicit | Insufficient warm-up, noncontiguous samples, invalid LTA | Hand-computed ratio; warm-up; gap reset; threshold/rearm; no future leakage | Required |
| evaluation.py | Match detections and compute metrics/uncertainty | Defined denominators; first qualifying trigger matched; event IDs are bootstrap units | Missing P, ambiguous key, zero exposure, unmatched trigger | P/P+H boundaries; miss penalty; equal-event weighting; seeded cluster bootstrap | Required |
| reporting.py | Write manifest, trace/event CSV and summary JSON | Provenance, seeds, exclusions, units and checksums retained; no waveform copying | Output failure, overwrite, nonfinite metrics | Schema/roundtrip; denominator/provenance presence; no overwrite | Required |
| cli.py | Validate/run/report command entry point | Reject unresolved config before replay; unique output directory | Bad args/config, accidental overwrite | CLI validation; small synthetic end-to-end execution | Required |
| fusion boundary | Future causal detection-only seam; no current module/dataflow | Later fusion sees detections only, bounded by current virtual time | Event association leakage/time alignment | Defer until revised protocol | Deferred; no file |
| physical sensor adapter | Translate live messages into same Packet/Gap envelope | Device sample time and receive time remain separate; detector/core unchanged | Clock drift, units/calibration, reconnect/reorder | Recorded-message/hardware-in-loop checks later | Deferred |

### Minimum public interfaces

Design contracts only; these are not implementation code. Samples should be immutable or exposed through read-only buffers.

- Data adapter: load_manifest(dataset_config) -> DatasetManifest; iter_eligible_traces(dataset_config, selection) -> iterator of TraceRecord.
- TraceRecord fields: dataset/event/station/location/channel IDs; samples; exact sample rate; recorded start UTC ns; P-pick sample index or UTC ns; representation/units; quality flags; source checksum and metadata provenance.
- Replay: run_trace(trace, detector_factory, fault_plan, replay_config) -> TraceRun.
- Packet fields: trace ID, sequence, first sample index, recorded sample-time bounds, payload, arrival simulation time, source packet ID.
- Detector callbacks: on_packet(packet, now_sim_ns) -> detections; on_gap(gap, now_sim_ns); finish(now_sim_ns) -> detections. Detector never receives TraceRecord or a future-data iterator.
- Faults: build_delivery_plan(trace_id, packet_count, scenario, replicate_key) -> DeliveryPlan; plan maps packet sequences to drop/delivery offset without reading waveform amplitudes.
- Detector factory: create_detector(detector_config, sample_rate) -> Detector. Detection includes trace ID, crossing sample index, emission simulation ns, score, detector ID and config hash.
- Fusion: no Phase 1 implementation. A later associator may consume detections and current virtual time, never source waveforms.
- Evaluation: match_trace_detections(trace_record, detections, horizon) -> TraceMetrics; aggregate_event_metrics(trace_metrics) -> SummaryMetrics; bootstrap_event_effect(control, fault, event_ids, seed, n) -> Estimate.
- Reporting: write_run(manifest, trace_metrics, event_metrics, summary, output_dir) -> output paths.

## 5. Time domains and causal guarantee

Use integer nanoseconds for UTC and simulation clock, integer sample indices, and exact rational sample rate (100/1 Hz). Avoid floating epoch timestamps.

- Recorded sample time: UTC from trace start and sample index.
- Packet-ready time: recorded time of the last sample in a packet.
- Simulated arrival time: packet-ready simulation time plus scenario delay; absent for a drop.
- Detector crossing sample: sample index where STA/LTA first crossed.
- Detection emission time: replay-clock time when the detector can emit after packet arrival.
- Event association and alert issuance/delivery: absent in this experiment.

The replay engine owns the dataset iterator. It creates a packet, applies its plan, advances virtual time, and then exposes only that delivered packet. The detector has no trace object, full-array reference, or ability to request an index. A dropped packet yields a gap callback and unavailable samples. Reject backward arrival times; reordering is not part of this protocol. A causality test compares emissions through cutoff T for a record truncated at T and the same record with future samples appended; results through T must be identical.

A detection carries both the recorded crossing sample time and the emission time. RDT uses emission time mapped to the UTC-anchored simulation clock, not crossing time. Added delay changes arrival/emission, never recorded sample time.

## 6. Faults and deterministic randomness

Packets use stable sequence numbers and exact sample ranges. Packetization is trace-start anchored; a final partial packet is explicit.

- C0: every packet arrives at packet-ready time.
- F1/F1a/F1b: independent Bernoulli packet loss; no retry/reorder.
- F2: drop exactly three consecutive packets starting at the packet boundary nearest P−1 s (ties earlier); record realized start offset from P.
- F3: add fixed 250 ms to each packet-ready time.

Generate random masks from a stable key containing master seed, dataset release, trace identity, scenario and replicate. Use NumPy PCG64 with seed derived by SHA-256; pin and record NumPy version and mask/checksum. Do not share mutable RNG state across traces or depend on execution order. Generate masks before detector execution. Faults cannot depend on sample values/results. Parameter values are exploratory and not empirically calibrated.

## 7. Detector/fusion and metric rules

Use the protocol’s fixed classic STA/LTA on HNZ vertical digital counts: sample rate 100 Hz; STA 0.5 s/50 samples; preceding non-overlapping LTA 10 s/1,000 samples; on ratio 3.5; rearm ratio 1.5; ratio is trailing mean-square STA divided by preceding mean-square LTA with a fixed numeric epsilon. Require contiguous 10 s warm-up; after every gap reset and rewarm. Do not add filtering, normalization or unit conversion. No fusion or event association is implemented.

The evaluator is a pure function of trace metadata, emissions and frozen rules. For each event trace, match the first emission in [P, P+10 s]. If found, RDT = emission minus P capped at 10 s; otherwise RDT = 10 s and miss = 1. Earlier emissions are pre-P triggers; later emissions are misses; additional in-window triggers are duplicates. Noise triggers are unmatched. Report noise exposure as valid HNZ trace-seconds/hours, not continuous monitoring time.

Primary aggregation: within trace average fault RDT over 20 masks and subtract C0; within event average trace differences; across events take equal-weight mean. Event-cluster bootstrap resamples event IDs with all their traces. Do not treat components, stations, samples or masks as independent events.

## 8. Configuration and manifest

The existing experiments/configs/phase1_protocol.yaml is a protocol description; no code consumes it. Runtime validation must reject unresolved fields such as data paths, checksums, metadata mappings, epsilon, bootstrap seed and frozen event IDs.

The run manifest records protocol ID/version, config checksum, dataset DOI/release/files/checksums/retrieval/license, schema mapping, selected trace IDs/exclusions, channel/representation/time/pick conventions, detector parameters, scenarios/seeds/mask checksums, code revision, Python/dependency versions, OS, command/run time, metric definitions/units/denominators, bootstrap method/seed, artifact checksums, warnings and deviations.

Write run_manifest.json, trace_metrics.csv, event_metrics.csv and summary.json to a new unique experiments/results run directory. Never overwrite. Keep waveforms outside Git and do not copy them into results. Commit only manifests/results if the applicable license and repository policy allow it.

## 9. Error and missing-data policy

Fail closed on unknown schema/version, checksum mismatch, unresolved config, ambiguous sample rate/time, missing P reference, inconsistent identity and illegal data handling. Individual records may be excluded only by predeclared criteria and with a reason code. Dataset-wide schema mismatch is fatal, not thousands of silent exclusions.

Missing packets are explicit Gap(start sample, end sample, cause) values; never zero-fill, interpolate or claim arrival. Source gaps are retained and flagged; per protocol, exclude traces with source gaps/quality flags before replay. Fault-injected gaps remain and cause reset plus fresh 10 s warm-up. If noise exposure is zero, false-trigger rate is null with a zero-exposure reason, not zero.

Output failure is fatal; do not leave a manifest marked complete. Write to temporary output and atomically rename to a unique final directory where supported.

## 10. Testing strategy tied to scientific invariants

Tests do not yet exist; this specifies their requirements. Use tiny hand-authored synthetic fixtures only for software behavior.

1. Causality: future samples cannot change emissions before arrival; detector has no full trace reference; no emission precedes packet arrival.
2. Clock separation: +250 ms shifts arrival/emission but leaves sample UTC/index unchanged; crossing and emission remain separate.
3. Packetization: exact 100 samples/full packet at 100 Hz, stable indices, explicit final partial packet.
4. Fault determinism: same keyed seed gives identical masks independent of trace order; p=0/p=1; F2 exactly three packets.
5. Gap handling: no fill/interpolation; detector resets and waits for warm-up.
6. Detector math: hand-computed ratios, no pre-warmup triggers, explicit threshold/rearm equality.
7. Evaluation: P/P+H boundaries, miss penalty, pre-P and duplicate triggers, zero exposure, equal event weights, event-cluster bootstrap repeatability.
8. Integration: one tiny synthetic event trace and noise trace pass through config/replay/fault/detector/evaluator/reporter with known outputs. This is not seismic detector validation.
9. Dataset adapter: validate actual INSTANCE mapping and fail on malformed/changed schema.
10. Reproducibility: same inputs/config/seed produce identical result tables and manifest content except explicitly variable run timestamp/path.

## 11. Dependencies and runtime

No runtime or dependency stack currently exists. The context recommends Python 3.11+; adopt it as a new design choice, not as existing project fact. Initially validate macOS and Linux; Windows remains unverified.

Proposed minimum dependencies: NumPy for arrays and pinned PCG64 masks; h5py for INSTANCE HDF5; PyYAML for YAML; pytest for development tests. Use the standard library for CSV/JSON, hashing, datetimes, paths and CLI. Do not add pandas, SciPy, ObsPy or SeisBench for this first path: the selected input is HDF5 plus metadata and the baseline detector is small. Add a library only if an actual data/API need appears. Lock dependencies and record runtime versions before runs. No database, cloud, broker, microservices or frontend.

## 12. Intentionally deferred

Multi-station fusion, association, alert lifecycle/delivery, target-site utility, physical sensors, MQTT/SeedLink, live ingest, clock synchronization, jitter/reordering/clock faults, ML detectors/training, continuous archive adapters, alternative datasets, dataset downloads in CI, dashboard, database, cloud deployment, distributed workers, generalized plugin registry and waveform redistribution are deferred.

## 13. Later physical sensor adapter

A future adapter translates device messages into the same Packet/Gap envelope, carrying device sample time, server receive time, sequence, station/channel IDs, units/calibration and quality flags. It must not change the detector or replay clock. Live arrival time comes from message receipt; replay arrival comes from the fault scheduler. Both call the same causal detector interface. Validate device clock drift, calibration, ordering and reconnect behavior at that adapter boundary.

## 14. Risks and tradeoffs

- The official sample may lack enough HNZ event/noise traces; stop rather than substitute another channel silently.
- One-second batching imposes latency in control; comparisons remain paired but do not estimate sample-level latency.
- Reset/re-warm is simple and explicit but differs from implementations that retain state or buffer.
- Counts avoid mixing physical representations for a dimensionless STA/LTA ratio, but instrument gain/response variation still affects threshold behavior.
- Ten-second horizon and 0.5 s practical margin are preregistered engineering choices, not empirically optimized.
- HNZ schema/coverage is unknown until metadata inspection; dataset access and h5py compatibility are not tested.
- This narrow result does not establish operational performance or the broad QuakeNode platform contribution.
