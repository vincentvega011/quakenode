# QuakeNode — Project Context for Contributors

> **Purpose of this file:** Give contributors a durable, technically grounded understanding of QuakeNode so they can implement it consistently without repeatedly rediscovering the project’s goals, architecture, research constraints, and definition of done.
>
> **Project status:** Research prototype / open-source engineering project. This is not a validated public earthquake-warning service and must never be presented as one.

---

## 1. Project in one paragraph

**QuakeNode is an open-source, software-first research testbed for evaluating earthquake early-warning (EEW) pipelines under realistic streaming and system-failure conditions.** It lets researchers replay seismic waveforms as if they were arriving live from a network of stations, run one or more detection pipelines without access to future samples, simulate communications and sensor failures, and compare results with reproducible experiments. The central deliverable is not a sensor board or a flashy dashboard: it is a trustworthy experimental system that makes the assumptions, timing, failures, and evaluation metrics of an EEW pipeline explicit and testable. Physical sensor nodes may be added later through a transport adapter, but the first milestone is software-only and must work with recorded waveforms and/or clearly labeled synthetic data.

## 2. The problem QuakeNode addresses

Earthquake early warning is not earthquake prediction. An EEW system detects an earthquake after rupture begins, estimates its likely effects, and attempts to alert locations before damaging shaking arrives. The available lead time depends on event geometry, distance, signal quality, communication delays, processing time, and the warning threshold. Some locations may receive only a few seconds of warning or none at all.

EEW systems are end-to-end systems, not merely classifiers. Their practical performance can depend on:
- when a station samples and timestamps a waveform;
- how data are buffered, packetized, transmitted, delayed, dropped, or reordered;
- whether station clocks are synchronized;
- how a detector behaves as samples arrive over time;
- how detections from multiple stations are associated into an event;
- how an event estimate changes as new information arrives;
- how and when an alert is issued, updated, or cancelled;
- whether the alert arrives before a defined level of shaking at a target location;
- how false alerts, missed alerts, latency, and uncertainty are counted.

A model that looks strong when given a complete waveform offline may behave differently in a causal live stream. QuakeNode should make those differences measurable, reproducible, and easy for others to investigate.

## 3. Research framing and novelty discipline

### Primary research question

**Do earthquake early-warning pipelines that perform well on offline test data remain reliable when evaluated as causal real-time systems under realistic sensor and network failures?**

A possible hypothesis to test—not an assumed result—is:

> Introducing causal streaming constraints and controlled sensor/network failures changes measured warning utility, latency, or the relative ranking of at least some EEW pipelines compared with idealized offline evaluation.

### Candidate research contribution

The project should aim to provide a coherent, open, reproducible benchmark that combines:

1. **Causal waveform replay:** data become available only at their simulated arrival time; future samples are inaccessible to the detector.
2. **Scenario-driven fault injection:** controlled loss, delay, jitter, reordering, station outages, missing samples, clock errors, and recovery.
3. **Multi-station event processing:** a transparent baseline for combining detections across stations, with assumptions documented.
4. **Warning-utility evaluation:** where the required data exist, measure alert timing relative to a defined ground-motion threshold at target sites.
5. **Reproducible experiment artifacts:** dataset identifiers, event/station selection, configuration, seeds, software versions, outputs, and plots are saved together.

This is a candidate contribution, not a novelty claim. Existing literature and tools already address real-time EEW evaluation, latency, seismic detection, and benchmarking in various forms. Do **not** claim that “no one has evaluated EEW in real time.” Before asserting novelty, compare QuakeNode against relevant papers, repositories, supplementary materials, and existing evaluation systems. The defensible angle may be the integration of causal replay, configurable fault scenarios, event fusion, and reproducible warning-utility evaluation in one accessible testbed—but this must be demonstrated, not assumed.

### What would make the work scientifically meaningful?

A paper should answer a narrow empirical question using a defined dataset and a fair protocol. It should report results even if the hypothesis is not supported. Useful outcomes include:
- which faults affect which metrics;
- whether a detector’s latency or false-alarm behavior changes under streaming;
- whether a fusion method is more robust than a single-station baseline;
- whether rankings of methods change between ideal and degraded conditions;
- which assumptions dominate the measured result;
- what cannot be concluded because of dataset or metadata limitations.

A dashboard, a repository, or a list of features is not by itself a research contribution.

---

## 4. Explicit non-goals

Unless the project scope is deliberately revised, do **not** spend the first phase on these:

- Building a custom PCB or physical seismic sensor.
- Claiming that QuakeNode predicts earthquakes.
- Issuing real public safety alerts.
- Claiming field readiness, certification, or life-safety reliability.
- Training a new deep-learning model before establishing a trustworthy baseline and evaluation protocol.
- Building a large, polished dashboard before the replay engine and tests work.
- Creating a generic IoT platform unrelated to EEW research.
- Claiming superiority over ShakeAlert, OpenEEW, or deployed systems without a rigorous, comparable evaluation.
- Using synthetic waveforms as if they were real earthquake recordings.
- Publishing unverified numerical claims, fabricated benchmarks, or results that cannot be reproduced.
- Redistributing waveform data, model weights, or station metadata without checking their licenses and terms.

---

## 5. Target users and intended use

Initial users:
- EECS students and researchers investigating real-time systems, signal processing, distributed sensing, or ML robustness;
- seismology researchers who need a repeatable way to test pipeline assumptions;
- open-source contributors who want a clean baseline for EEW experiments;
- educators demonstrating why real-time performance differs from offline classification.

