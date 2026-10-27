# QuakeNode development guidelines

Guidelines for contributors. The long background is in `context.md` and the Phase 1 audits in `docs/phase1/`. Do not edit those; they are the historical record.

## What this project is

QuakeNode is an open-source Python package and research testbed for evaluating earthquake early warning (EEW) detectors as **causal streaming systems**, with deterministic fault injection and reproducible experiments. It is paired with a paper. It is a research tool, never an operational warning system. Every README, demo and CLI banner must say so.

## Goals (in priority order)

1. A tool other researchers can `pip install` and run in under 5 minutes (clear README, one-command demo, good docs).
2. A paper whose result comes from the tool: how offline-processed benchmarks differ from causal streaming evaluation. Report negative or null results honestly.
3. Stars and citations follow from 1 and 2. Never chase them with overclaiming.

## Current research question (narrow, from Phase 1)

For matched INSTANCE reviewed-P traces, how much does the released full-window detrended/resampled count product change a fixed STA/LTA detector's P-relative trigger behavior compared with causal processing of the same raw waveform? The broader tool framing (replay, faults, detector plugins) is the vehicle for this result.

## Hard rules

- **No future-sample leakage.** Detectors only see data delivered by the logical clock. Any change touching timing, preprocessing or replay needs a test that alters only future samples and asserts identical earlier outputs.
- **Keep clocks separate:** sample time, packet-ready time, arrival time, emission time. Never merge them.
- **No fabricated data, numbers or citations.** Synthetic data is always labeled synthetic and only supports software-invariant claims. Unknown means `None` plus a reason.
- **No novelty claims** ("first", "no one has") until the prior-art artifact check is done. QCN, EPIC Alaska, CREW, Zuccolo et al. 2021, Meier 2017 already cover real-time EEW evaluation broadly.
- **No claims** of system recall, operational false-alert rate, or target warning time unless the data and method truly support them. Outcomes are limited to picked-trace behavior.
- **Never commit waveform data.** `data/` is gitignored. Respect dataset licenses; record source, DOI, checksum, retrieval date.
- **Do not tune on evaluation outcomes.** Freeze parameters and protocol before running the real-data comparison; record the freeze (commit hash in the manifest).
- Deterministic by default: seeded randomness, no wall-clock `sleep` for simulation logic.
- Fail loudly on invalid config, unknown units, missing metadata. No silent fallbacks.

## Stack and conventions

- Python >= 3.10. Host: system `python3` is 3.9.6 (too old); use Homebrew `python3.11` (project `.venv`) and `python3.12` for checks. 3.10 is only exercised in CI. `src/` layout, package name `quakenode`.
- Runtime deps minimal: numpy, scipy first. Add obspy, pyyaml, pydantic, matplotlib only when a task needs them.
- Dev: pytest, ruff. Type hints on public APIs. Small functions.
- License: MIT. Code only; datasets and weights have their own terms.
- Every run writes a manifest (schema version, config snapshot, seeds, git commit, python and dependency versions, dataset IDs and checksums, metric definition version).

## Workflow rules for you

1. Inspect before editing. State the intended change and the invariant the tests protect.
2. Smallest vertical slice. No empty modules, no dashboard, no database, no ML model, no MQTT until a milestone needs it.
3. Run tests (`pytest`) and report exactly what ran and the result. If something cannot run, say why.
4. Do not alter `context.md` or anything under `docs/phase1/`. New docs go in `docs/`.
5. End every change with a concise summary: files changed, design choices, tests run and outcome, known limitations, suggested next step.
6. Commit in small logical commits with clear messages.

## Existing assets

