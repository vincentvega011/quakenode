# QuakeNode repository reconnaissance

**Inspection date:** 2026-10-26  
**Scope:** Root workspace contents and the complete root `context.md`. No application code was present to inspect.

## Executive summary

The current `<workspace>` workspace is a planning-only starting point: its only file is `context.md` (52,675 bytes). There is no Git repository, README, package metadata, application source, tests, CI configuration, experiment, adapter, data file, license, or other project documentation. Consequently, no existing runtime, package manager, supported operating system, runnable test command, or implemented QuakeNode capability can be established from repository evidence.

The context describes an intended Python software research testbed, but explicitly frames its architecture and commands as proposals. It requires causal replay, explicit data/sample/arrival/detection time semantics, deterministic fault scenarios, reproducible manifests, defined evaluation metrics, and careful dataset licensing. These are constraints for future work, not evidence that any feature exists. The first useful step is therefore to establish a version-controlled baseline and a small documented synthetic fixture/protocol before implementation; the next step should not assume a codebase or existing architecture.

## Current repository map

```text
quake/
├── context.md
└── docs/
    └── phase1/
        └── repository_reconnaissance.md   # this report
```

`docs/phase1/repository_reconnaissance.md` was created for this task. Before it was created, `context.md` was the only file found in the workspace, including hidden files. The workspace root is not inside a Git repository (`git status --short --branch` returned `fatal: not a git repository`). No neighboring directory was treated as part of QuakeNode.

Relevant context references:

- Project purpose/status and software-first research scope: `context.md:3-11`.
- Proposed data flow and responsibilities (not implemented architecture): `context.md:170-197`, `context.md:199-...`.
- Proposed repository layout explicitly described as adaptable: `context.md:276-335`.
- Data-time versus simulated-arrival-time schema concepts: `context.md:339-375`.
- Recommended stack and engineering standards: `context.md:600-630`.
- Dataset and licensing integrity constraints: `context.md:576-596`.
- Proposed metric definitions/denominators and warning-time caution: `context.md` section 14.
- Agent inspection and scientific-semantics rules: `context.md` section 26.

Line references above are grounded in the context file; some section references are used where exact line numbers would be less useful than the named section.

## Implemented / partial / absent capability table

“Absent” means not found in this workspace; it does not claim that no external/untracked copy exists elsewhere.

| Capability / project area | Status | Repository evidence |
|---|---|---|
| Python package, CLI, application architecture | Absent | No source tree, package metadata, entry point, or scripts. Python 3.11+ and CLI options are recommendations only (`context.md` sections 16–17). |
| Waveform loading / dataset adapters | Absent | No adapter code, sample waveform, catalog, station table, or data directory. Context specifies desired behavior (`context.md` section 8, `data/`; section 15). |
| Time handling / causal streaming replay | Absent | No replay implementation or tests. Context defines the required distinction between sample and simulated arrival times (`context.md:343-361`) and causal invariant (section 11). |
| Stream transport / network behavior | Absent | No transport interface or queue. In-process transport is a suggested starting point; MQTT is optional later (`context.md` section 8, `transport/`). |
| Detectors | Absent | No detector code or model assets. STA/LTA and SeisBench are candidate future choices, not present features (`context.md` section 13 and section 15). |
| Fusion, event association, alerts | Absent | No modules or schemas. The K-of-N rule and alert states are proposals (`context.md` sections 8 and 13). |
| Fault injection | Absent | No fault code/config. Delay, jitter, loss, reordering, outages, clock errors, and deterministic seeds are requirements/proposals (`context.md` section 12). |
| Metrics / evaluator | Absent | No evaluator or results. Metrics and required denominators are specified in `context.md` section 14 only. |
| Experiment manifests / reproducibility | Absent | No config, manifest, run output, or experiment. Manifest fields and CLI flows are illustrative target behavior (`context.md` sections 10, 17–18). |
| Data, license, station metadata | Absent | No data or license files found. Dataset choice and permission remain unresolved; the context requires checking terms (`context.md:576-596`, section 25). |
| Tests / CI | Absent | No test directory, test configuration, workflow, or CI files. Test strategy in context section 19 is aspirational. |
| Documentation / experiments | Partial | Root `context.md` is extensive project guidance. No README, architecture note, protocol, prior-art review, experiment, or runbook exists. |
| Hardware / dashboard | Absent and explicitly later/non-goal for initial phase | No hardware, UI, or dashboard code. Context says software-first and defers physical nodes/dashboard (`context.md:9-11`, sections 4 and 21). |

## Existing tests and how to run them

No tests or test runner configuration exist. No command can be identified as the repository’s test command, and no tests were run. `pytest` appears only as a recommended dependency and example command in `context.md` sections 16–17; that does not establish an installable project or runnable suite. The context’s suggested install/run commands are target examples and expressly should not be claimed to work before implementation.

## Runtime, operating systems, package manager, and architecture

- **Current language/runtime:** Not established; there is no implementation. The context recommends Python 3.11+ (`context.md:600-612`), which is a proposal rather than a project pin.
- **Supported operating systems:** Not documented. The inspection environment is macOS, but that does not imply project support.
- **Package manager / dependency files:** None found (`pyproject.toml`, requirements files, lockfiles, `package.json`, etc. are absent).
- **Architecture:** No existing code architecture. The context proposes a modular, single-process Python design and specifically says to adapt to the actual codebase rather than recreate its proposed tree blindly (sections 8–9).
- **Git state:** Not applicable; this directory is not a Git worktree, so branch, commit, and tracked/untracked status are unavailable.