Intended use:
- offline research and simulation;
- reproducible experiments on recorded or explicitly synthetic waveform streams;
- comparisons among baseline detectors, fusion rules, and failure scenarios;
- educational demonstrations of latency and warning-time tradeoffs.

Not intended for:
- operational emergency management;
- direct public warning;
- replacing official seismic monitoring;
- safety-critical decisions.

Every README, demo, and dashboard should state that QuakeNode is a research testbed, not an operational warning system.

---

## 6. Product principles

1. **Correctness before spectacle.** A small, tested replay engine beats a beautiful dashboard with invalid timing.
2. **Causal by construction.** No detector or fusion component may access samples that have not arrived yet.
3. **Reproducibility by default.** Every experiment should be rerunnable from a versioned configuration and recorded data references.
4. **Explicit assumptions.** Sampling rates, clocks, units, thresholds, station geometry, latency, and missing-data behavior must be documented.
5. **Baseline before complexity.** Begin with a simple, interpretable detector and fusion rule. Add ML only when the evaluation is trustworthy.
6. **Faults are first-class scenarios.** Failure injection must be deterministic and configurable, not ad hoc sleeps or random bugs.
7. **Metrics must have precise definitions.** “Accuracy” alone is not sufficient for an end-to-end EEW system.
8. **Scientific humility.** Negative results and limitations are valuable. Never imply a benchmark is representative of all earthquakes unless the data support that claim.
9. **Modular interfaces.** Detectors, transports, fusion methods, and metrics should be replaceable without rewriting the replay engine.
10. **Small vertical slices.** Each implementation phase should result in a runnable example and automated tests.

---

## 7. Recommended initial technical scope

### Minimum viable research prototype (MVRP)

The first usable version should support:

- reading a documented waveform dataset or a small locally available sample;
- replaying station traces in causal time;
- a simple baseline detector, such as STA/LTA, with clear threshold and trigger semantics;
- simulated station streams and station metadata;
- configurable communication delay and packet loss;
- event/detection records with timestamps and station identifiers;
- an evaluator that computes at least detection latency, missed detections, false triggers under a documented definition, and performance under fault scenarios;
- an experiment configuration file and a one-command run;
- tests that prove future samples are not leaked;
- a machine-readable result file and at least one useful plot/report.

Do not make every feature below a prerequisite for the first demo. Deliver the causal replay plus baseline plus one fault plus tests before expanding.

### Recommended first experiment

Use one documented dataset split, one simple baseline detector, and a small set of controlled scenarios:

- **Scenario A — idealized delivery:** recorded samples arrive at their nominal time with no injected communication faults.
- **Scenario B — fixed delivery delay:** all packets incur a configured delay.
- **Scenario C — random packet loss:** packets are dropped using a seeded, documented process.
- **Scenario D — station outage:** one or more stations go offline for a specified interval.
- **Scenario E — combined degradation:** a predeclared combination of delay, loss, and outage.

Compare results across scenarios using the same event set, detector parameters, and evaluation definitions. Report uncertainty and event-level variation where practical. The purpose is not to choose a dramatic result; it is to learn which effects are measurable and whether the experiment is fair.

---

## 8. Architecture

Keep the first implementation as a Python package with narrow module boundaries. Avoid premature microservices.

### Data flow

```text
Waveform files + station metadata + event metadata
                    |
                    v
            Dataset adapter
                    |
                    v
         Causal streaming replay
                    |
                    v
         Virtual station / transport
                    |
           +--------+--------+
           |                 |
           v                 v
      Fault injector     Stream monitor
           |                 |
           +--------+--------+
                    |
                    v
             Detector plugin(s)
                    |
                    v
           Detection/event fusion
                    |
                    v
            Alert state machine
                    |
                    v
              Evaluator
                    |
                    v
       Results + metadata + plots/report
```

The diagram describes logical responsibilities, not necessarily separate processes. The first version can run all of these in one process.

### Module responsibilities

#### `data/`
- Load waveform traces, station metadata, and event metadata through adapters.
- Preserve units, sample rate, start time, station/channel identifiers, and source/license information.
- Validate missing or inconsistent metadata.
- Never silently treat unknown units or timestamps as valid.
- Keep downloaded datasets out of version control unless their license explicitly allows redistribution.

#### `replay/`
- Turn traces into sample or packet events in simulation time.
- Expose only samples that have arrived.
- Support deterministic time progression.
- Make replay speed explicit: real-time simulation, accelerated simulation, or step-by-step mode.
- Separate **recorded sample time** from **simulated arrival time**.
- Ensure accelerated replay changes wall-clock runtime, not the logical event timing or causal ordering.

#### `stations/`
- Represent virtual stations and their identity, coordinates, channels, sample rates, and availability.
- Track station status, gaps, and last received sample time.
- Avoid assuming all stations have identical rates or perfectly synchronized clocks.

#### `transport/`
- Define a transport-neutral message interface for station data and detections.
- Start with an in-process transport or async queue.
- Add MQTT only if it supports a concrete experiment or integration goal.
- Keep transport delay and queueing observable.

#### `faults/`
- Apply configurable delay, jitter, packet loss, reordering, station outage, clock offset/drift, and missing-sample scenarios.
- Use deterministic seeds for random faults.
- Record every injected fault in experiment metadata and, where useful, in an event log.
- Make the no-fault case an explicit baseline.