- **Tool (v0.2.0, D7/D8/D9):** `quakenode` CLI (`demo`, `run`, `sweep`, `compare`, `report`, `validate`, `version`) over a strict YAML config (`config.py`); `experiment.py` runs seeds and writes manifest/events/metrics/report/plots (`report.py`); `faults/` (seeded, composed, `FaultRecord`s); `scenario/` (SYNTHETIC network generator); `fusion/` (k-of-n on the emission clock); `evaluation/` (metrics, `docs/metrics.md`); `streaming/` (`StreamDetector` protocol, registry, `sta_lta_rms`, `recursive_sta_lta`, out-of-order policies reject/drop_late/buffer; gap policies reset/hold/zero_fill, `docs/gap_policies.md`). Real recorded events: `scenario.source: instance_event` (`data/instance_event.py`, extra `data`; `examples/instance_event/`, `docs/dev_events.txt`, `docs/real_event_demo.md`), tool demonstrations only. `--set key=value` overrides on the CLI; sweeps pair each point with a matched no-fault control. Examples: `examples/synthetic_network/`. Docs: `docs/architecture.md`, `docs/metrics.md`, `CONTRIBUTING.md`, `CHANGELOG.md`. Runtime deps: pyyaml only; matplotlib is the optional extra `plots`. Never commit `runs/`.
- `src/quakenode/`: `preprocessing/` (offline mean/detrend, causal one-pole with chunk state), `detectors/sta_lta.py`, `manifest.py` (RunManifest schema v1), `replay/` (Packet, VirtualClock, ReplayEngine, Receiver, Detection record), `streaming/` (streaming one-pole, incremental STA/LTA, StreamingPipeline with gap/order policy). Synthetic-only so far.
- `src/quakenode/data/`: lazy-import adapters for the INSTANCE release Z array, raw miniSEED windows and replay packets (`pip install -e ".[data]"`). Scripts: `draw_cohort.py`, `fetch_cohort.py` (resumable, polite), `build_cohort.py`. Docs: `cohort_stage1_summary.md`, `stage1_protocol_options.md` (draft).
- `experiments/synthetic_causality.py`: thin script over the package; text output must stay byte-identical (baseline check) and `--json` includes provenance and a manifest. `experiments/synthetic_streaming.py` runs the causal path through replay (results in `docs/synthetic_streaming.md`). Both emit `results_sha256` in `--json`. Tests in `tests/` (201 passing with the `data` extra installed).
- Phase 1 record committed unmodified: `context.md`, `docs/phase1/`, `experiments/configs/phase1_protocol.yaml` (draft, historical).
- Ruff config is explicit in `pyproject.toml` (ruff 0.17's built-in default rule set is broad, so do not rely on it). CI runs `ruff check`, `ruff format --check`, `pytest`.
- `data/` (gitignored): INSTANCE sample archive, extracted to `data/instance_sample/` (metadata CSVs, counts/gm/noise HDF5, inventory.json), raw INGV miniSEED probes in `data/raw/`. Inspected only (`scripts/inspect_instance_sample.py`, `scripts/pair_instance_traces.py`, results in `docs/instance_access.md`); no detector run on it. Pre-registered detrend/cast check done (`docs/detrend_check_results.md`): released Z counts are within about 1 count of a window least-squares-line removal truncated to int (HH only well tested), never exact. Install with `pip install -e ".[dev,data]"`.

## Decisions (full log in `docs/decisions.md`)

- D1: offline arm = the released INSTANCE HDF5 array, labeled "release product". The pre-registered equivalence to a window linear fit subtracted then truncated (84/88, Wilson 88.9 to 98.2%, HH only) is a caveated equivalence, not an exact reproduction.
- D2: cohort = IV network, HH, Z component, 100 Hz native. HN excluded; reopening needs a separate pre-registration.
- D3: causal arm = raw INGV miniSEED processed causally.
- D4: positioning = P2 in two stages (Stage 1 STA/LTA release vs causal; Stage 2 SeisBench pickers, optional extra only; SeisBench is GPL-3.0, never vendored, never imported from the core package).
- D8: gap handling is a configurable policy (reset default, hold, zero_fill); real recorded event replay uses ONLY development events with no trace in the frozen Stage 1 draw (`docs/dev_events.txt`); real-event runs are tool demonstrations, never scientific claims; Stage 1 files stay untouched.
- D7: near-term goal is a credible, usable open-source TOOL, not a paper; real-data Stage 1/2 work is paused (its files stay untouched). Scenario data in the tool are SYNTHETIC and must say so everywhere. (No D6 exists.)
- D5: Stage 1 cohort = seed 20261105, 1,000 of 3,701 IV/HH traces, list `docs/cohort_stage1_traces.txt` (sha256 in `docs/decisions.md`); no replacements for excluded traces.

## Tool rules (from D7)

- Faults and the synthetic generator use only `quakenode.faults.rng.Stream` (built on `random.Random(seed).random()`, stable across Python versions); every fault change needs a pinned-pattern test and keeps the whole-chain future-mutation counterfactual green with faults applied.
- Float sums that reach outputs use `math.fsum` (built-in `sum()` rounds differently from Python 3.12; this once changed result hashes across versions). Results of the example configs must have the same `results_sha256` on 3.11 and 3.12.
- Fault records must match what actually happened (affected packet keys, applied/skipped).
- Every CLI command prints the banner "QuakeNode is a research testbed, not an operational warning system."; every report and manifest says the data are SYNTHETIC.
- Run directories are unique and never overwritten.
- Real-data outputs always carry the input kind and data source; `release_hdf5` is labeled "NOT causal input". Never commit waveforms; development events only (D8). Zero-filled samples are always labeled and never counted as evidence.

## Prior-art rule (from `docs/prior_art_artifact_check.md`)

- Positioning and novelty wording in the README, docs or paper must be traceable to that audit. No "first", "novel" or "no one has" until its "minimum evidence" checklist is complete; use "we are not aware of ..." with the search protocol and date.
- SeisBench is GPL-3.0: use only as an optional extra, never vendor its code. "CREW" is ambiguous (EPOS testing center versus the SeisBench CREW dataset); always say which.

## Known limits to carry forward (from the audit)

- Cross-arm detector differences in the synthetic study mix future dependence with filter response and scaling; only the prefix-counterfactual isolates causality.
- Protocol chronology cannot be proven without git history; use git from now on and record commit hashes.
- Record Python version and source/config hash in every JSON output.