## Data and licensing status

No waveform, event catalog, station metadata, model weights, dataset references with retrieval details, or license/third-party notice files were found. Therefore data provenance, terms, redistribution rights, channels, units, sample rates, station coverage, and record quality are unknown. The prior-art list and candidate tools in `context.md` sections 15 and 24 are starting points, not selected or approved data sources. Do not infer that an accessible public dataset is redistributable. A synthetic fixture can support software invariants, but cannot support seismological performance claims (`context.md:585-596`).

## Scientific and engineering risks

Because no implementation exists, these are unresolved design/verification risks rather than observed code defects:

1. **Future-sample leakage:** no replay API or invariant test exists. The context labels this critical and requires detectors to receive only data made available by logical simulation time (section 11).
2. **Ambiguous timestamps:** no schema exists. Future code must separate recorded sample time, simulated arrival/availability time, detection/onset time, detector emission time, alert decision, and delivery time (`context.md:343-375`, section 10).
3. **Hidden resampling/preprocessing and units:** no loader or preprocessing code exists. Dataset format, units, filtering, and resampling are not documented; these must be explicit and validated before a real waveform experiment (sections 8 and 15).
4. **Silent gap filling or packet reordering:** no behavior is implemented. Context calls for representing gaps and documenting reordering/buffering rather than silently interpolating or hiding faults (sections 11–12).
5. **Nondeterministic randomness:** no fault engine exists. Seeded, recorded random processes and repeatability checks remain to be designed (sections 12 and 19).
6. **Metrics without denominators/matching rules:** no metrics exist. The context explicitly requires defined eligible-event populations, event matching, false-trigger denominators, exclusions, and station completeness denominators (section 14).
7. **Warning-time overclaim:** there are no target-site ground-motion data or computation. Context says warning time is valid only when target threshold and alert delivery times share a defensible timeline; otherwise report latency (section 14).
8. **Unsupported operational claims:** context states this is not a validated public warning service and excludes public alerting and safety claims (`context.md:3-5`, sections 4 and 20).

## Constraints and assumptions

### Explicit project constraints from context

- Treat QuakeNode as a software-first research prototype, not a public warning service; no earthquake prediction or operational safety claims (`context.md:3-11`, section 4).
- Inspect and adapt to actual repository state; the proposed architecture is not mandatory (`context.md` sections 9 and 26).
- Prioritize causality, explicit assumptions, deterministic fault scenarios, defined metrics, reproducibility, and a small end-to-end slice (sections 6–7, 11–14).
- Do not fabricate data, metadata, citations, or results; distinguish synthetic software tests from real-record evaluation (sections 15, 20, 23, 26).
- Check licensing for datasets, models, and metadata before use or redistribution (sections 8, 15, 25).
- Defer a dashboard, physical hardware, and complex services until the core workflow warrants them (sections 4, 8, 21).

### Not established

No compute budget, deadline, dataset, hardware availability, OS matrix, CI provider, package manager, or existing coding convention is established by repository evidence. The nine-day sprint in context section 22 is explicitly conditional (“if that deadline still applies”), so it is not treated as an active deadline. The recommended Python stack is not an adopted dependency set.

## Dependency and maintenance risk list

There are currently no project dependencies to assess for version, license, security, or maintenance risk. This is an inventory finding, not a reason to replace or preemptively add dependencies.

Risks to manage when dependencies are selected:

- Numeric/seismology stack (NumPy/SciPy/ObsPy) can constrain supported Python/platform versions and waveform semantics; choose only where a real format or computation requires it, and record versions.
- Optional ML packages/models can add large transitive dependencies, compute requirements, model/data licensing questions, and input-convention mismatches; context places them after baseline validation (`context.md` sections 13 and 16).
- CLI/schema/plotting libraries should remain minimal until a concrete interface needs them; the context recommends alternatives rather than mandating them (`context.md:604-620`).
- No lockfile, CI, contributor instructions, or environment pinning currently exists, so future reproducibility and maintenance baselines are absent.

## Recommended immediate next step

Create the project’s Git baseline and agree on a minimal runnable vertical slice before adding broad architecture. The lowest-rework evidence-producing slice is a tiny, explicitly synthetic waveform fixture plus a documented schema/time contract and a test proving that a consumer cannot see samples before their logical availability. In parallel, record an actual supported Python version and a minimal dependency/test setup in project metadata. This directly tests the most important scientific invariant without prematurely selecting real data, ML models, transport infrastructure, dashboard technology, or an unverified dataset. The context’s own staged plan puts data/schema and synthetic fixture before replay and detectors (section 21).

## Phase 1 blockers

The next phase can proceed with design/protocol work, but implementation work is blocked by the absence of a Git baseline, source/package structure, test harness, and selected data contract. No external data choice is required for the first synthetic causal-replay proof. Before any real-record performance experiment, the team must choose a dataset and confirm its license and metadata; before claiming platform support, it must define and exercise an OS/runtime matrix. No tests were run in this reconnaissance.