#### `detectors/`
- Define a common detector interface.
- Include a simple, interpretable baseline first (e.g. STA/LTA).
- Later, integrate documented existing detectors or SeisBench models through adapters where appropriate.
- Do not force all algorithms into a single interface if their inputs/outputs genuinely differ; define a minimal common contract and preserve model-specific metadata.
- Every detector output must include a timestamp and enough metadata to interpret it.

#### `fusion/`
- Combine station detections into candidate events using explicit rules.
- Start with a transparent rule such as a minimum number of distinct stations triggering within a time window.
- Make thresholds, windows, and station eligibility configurable.
- Do not imply that simple fusion is equivalent to a validated earthquake location/magnitude estimator.
- Track how each event decision was produced.

#### `alerts/`
- Represent alert lifecycle and state transitions, such as candidate, issued, updated, and cancelled, only if these states are implemented and documented.
- Keep detection, event association, alert issuance, and alert delivery as separate timestamps.
- Avoid sending real alerts or connecting to public alert infrastructure in the prototype.

#### `evaluation/`
- Implement clearly defined metrics and event matching.
- Compute event-level and aggregate outcomes.
- Keep the evaluation protocol separate from detector implementation.
- Record exclusions, unmatched events, missing data, and evaluation windows.
- Avoid tuning detector parameters on the test set.

#### `experiments/`
- Store versioned experiment configs and scripts.
- Record dataset IDs, station/event selections, seed, code version, dependency versions, parameters, and output location.
- Support rerunning a configuration without manually editing source code.

#### `reporting/`
- Produce CSV/JSON results and simple plots.
- Plot clarity and correct units matter more than visual polish.
- Generate a concise experiment summary that links every reported number to its config and input data.

#### `dashboard/` (later)
- Visualize station status, waveform arrival, detections, injected faults, event fusion, alert timeline, and experiment comparisons.
- The dashboard must consume the same results/events as the evaluator; it must not maintain a separate source of scientific truth.
- Build it only after the command-line workflow works.

---

## 9. Proposed repository layout

This is a starting proposal. Adapt to the actual codebase rather than blindly recreating directories.

```text
quakenode/
├── README.md
├── CONTEXT.md                 # Optional copy/link of this context
├── LICENSE
├── pyproject.toml
├── .gitignore
├── .pre-commit-config.yaml    # Optional
├── docs/
│   ├── architecture.md
│   ├── scientific-assumptions.md
│   ├── evaluation-protocol.md
│   ├── datasets-and-licenses.md
│   ├── reproducibility.md
│   └── limitations.md
├── src/
│   └── quakenode/
│       ├── __init__.py
│       ├── config.py
│       ├── schemas.py
│       ├── data/
│       ├── replay/
│       ├── stations/
│       ├── transport/
│       ├── faults/
│       ├── detectors/
│       ├── fusion/
│       ├── alerts/
│       ├── evaluation/
│       ├── experiments/
│       └── reporting/
├── experiments/
│   ├── configs/
│   ├── baselines/
│   └── README.md
├── examples/
│   ├── synthetic_stream/
│   └── recorded_waveform/
├── tests/
│   ├── test_config.py
│   ├── test_causal_replay.py
│   ├── test_no_future_leakage.py
│   ├── test_fault_injection.py
│   ├── test_station_outage.py
│   ├── test_detector_contract.py
│   ├── test_fusion.py
│   └── test_metrics.py
├── scripts/
└── papers/
    └── first_study/
        ├── outline.md
        ├── protocol.md
        └── figures/
```

Prefer `src/` package layout and explicit public APIs. Do not add empty modules simply to match this tree. Each directory should exist when there is a real responsibility for it.

---

## 10. Core data contracts

Use typed, documented schemas. Dataclasses or Pydantic are both reasonable; choose one approach and avoid mixing styles unnecessarily. Keep schemas stable and version them if stored experiment outputs will be consumed by external tools.

### Waveform sample / chunk

A stream item should carry enough information to distinguish data time from arrival time. Conceptually:

```python
WaveformChunk(
    station_id: str,
    channel_id: str,
    sample_rate_hz: float,
    sample_start_time_utc: datetime,
    samples: array,
    sequence_number: int,
    simulated_arrival_time_s: float,
    units: str,
    metadata: dict,
)
```

This is illustrative, not a requirement to use these exact names. For a chunk, `sample_start_time_utc` refers to the time of its first recorded sample; `simulated_arrival_time_s` is the simulator's logical time when that chunk becomes available to downstream components. If chunks contain multiple samples, define the delivery semantics: do all samples become available together when the packet arrives, or are samples exposed one by one? Document the chosen behavior.

### Detection

A detection record should include:
- unique detection ID;
- detector name/version;
- station and channel IDs;
- detection/trigger timestamp in the waveform time domain;
- simulator time at which the detection was emitted;
- score or trigger statistic, if applicable;
- threshold/parameters used;
- relevant quality flags and metadata.

Do not conflate the estimated onset time with the time the detector actually emitted its result.

### Event candidate / alert

An event candidate should reference the detections that contributed to it, plus:
- creation time;
- update time(s), if supported;
- station count and station IDs;
- current status;
- confidence/score only if it has a defined meaning;
- event estimate fields only when an actual method computes them.

An alert should have separate times for:
- first supporting waveform sample;
- first station detection;
- event association;
- alert decision;
- alert delivery to a simulated recipient.

Do not populate unavailable values with invented estimates. Use explicit `null`/missing values and explain why.

