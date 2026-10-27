# QuakeNode repository reality audit

**Inspection date:** 2026-10-26  
**Scope:** workspace at <workspace>; context.md; all four remediation documents; repository files, manifests, data candidates, tests, and prior-art documents.  
**Result:** this workspace is a documentation-only research plan. It is not a Git checkout and contains no executable QuakeNode implementation.

## Executive summary

The tree contains context.md, Phase 1 reports/ADR, and one draft YAML protocol. It contains no README, application source, executable script, test file, CI workflow, dependency/package manifest, lockfile, waveform/metadata data file, or Git metadata. There is no current application entry point or project command.

The causal-preprocessing concern is supported by the INSTANCE data paper, not by local code: the paper describes mean/linear detrending over each 120 s digital-count trace and resampling to 100 Hz before HDF5 release. This workspace has no INSTANCE HDF5, original miniSEED, loader, transform implementation, or cache to inspect. The effect on detector outcomes is unknown.

The command python3 -m unittest discover -v returned exit 0 and “Ran 0 tests”; it validates no behavior. Python 3.9.6 is installed on this host, but the repository does not declare Python as a supported runtime. pytest was not found on PATH. No package/runtime support matrix or supported OS is documented.

## Git and workspace state

- git status --short --branch → exit 128: “fatal: not a git repository (or any of the parent directories): .git”.
- git log -8 --oneline --decorate → same exit 128.
- Therefore recent commits and whether files were previously modified/untracked cannot be established. This is not a verified clean working tree.
- The visible files include remediation reports already present at inspection start. This audit adds only the three requested documentation files; it does not modify application code.

## Current repository map

| Path | Actual role/status |
|---|---|
| context.md | Aspirational project description, research principles, proposed architecture and phased plan. It explicitly says proposed commands should not be claimed as working before implementation (§17, lines 639–663); see also lines 5, 11, 42–50. |
| docs/phase1/repository_reconnaissance.md | Earlier source/document reconnaissance report; not executable evidence. |
| docs/phase1/prior_art_audit.md, prior_art_matrix.csv | Prior literature/tool comparison; records artifact/license unknowns. |
| docs/phase1/research_gap_decision.md | Earlier candidate assessment; broad testbed framing is superseded by the NO-GO/remediation analysis. |
| docs/phase1/dataset_feasibility.md | Source-based dataset feasibility review; no dataset downloaded or queried. |
| docs/phase1/evaluation_protocol.md | Preregistration draft, not an executed experiment. Describes one-channel HNZ STA/LTA and no fusion. |
| experiments/configs/phase1_protocol.yaml | Protocol description only; line 1 says no experiment implementation consumes it. Data paths/checksum/event IDs are null and access/download flags false (lines 13–45). |
| docs/phase1/architecture_decision.md, adr/0001-minimum-research-prototype.md | Proposed design/ADR for an unimplemented prototype. |
| docs/phase1/adversarial_review.md | Prior NO-GO review. |
| docs/phase1/remediation_plan.md, causal_preprocessing_audit.md, metric_validity_matrix.md, revised_research_question.md | Current remediation analysis; conditional, not code/test results. |
| .DS_Store, docs/.DS_Store | Host-generated metadata, not project components. |

No README or license file is present. experiments/configs/phase1/ exists as an empty directory. No package source directory exists.

## Components, entry points and commands

| Component | Status | Evidence |
|---|---|---|
| CLI / run command | Absent | No executable files, package entry points or scripts. Commands listed in context.md §17 are explicitly target commands only. |
| Dataset adapter / waveform loader | Absent | No Python files or local data; architecture describes a proposal. |
| Replay scheduler / virtual clock | Absent | No implementation. |
| Detector | Absent | STA/LTA settings appear only in evaluation_protocol.md and YAML lines 67–83. |
| Fault injector / seed logic | Absent | Scenario configuration exists only in YAML lines 107–150 and later sections. |
| Fusion / alert state machine | Absent for proposed experiment | Protocol says no fusion/association/alert timing; YAML lines 60–65, 85–105. |
| Metrics / event matching | Absent | Formula and denominator are protocol text only. |
| Reporting / manifest generation | Absent | Described in context/architecture, no code. |
| CI | Absent | No workflows or pipeline files. |
| Existing test command | No project test command | No tests or package/test configuration found. |

Commands/evidence:

- find . -maxdepth 5 -type f -print | sort shows only context, Phase 1 documents/CSV, YAML config and .DS_Store.
- rg --files scoped to Python, scripts, package/config/test patterns finds only experiments/configs/phase1_protocol.yaml.
- Search for HDF5, miniSEED, JSON, XML, waveform manifests, README, requirements and pyproject.toml finds only the prior-art CSV among data-like patterns.
- python3 --version → Python 3.9.6 at /usr/bin/python3; host information, not project support.
- command -v pytest → no executable found on PATH.
- python3 -m unittest discover -v → exit 0, zero tests discovered, output “Ran 0 tests / OK.” No behavior is validated.

No dependencies or package manager are declared. No install/build/run command can be derived.

## Data and preprocessing reality

### Local data

No raw INSTANCE miniSEED, INSTANCE HDF5, StationXML, event metadata, local data manifest/checksum, or experiment output is present. YAML lines 19–23 mark access/download false and paths/checksum null; lines 30–45 leave cohort/schema fields unresolved.

### Exact proposed product

The protocol selects the INSTANCE v3 sample, HNZ vertical, digital counts, 100 Hz, 120 s (experiments/configs/phase1_protocol.yaml:13–45). No event/station/channel IDs are frozen; event_ids is null at line 30. The proposal is a selection rule, not an enumerated cohort.

### Transform implementation audit

No local function performs detrending, normalization, filtering, resampling or windowing: there are no application Python files. The exact transformations are documented only in Michelini et al. (2021), INSTANCE §§2.1.3–2.1.6:

- archived miniSEED is selected/cross-checked, gap-containing records removed, trimmed and made into 120 s windows;
- digital-count traces have mean and linear trends removed and are resampled to 100 Hz before HDF5 publication;
- SNR and quality metadata are calculated from waveform windows; a sliding Hampel spike summary is also described;
- a separate physical-unit branch removes instrument response with frequency corners and tapers; the proposal does not select it.

The paper does not provide enough detail in the inspected methods to identify exact detrend options or resampling temporal support. No local preprocessing function, parameters, cache or intermediate output exists.

| Operation | Local code evidence | Source-paper evidence | Conclusion |
|---|---|---|---|
| Detrending | None | Whole-trace mean and linear trend removal before HDF5 | Future-dependent processing is established by source description, not by local executable code. |
| Resampling | None | Resample to 100 Hz; exact kernel/options unknown | Applied upstream; causal support unresolved. |
| Filtering / response removal | None | Response removal/tapers for separate physical-unit branch | Not selected by current digital-count protocol. |
| Normalization | None | No count normalization found in described steps; arrays not inspected | Unknown for exact release artifact. |
| Windowing | None | 120 s windows; actual starts can vary | Exact sample/P mapping unresolved. |
| Cache | None | No local data/cache | None to audit. |

The prior causal finding is verified against the data paper, not against a QuakeNode loader. It is not possible to test whether detrending changes outcomes without same-record data and a detector implementation.

## Evidence versus proposal

**Verified locally:** workspace inventory; absence of Git metadata, code, tests, data and dependencies; YAML draft values; zero-test discovery; host Python version.

**Verified from primary sources, not local code:** INSTANCE digital-count preprocessing and reviewed-P selection; EIDA policy/network-specific access terms; QCN, EPIC, CREW and real-time comparison descriptions (see prior_art_review.md).

**Proposed/unverified:** raw EIDA access for exact records; HNZ coverage in the sample; event/P/time joins; original sample rate and raw-to-release alignment; network licenses; causal preprocessing choice; metrics/results; candidate novelty.

## Smallest missing pieces blocking a causal experiment

1. Data feasibility manifest with actual sample IDs, HNZ rows, station/event/P joins, rates, starts, units, gaps/flags and exclusions.
2. Legally usable original miniSEED plus StationXML that can be aligned to release traces, with per-network terms recorded.
3. Exact time mapping and preprocessing provenance, including whether the release resampling can be reproduced.
4. Streaming input contract and stateful transform/detector; currently only design text exists.
5. Full-path counterfactual, arrival-cutoff, chunk and gap tests. Current test discovery finds none.
6. Narrowed preregistration with picked-trace denominators and artifact-checked contribution.

The next evidence step is data/metadata feasibility and artifact review, not a replay engine or dashboard.

