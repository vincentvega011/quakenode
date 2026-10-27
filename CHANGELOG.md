# Changelog

All notable changes. Research testbed, not an operational warning system.

## 0.2.0

- **`quakenode compare CONFIG --a K=V[,K=V] --b K=V[,K=V]`**: runs one scenario twice with different overrides on the
  same seeds and pairs the arms per station: detection status (both / only A / only B / neither), paired sample- and
  emission-clock latency differences (B minus A), event association latency, medians and quartiles. For recorded events
  with different station sets (for example missing raw data) both arms are re-run on the common stations and the
  dropped stations are listed. Writes `compare.md`, `compare.csv`, `compare.json` (with a manifest recording both
  override sets) and a plot; labels carry the input kind (`release_hdf5` is "NOT causal input").
- **`quakenode demo [--dir DIR]`**: writes the packaged SYNTHETIC example configs and runs them; works from an installed
  wheel with no repository files.
- Package metadata completed (MIT SPDX licence, classifiers, keywords, project URLs);
  explicit UTF-8 for text I/O; POSIX-style relative paths in sweep results.
- GitHub scaffolding: issue and pull request templates, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CITATION.cff`,
  Dependabot, `docs/good_first_issues.md`; CI adds macOS, an experimental Windows entry and a wheel build/install job.
- README: badges, "Why this exists", "Status and limitations", "Related tools" (from `docs/prior_art_artifact_check.md`).
  Fixed the quickstart override example for switching detectors (the other detector's parameters must be given too).

- **Gap policies** (`pipeline.gap_policy`): `reset` (default, previous behaviour), `hold`, `zero_fill`; every policy logs
  `GapEvent`s with the missing and filled sample counts; filled samples are labeled in events and metrics and detections
  triggered on them are kept out of hits, false triggers and (by default) fusion (`docs/gap_policies.md`). Nothing is
  interpolated.
- `--set key=value` (repeatable) on `run`, `sweep` and `validate` for dotted config paths, validated by the strict schema
  and recorded in the manifest.
- Sweeps accept non-numeric parameters (detector names, gap policies) and pair every point with a MATCHED no-fault
  control (same non-fault settings); `sweep.yaml` now crosses packet loss with the three gap policies and
  `sweep_detector.yaml` compares the two detectors at fixed loss. `runs/control` is now `runs/control_01...`.
- **Real recorded event replay** (`scenario.source: instance_event`, extra `data`): INSTANCE release HDF5 or raw INGV
  miniSEED input, stations on one clock, catalog P (with stated uncertainty) as reference, earliest-P event reference,
  outputs labeled with input kind and data source; `scripts/select_dev_events.py`, `scripts/fetch_dev_events.py`,
  `examples/instance_event/`, `docs/dev_events.txt`, `docs/real_event_demo.md` (tool demonstrations on 3 development
  events, not performance evidence; the events have no trace in the frozen Stage 1 draw).
- `Detection.on_filled_samples`, `Trace.first_sample_index` (shared multi-station timeline), `metrics.event_reference`.
- CI validates every example config.

## 0.1.0

- `quakenode` command line: `run`, `sweep`, `report`, `validate`, `version`.
- YAML experiment config (schema version 1) with strict validation; `pyyaml` is now a runtime dependency, `matplotlib`
  is the optional extra `plots`.
- Seeded fault injection on packet lists: fixed delay, jitter (uniform, exponential), packet loss (Bernoulli,
  Gilbert-Elliott), duplicate, reorder, station outage, clock offset, missing samples; every fault writes a `FaultRecord`.
- Configurable out-of-order policy in the streaming pipeline: `reject`, `drop_late`, `buffer` (reordering buffer with
  `max_wait_s`).
- `StreamDetector` protocol and detector registry; second built-in detector `recursive_sta_lta`.
- SYNTHETIC multi-station network scenario generator.
- k-of-n fusion on the emission (or arrival) clock with per-step decision log.
- Metrics (latency on the sample and emission clocks, detection rate, false triggers, completeness, association
  latency, event detection rate, seed-paired fault sensitivity); definitions in `docs/metrics.md`.
- Reports and plots per run and per sweep; manifests with config snapshot, seeds, git commit, versions.
- Packet gains an optional `reported_first_sample_time_s`; `Detection` gains an optional
  `reported_trigger_sample_time_s` (both default to `None`).

- Float aggregation uses `math.fsum`, so result hashes are identical on Python 3.11 and 3.12.

## 0.0.1

- Foundation: preprocessing, STA/LTA, replay engine with separate clocks, streaming pipeline, run manifest, synthetic
  experiments, INSTANCE data adapters and inspection scripts.