### Experiment manifest

Every run should persist:
- schema version;
- experiment ID;
- UTC creation time;
- QuakeNode version or git commit;
- Python and dependency versions;
- dataset identifiers and licenses/source URLs;
- event and station selection;
- configuration snapshot;
- random seed(s);
- detector and fusion parameters;
- fault scenario and parameters;
- metric definitions/version;
- output paths;
- warnings, exclusions, and failures.

A run without sufficient metadata to reproduce its settings is not a fully reproducible experiment.

---

## 11. Causal replay: the most important correctness requirement

**Future-sample leakage is a critical failure.** The replay engine must not load a full trace into a detector in a way that allows the detector to inspect samples that would not yet have arrived in a live system.

Requirements:
- Replay advances a logical simulation clock.
- A component can read only data delivered by that clock.
- Arrival delays and gaps affect when data become available.
- Detector code should receive incremental chunks or a stream abstraction, not an unrestricted future trace.
- Each emitted result records both waveform/event time and simulator emission time.
- Tests must deliberately construct a waveform where future samples would make detection trivial and verify that the detector cannot see them early.
- Accelerated replay may process many simulated seconds per wall-clock second, but logical arrival ordering and event times must remain correct.
- A deterministic replay of the same configuration and seed should produce the same output, subject to documented nondeterminism.

Avoid relying on wall-clock `sleep()` for simulation correctness. Prefer a deterministic event queue or logical scheduler. Wall-clock sleeps can be used only for an optional live-speed demo mode.

### Suggested causal replay tests

1. **No future samples:** at simulation time `t`, the detector's visible buffer contains no samples whose delivery time exceeds `t`.
2. **Arrival delay:** adding a known transport delay shifts availability/emission timing by the expected amount.
3. **Chunk boundaries:** changing chunk size does not silently change sample timestamps; any real algorithmic dependence on chunking is measured and documented.
4. **Gaps:** missing chunks are represented as gaps, not silently interpolated.
5. **Repeatability:** same seed and configuration yield equivalent output.
6. **Ordering:** packet reordering is either preserved as an explicit fault or resolved by a documented buffering policy; it is never silently hidden.
7. **Clock domains:** waveform time and simulation arrival time are not accidentally compared as if they were identical.

---

## 12. Fault-injection design

Faults should be independent, configurable components that transform the delivery of data or the availability of stations. Keep their behavior measurable.

### Initial fault types

- **Fixed delay:** add a constant delivery delay.
- **Jitter:** add a random delay drawn from a configured distribution; record the seed and distribution.
- **Packet loss:** drop a specified fraction or use a defined burst-loss process.
- **Reordering:** deliver packets out of sequence according to a documented rule.
- **Station outage:** stop data from one station over a specified logical interval, then recover it.
- **Missing samples:** remove a range or chunks from a waveform stream.
- **Clock offset:** shift a station's reported timestamps by a known amount.
- **Clock drift:** make reported timestamp error evolve over time.
- **Noise perturbation:** only add noise when the signal-processing meaning and units are clear; distinguish signal noise from network faults.
- **Queue/backpressure:** simulate queue limits or overload only when behavior is specified and tested.

For each fault, record:
- fault type and parameters;
- target station(s), channel(s), or stream(s);
- start/end simulation time;
- seed and random process;
- packets/samples affected;
- whether the fault was applied, skipped, or impossible due to missing data.

Avoid a vague “chaos mode” that changes many things unpredictably. Every experiment should say exactly which faults were applied.

### Fair comparisons

When comparing baseline and degraded runs:
- keep the underlying event set fixed;
- keep detector parameters fixed unless tuning is itself the subject;
- use paired random seeds where appropriate;
- clearly distinguish fault-free control runs from degraded runs;
- repeat stochastic scenarios enough times to estimate variability;
- report the number of events/stations/runs;
- do not cherry-pick only the most dramatic event.

---

## 13. Detection and fusion strategy

### Baseline detector

Begin with an interpretable short-term average / long-term average (STA/LTA) trigger or another simple, documented detector. Define:
- signal component/channel used;
- preprocessing/filtering;
- sample rate assumptions;
- STA and LTA window lengths;
- trigger and detrigger thresholds;
- minimum trigger duration;
- re-arming / dead-time behavior;
- gap and clipping behavior;
- detector output timestamp semantics.

Do not assume the baseline is a state-of-the-art detector. Its role is to verify the pipeline and establish a transparent reference.

### Later detector integrations

After the baseline is correct, consider adapters for established seismic ML tools such as SeisBench, subject to model/dataset compatibility, computational cost, licensing, and input conventions. Compare methods only under a fair protocol and avoid training on test events.

### Initial fusion baseline

A simple fusion rule can require detections from at least `k` distinct stations within a configurable time window. This is a systems baseline, not a scientifically complete location or magnitude estimator.

Define:
- how station clocks and detection times are handled;
- whether late-arriving detections can update an existing event;
- how duplicate detections are deduplicated;
- how stations are weighted, if at all;
- how the fusion window is selected;
- what causes a candidate to be issued, updated, or cancelled.

Use event identifiers and state transitions that can be inspected in a trace log. Never hide a fusion decision behind an undocumented score.

---

## 14. Evaluation protocol and metrics

The project must not reduce system performance to one accuracy number. Different metrics answer different questions.

### Minimum metrics

