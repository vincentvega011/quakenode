# Good first issues

Concrete, bounded tasks for new contributors. Each lists the files involved and what "done" means. Read `CONTRIBUTING.md`
first: the hard rules (no future-sample leakage, the four clocks kept apart, determinism, no novelty or operational
claims) apply to every task. QuakeNode is a research testbed, not an operational warning system. Sizes are rough guesses.
These are suggestions, not commitments: open an issue before starting so effort is not duplicated.

## 1. New fault: linear clock drift (small to medium)

A station clock that drifts linearly, as opposed to the constant `clock_offset`.

- Files: `src/quakenode/faults/library.py`, `src/quakenode/faults/__init__.py`, `src/quakenode/config.py` (`FAULT_SPECS`),
  `src/quakenode/experiment.py` (`build_fault`), `tests/test_faults.py`, `docs/architecture.md` (fault table).
- Acceptance: parameters `drift_ppm`, `targets`, `start_s`, `end_s` validated by the strict schema; only packet timestamps
  change, never sample values; a `FaultRecord` lists the affected packet keys; a pinned-pattern test for a fixed seed;
  the whole-chain future-mutation counterfactual stays green with the fault applied.

## 2. New detector: absolute-amplitude threshold (small)

A deliberately simple detector (trigger when the one-pole high-passed absolute amplitude exceeds a threshold), useful as a
second plug-in example.

- Files: `src/quakenode/streaming/detectors.py`, `src/quakenode/streaming/registry.py` (registration), `tests/test_pipeline_policies.py`
  (pattern for plug-in tests), `README.md` ("Add a detector").
- Acceptance: implements the `StreamDetector` protocol (`reset()` after a gap, `process(packet, processed_at_s)`); a
  hand-computed toy case; identical output for different packet lengths of the same signal; a config using it passes
  `quakenode validate`.

## 3. New metric: false candidates per station-hour (small to medium)

Event-level false candidates are counted, but not normalised.

- Files: `src/quakenode/evaluation/metrics.py`, `src/quakenode/experiment.py` (`HEADLINE_METRICS` and `aggregate`),
  `src/quakenode/report.py`, `docs/metrics.md`, `tests/test_metrics.py`.
- Acceptance: defined in `docs/metrics.md` (including when it is `None` and why); hand-computed test; metric version
  string bumped if an existing output changes; reports show it. Note that on SYNTHETIC data this is a software metric, not
  a false-alert rate.

## 4. Plot: per-station detection timeline (medium)

A figure with one row per station showing the catalog or synthetic P time, the detection trigger time and the emission
time on a shared axis.

- Files: `src/quakenode/report.py` (`plot_run`), `tests/test_experiment_cli.py` (plots exist when matplotlib is installed).
- Acceptance: titled with the data label via `_title` (SYNTHETIC or real-event input kind); the sample, arrival and emission
  clocks are visibly distinguished; works when no station detects; no new hard dependency (matplotlib stays optional).

## 5. `quakenode list` for detectors and faults (small)

Print the registered detectors with their parameter tables, and the fault types with their parameters.

- Files: `src/quakenode/cli.py`, `src/quakenode/streaming/registry.py`, `src/quakenode/config.py` (`FAULT_SPECS`),
  `tests/test_experiment_cli.py`.
- Acceptance: `quakenode list detectors` and `quakenode list faults` print the banner and a table including types,
  defaults and ranges taken from the same specs the validator uses (no second copy); non-zero exit on an unknown topic.

## 6. `quakenode compare` from a YAML spec (medium)

`compare` takes `--a` and `--b` on the command line; allow a small spec file instead.

- Files: `src/quakenode/cli.py`, `src/quakenode/compare.py`, `tests/test_compare.py`, `README.md`.
- Acceptance: a documented spec format (config path, `a:` and `b:` override mappings, optional shared overrides) validated
  strictly with errors naming the file and key; identical results to the equivalent command-line call (same
  `results_sha256`); the spec is recorded in the manifest.

## 7. Tutorial: write and test your first detector (small, docs only)

A step-by-step page that builds a tiny detector from scratch and runs it through `quakenode run` and `quakenode compare`.

- Files: new `docs/first_detector.md`, link from `README.md` and `docs/architecture.md`.
- Acceptance: every command in the page was run and its real output pasted; the code is in a runnable file under
  `examples/`; the page states that results are on SYNTHETIC data.

## 8. Windows and macOS testing (small to medium, needs a Windows machine)

CI has experimental Windows and macOS entries that nobody has verified locally.

- Files: `.github/workflows/ci.yml`, `src/quakenode/` (any path or encoding issue found), `tests/`, `README.md`
  ("Status and limitations"), `CONTRIBUTING.md`.
- Acceptance: run `pip install -e ".[dev,data,plots]"`, `ruff check .`, `pytest` and the README quickstart on Windows; open
  an issue or PR listing every failure; fix path, newline or encoding problems; confirm `results_sha256` of the example
  configs is the same as on Linux/macOS; only then remove `continue-on-error` for Windows and update the README claim.

## 9. Gap-policy plot labels and legend polish (small)

The gap-policy sweep figure in the README is the most visible output; make it easier to read.

- Files: `src/quakenode/report.py` (`_sweep_plot`), `docs/img/` (regenerated figure), `README.md`.
- Acceptance: direct legend labels for the three policies, the control line labelled in the legend, colour-blind-safe
  colours, readable at README width; figure regenerated with `quakenode sweep examples/synthetic_network/sweep.yaml`
  and the command recorded in the caption.

## 10. Docs fix pass: examples and commands that actually run (small, docs only)

- Files: `README.md`, `examples/*/README.md`, `docs/*.md` (except `docs/phase1/`, `context.md` and the Stage 1 documents,
  which are the historical record).
- Acceptance: every shell command in the listed files was executed in a fresh virtual environment; those that fail are
  fixed or removed; a short list of what was checked is in the pull request.