1. **Detection latency:** elapsed simulated time between a precisely defined input reference and detector output. State the reference definition.
2. **Event detection rate / recall:** fraction of eligible reference events matched by the system under a declared matching rule.
3. **Missed-event count:** number of eligible reference events not matched.
4. **False-trigger rate:** false detections per unit time or another explicitly defined denominator. Do not call every unmatched station trigger a false earthquake without event association.
5. **Event association latency:** time from a declared reference point to event-candidate creation.
6. **Alert issuance latency:** time from a declared reference point to simulated alert decision.
7. **Station availability / data completeness:** received samples or packets relative to expected values, with the denominator defined.
8. **Fault sensitivity:** change in each metric relative to a matched fault-free control.
9. **Warning time:** only when target-site shaking information is available and a defensible method is implemented.

### Warning-time definition

A useful conceptual definition is:

`warning_time(target) = target_shaking_threshold_time - alert_delivery_time_to_target`

Positive means the alert arrived before the threshold crossing; negative means it arrived too late. This formula is only valid if both times are defined on a consistent timeline and the target shaking threshold is derived from suitable data or a documented ground-motion model. Report negative values; do not discard them because they look bad. State whether the reference is observed ground motion or a modeled estimate.

If data do not support a defensible target-site threshold calculation, do not claim to measure real warning time. Report detection/event/alert latency instead and mark target warning utility as future work.

### Event matching

Document how detections or event candidates match reference events:
- time window;
- geographic distance window, if location estimates exist;
- one-to-one matching or multi-match rules;
- treatment of multiple triggers for one event;
- treatment of events outside the station network or evaluation window;
- exclusions and missing reference metadata.

Do not tune matching rules after inspecting the result without documenting the change and rerunning the full experiment.

### Statistics and reporting

- Report counts and distributions, not only means.
- Include median and relevant quantiles for latency.
- Include confidence intervals or uncertainty estimates when sample sizes and experimental design justify them.
- For stochastic faults, report repeat count and variability.
- Separate event-level results from station-level results.
- Report all tested scenarios, including neutral or negative outcomes.
- Clearly label simulated outcomes versus measured field data.
- Include data limitations and avoid broad claims from a small dataset.

---

## 15. Dataset and scientific integrity rules

Candidate sources and tools to investigate include:
- **ObsPy** for waveform and seismology data handling;
- **SeisBench** for established seismic ML models and datasets;
- **OpenEEW** as an open-source EEW hardware/software ecosystem to study;
- public waveform archives and event catalogs appropriate to the chosen region and research question;
- synthetic waveforms for software tests and controlled edge cases.

These are starting points for research, not automatic endorsements or permission to redistribute data.

For every dataset/model:
- read the license and terms;
- record source, version, citation, and retrieval date;
- document whether redistribution is allowed;
- document station coverage, sample rate, channels, units, and known quality issues;
- keep train/validation/test splits separate where model training is involved;
- avoid data leakage between event windows or stations when it would invalidate evaluation;
- distinguish actual earthquake records, noise-only records, and synthetic examples;
- document preprocessing and any resampling/filtering;
- never fabricate station coordinates, event magnitudes, ground-motion labels, or event times.

For the first prototype, use the smallest real dataset that supports a valid end-to-end demonstration. If access to a suitable dataset is delayed, build against synthetic fixtures while clearly marking all results as software-validation tests, not seismological performance results.

---

## 16. Recommended technology choices

Use a boring, testable stack.

### Core
- **Python 3.11+** (choose a supported version and pin it in project metadata).
- **NumPy / SciPy** for numerical work and signal processing.
- **ObsPy** for waveform/seismology formats and utilities when needed.
- **pytest** for automated tests.
- **Pydantic or dataclasses** for configuration and data contracts.
- **Typer** or `argparse` for the command-line interface.
- **Pandas** only where tabular aggregation materially helps.
- **Matplotlib** for initial reproducible plots.

### Optional later
- **SeisBench** for model integration after baseline validation.
- **asyncio** for stream processing when asynchronous behavior is necessary; do not use async merely for fashion.
- **MQTT** for a physical-node or network integration milestone.
- **FastAPI** only if a real API boundary is needed.
- **React/TypeScript** for a dashboard after the CLI pipeline is stable.
- **Docker** for reproducible setup if it reduces contributor friction; do not make it a requirement if a clean Python environment is sufficient.

### Engineering standards
- Use `pyproject.toml` for package metadata and dependencies.
- Add type hints to public interfaces.
- Keep functions small and testable.
- Prefer structured logging over print statements in library code.
- Validate configuration at startup and fail loudly on invalid settings.
- Use stable random seeds in experiment configs.
- Avoid hidden global mutable state.
- Do not catch exceptions and silently continue.
- Use clear error messages that identify the station, trace, or config key involved.
- Keep scientific logic out of UI components.
- Add dependency versions and platform notes to experiment manifests.

Do not introduce a database, distributed queue, cloud service, or complex orchestration framework until a concrete experiment requires it.

---

## 17. Command-line experience

The first interface should be usable without a dashboard. Exact command names may change, but the workflow should be similarly simple:

```bash
# Install in development mode
python -m pip install -e ".[dev]"

# Run tests
pytest

# Run a synthetic pipeline fixture
quakenode run examples/synthetic_stream/config.yaml

# Run a recorded-waveform experiment
quakenode run experiments/configs/baseline.yaml

# Compare baseline and fault scenarios
quakenode compare experiments/configs/fault_sweep.yaml

# Inspect a saved run
quakenode report outputs/<run-id>/
```

Do not claim these commands work until implemented. If the CLI has not been built yet, treat this block as a target interface rather than existing functionality.

Every run should create a unique output directory with a manifest, logs, raw metrics, and generated plots. Avoid overwriting a previous run by default.

---

## 18. Configuration design

Use human-readable YAML or TOML. Validate values and document defaults. Example shape:

```yaml
schema_version: 1
experiment:
  name: "sta_lta_packet_loss_sweep"
  seed: 20261026

data:
  source: "local"
  dataset_id: "REPLACE_WITH_DOCUMENTED_DATASET_ID"
  waveform_path: "data/example_waveforms/"
  event_catalog_path: "data/example_events.csv"
  station_metadata_path: "data/stations.csv"

replay:
  mode: "accelerated"
  chunk_size_samples: 100
  preserve_recorded_timestamps: true

detector:
  type: "sta_lta"
  parameters:
    sta_seconds: 1.0
    lta_seconds: 10.0
    trigger_threshold: 3.5
    detrigger_threshold: 1.5

fusion:
  type: "k_of_n"
  minimum_stations: 2
  time_window_seconds: 5.0

faults:
  - type: "packet_loss"
    probability: 0.05
    seed: 20261026

evaluation:
  event_match_window_seconds: 30.0
  compute_warning_time: false

output:
  directory: "outputs/"
  save_event_log: true
  save_metrics_csv: true
  save_plots: true
```

The values above are illustrative starter values, not validated seismological parameters. Do not present them as scientifically optimized. The schema should reject unknown fault types, invalid probabilities, negative delays, impossible sampling rates, and missing required fields. Make all defaults explicit in generated manifests.

---

## 19. Testing strategy

Tests are part of the scientific instrument, not just software hygiene.

### Unit tests
- configuration validation;
- waveform/chunk timestamp arithmetic;
- fault transformations;
- detector state transitions;
- fusion rules;
- event matching;
- metric calculations;
- manifest serialization.

### Integration tests
- synthetic waveform → causal replay → detector → fusion → evaluator;
- packet loss and station outage change data availability as configured;
- saved experiment output can be loaded by the report command;
- a full example runs from a clean environment.

### Scientific invariants
- no future samples are visible;
- a no-fault scenario does not unexpectedly lose data;
- adding a configured fixed delay does not alter the original waveform timestamps;
- simulation arrival time and recorded sample time remain distinguishable;
- deterministic seeds reproduce stochastic fault patterns;
- station outage begins and ends at the specified logical times;
- metrics match hand-calculated toy examples;
- a detector cannot emit a result before it has received enough input to calculate it;
- changing a plotting option does not change scientific outputs;
- result files contain the exact configuration and dataset identity used.

### Continuous integration
At minimum, run formatting/linting and tests on supported Python versions. Keep CI small enough that contributors can run the same checks locally. Use a tiny synthetic fixture for fast CI; do not download large datasets in every test run.

---

## 20. Security, safety, and reliability

Although the initial system is a research simulator, its subject is public safety. Avoid language that could make a prototype appear operational.

- Display a clear “research prototype—not for public warning” notice in demos.
- Never connect the prototype to public alert channels by default.
- Do not use real people's location data or collect user location unnecessarily.
- Keep downloaded data paths configurable and do not execute untrusted dataset content.
- Validate input file sizes and configuration values.
- Avoid network services bound to public interfaces unless intentionally configured.
- Do not log secrets, tokens, or private connection strings.
- If hardware is eventually attached, document electrical, power, enclosure, mounting, and sensor-calibration limits.
- Do not state that a low-cost accelerometer node provides reliable earthquake warnings without calibration, testing, and comparison with appropriate reference instruments.
- Separate a sensor's ability to detect vibration from the ability to identify an earthquake and from the ability to deliver a useful warning.

---

## 21. First implementation plan

Prioritize a narrow, end-to-end vertical slice. The following plan is deliberately staged; if the schedule is only about nine days, aim for a credible prototype and preliminary experiment, not a finished publication.

### Phase 0 — Prior-art and feasibility audit
Deliverables:
- a comparison table of relevant papers, repositories, and tools;
- a clear statement of what they already provide;
- a narrowed gap that QuakeNode can actually test;
- a feasible dataset and licensing plan;
- a written evaluation protocol before running experiments.

Questions to answer:
- Which tools already support causal/streaming replay?
- Which support network delay/loss or station outages?
- Which evaluate warning time at target locations versus detector accuracy?
- Which preserve run configs, seeds, versions, and event-level results?
- Can QuakeNode add value through integration, a new benchmark protocol, a new failure model, or a rigorous empirical result?

### Phase 1 — Data and deterministic synthetic fixture
Deliverables:
- a minimal data schema;
- one small documented waveform input, if available;
- a synthetic fixture for tests;
- validation for units, timestamps, sample rate, and station IDs.

### Phase 2 — Causal replay and baseline detector
Deliverables:
- logical event scheduler;
- incremental sample/chunk delivery;
- baseline detector;
- detection records with event time and emission time;
- future-leakage tests;
- one command that runs end-to-end on a toy example.

### Phase 3 — One fault, then a fault matrix
Deliverables:
- packet delay and packet loss first;
- station outage next;
- deterministic fault logs;
- paired no-fault/fault runs;
- metric table and plot.

### Phase 4 — Fusion and evaluation
Deliverables:
- transparent multi-station fusion baseline;
- documented event matching;
- latency and false-trigger/miss metrics;
- warning-time calculation only if the reference data support it.

### Phase 5 — Reproducibility and paper artifacts
Deliverables:
- saved experiment manifests;
- fixed configuration files;
- one-command reproduction;
- figures generated from saved outputs;
- limitations and assumptions document;
- a preliminary results report that includes failures and negative results.

### Phase 6 — Dashboard and physical-node adapter
Only start after the core workflow is correct. A dashboard can visualize the pipeline; it must not substitute for a working, tested experiment runner. Hardware is a future integration path, not a prerequisite for the software research contribution.

---

## 22. Nine-day focused sprint (if that deadline still applies)

This is an aggressive prototype schedule, not a promise of publication readiness.

| Day | Focus | End-of-day artifact |
|---|---|---|
| 1 | Prior-art audit and narrow question | Comparison matrix, research question, initial protocol |
| 2 | Dataset/license check; schemas and toy fixture | Data adapter plan, reproducible synthetic fixture |
| 3 | Causal replay | Replay tests, event-time/arrival-time distinction |
| 4 | Baseline detector | End-to-end run, no-future-leakage tests |
| 5 | Delay and loss injection | Deterministic fault scenarios and event log |
| 6 | Station outage and basic fusion | Multi-station toy experiment |
| 7 | Metrics and paired experiments | CSV/JSON metrics and first plots |
| 8 | Reproduction, edge cases, documentation | Clean-run instructions, known limitations |
| 9 | Results and demo | Reproducible demo, short report, next-step decision |

If the data or prior-art audit exposes a flaw in the premise, change the research question early. Do not build a large dashboard just to preserve the original plan.

---

## 23. Paper strategy

Possible working title:

**Beyond Offline Accuracy: A Reproducible Robustness Benchmark for Real-Time Earthquake Early Warning**

The title should be changed if the actual contribution is narrower or the results do not support it.

### Paper structure
1. **Abstract:** problem, gap relative to existing work, method, dataset/scenarios, primary findings, limitations.
2. **Introduction:** why offline metrics do not fully characterize end-to-end EEW behavior; what is already known; exact contribution.
3. **Related work:** EEW systems, real-time evaluation, seismic detectors, event fusion, networked sensing, robustness/fault testing.
4. **System and threat/assumption model:** timing model, data path, fault types, what is and is not simulated.
5. **Evaluation protocol:** data, station/event selection, baselines, metrics, matching rules, seeds, exclusions.
6. **Experiments:** predeclared scenarios and controlled comparisons.
7. **Results:** event-level outcomes, aggregate distributions, variability, failure cases.
8. **Discussion:** interpretation, applicability, what cannot be concluded.
9. **Limitations:** dataset coverage, simulated network assumptions, baseline simplicity, lack of field validation.
10. **Reproducibility:** repository commit, configs, environment, data access, command to rerun.
11. **Conclusion:** evidence-based claims only.

### Contribution statement template

Use only after results support it:

> “We present QuakeNode, an open-source testbed for [precisely supported capabilities]. Using [dataset and number of events/stations], we evaluate [baseline pipelines] under [predefined scenarios]. We find [measured result with uncertainty]. We release [code/configs/results] to support reproduction.”

Do not fill the brackets with invented results. If results are preliminary, label the manuscript as a preprint or technical report and be transparent about scope. Do not imply peer review or conference acceptance before it happens.

### Conference strategy
A credible submission needs a contribution aligned with the venue. A software demo, student research track, seismology meeting, systems workshop, or ML robustness workshop may have different requirements. Choose the venue after the contribution and evidence are clearer, not before. Check current calls for papers, deadlines, format, and artifact policies directly from the venue.

---

## 24. Prior-art starting list

Use these as starting points for a structured review. Verify the latest versions, publication details, licenses, and scope before citing them.

- **OpenEEW:** https://github.com/openeew/openeew
- **OpenEEW sensor repository:** https://github.com/openeew/openeew-sensor
- **OpenEEW firmware repository:** https://github.com/openeew/openeew-firmware
- **SeisBench:** https://github.com/seisbench/seisbench
- **USGS — Limits of earthquake early warning timeliness and ground-motion estimates:** https://www.usgs.gov/publications/limits-earthquake-early-warning-timeliness-ground-motion-estimates
- **Real-time warning utility / timeliness and correctness evaluation (2017):** https://agupubs.onlinelibrary.wiley.com/doi/full/10.1002/2017jb014025
- **E3WS single-station ML EEW study:** https://doi.org/10.1029/2023JB026575
- **2026 paper on real-time classification and end-to-end latency:** https://link.springer.com/article/10.1007/s12145-026-02099-6
- **ShakeAlert testing with synthesized earthquake sequences:** https://www.usgs.gov/publications/testing-shakealert-earthquake-early-warning-system-using-synthesized-earthquake
- **Nepal EEW feasibility/program context (NSET):** https://nset.org.np/program/nepal-eew-earthquake-early-warning/
- **Nepal project context (SEG):** https://seg.org/gwb_projects/nepal-3/
- **Duke/Tribhuvan Kathmandu EEW project context:** https://bassconnections.duke.edu/project/earthquake-early-warning-kathmandu-2025-2026/

This list is not a completed literature review. Search for newer work and inspect references/citations of relevant papers. Compare the actual methods and capabilities rather than judging from abstracts alone. The Nepal-specific context is important for motivation, but do not claim a system is suitable for Nepal without considering local seismicity, station coverage, telemetry, governance, and validation.

---

## 25. Open-source and contribution policy

- Choose a recognized license compatible with the intended project and dependencies. MIT or Apache-2.0 may fit code, but decide deliberately and include third-party notices where required.
- A permissive code license does not automatically grant rights to datasets, trained weights, logos, or third-party documentation.
- Include a `CITATION.cff` when a citable research release is ready.
- Use issues to track reproducible bugs and research questions separately where practical.
- Require tests for changes to timing, fault injection, event matching, or metrics.
- Keep configuration changes and metric-definition changes visible in version control.
- For research results, tag the code version and archive the exact configs.
- Do not report a benchmark number without recording the code version, data selection, parameters, and metric definition.
- Make contribution instructions short and include a minimal “run tests / run example” path.

---

## 26. Guidance for contributors

When an agent is asked to work on QuakeNode, it should follow these rules:

1. **Inspect before editing.** Read the existing repository, tests, README, and dependency metadata first. Do not assume the repository is empty or matches the proposed tree.
2. **State the intended change.** Identify the module, contract, tests, and user-visible outcome before making broad changes.
3. **Implement the smallest vertical slice.** Prefer one complete, tested path over many empty abstractions.
4. **Preserve scientific semantics.** Never collapse waveform time, simulation time, detection time, and alert-delivery time into one ambiguous timestamp.
5. **Never introduce future leakage.** Do not pass future samples to a detector under the guise of convenience.
6. **Test faults deterministically.** Randomness must be seeded and represented in run metadata.
7. **Do not fabricate data.** Synthetic data must be labeled synthetic and never used to claim real-world detection performance.
8. **Do not fabricate research results or citations.** Mark unknowns as unknown; ask for a source or implement a reproducible check.
9. **Respect data/model licenses.** Do not download, bundle, or redistribute assets without checking terms.
10. **Keep scope aligned.** Do not add a dashboard, database, cloud deployment, hardware driver, or ML model unless it supports the current milestone.
11. **Run the relevant tests.** Report exactly which tests were run and their outcome. If tests could not be run, say why.
12. **Document assumptions.** If an implementation makes a timing, sampling, event-matching, or fault-model assumption, write it down.
13. **Avoid silent behavior.** Invalid configurations, unknown units, and missing required metadata should cause clear errors or explicit warnings—not hidden defaults.
14. **Prefer backward-compatible changes.** If a stored schema or public API must change, version it and document migration implications.
15. **Finish with a concise handoff.** Summarize changed files, design choices, tests, known limitations, and the next best step.

### Before writing code, an agent should answer
- What is the current milestone?
- What existing behavior must remain correct?
- What is the smallest change that demonstrates progress?
- What invariant will the tests protect?
- Does the change affect reproducibility or scientific interpretation?
- What evidence will show that it works?

### Definition of done for a task
A task is done when:
- the implementation exists and fits the existing architecture;
- relevant tests pass or the blocker is explicitly reported;
- timing and units are documented where relevant;
- configuration and errors are validated;
- results are reproducible when the task affects experiments;
- the README/docs are updated if the public workflow changes;
- no unsupported scientific claims were added.

---

## 27. Immediate next actions

Start here, in this order:

1. Inspect the current QuakeNode repository and identify what already exists.
2. Create `docs/prior_art_audit.md` with a comparison matrix of existing tools and papers.
3. Write `docs/research_question.md` and `docs/evaluation-protocol.md` before optimizing the implementation.
4. Pick one accessible dataset and confirm its terms; create a tiny synthetic fixture for tests.
5. Implement a deterministic causal replay API with a test that proves future-sample leakage is impossible.
6. Implement a baseline detector and record both detection event time and emission time.
7. Add one deterministic transport fault—fixed delay—then packet loss.
8. Run paired no-fault/fault experiments and save a machine-readable manifest plus results.
9. Only then expand fusion, target-site warning utility, dashboard, and hardware adapters based on evidence.

**The highest-priority milestone is not “make QuakeNode look finished.” It is “make one small experiment causally correct, reproducible, and scientifically interpretable.”**

---

## 28. Glossary

- **EEW (earthquake early warning):** detecting an earthquake after it starts and attempting to warn places before strong shaking arrives.
- **Causal replay:** replaying data in a way that prevents a component from seeing information before it would have arrived.
- **Waveform time / sample time:** the timestamp associated with a recorded seismic sample.
- **Arrival time:** the simulated time at which data become available to a downstream component.
- **Detection time:** the time assigned to the detected signal/onset, depending on the detector's documented semantics.
- **Emission time:** the time the detector actually emits its result in the simulation.
- **Event fusion/association:** combining detections from multiple stations into a candidate earthquake event.
- **Warning time:** time between alert delivery to a target and a defined shaking threshold at that target; it can be zero or negative.
- **Fault injection:** deliberately introducing a controlled failure to study system behavior.
- **False trigger:** a detector/event output that does not match a reference event under the declared matching protocol.
- **Reproducibility manifest:** the configuration and metadata required to understand and rerun an experiment.
- **Offline evaluation:** evaluating a method on already available complete records, potentially without simulating real-time arrival constraints.
- **Future-sample leakage:** accidentally allowing a model or component to use samples that would not yet be available at decision time.

---

## 29. One-sentence north star

**QuakeNode should make it easy to prove—not merely claim—how an earthquake early-warning pipeline behaves when real-time causality, station availability, and network delivery are imperfect.**
