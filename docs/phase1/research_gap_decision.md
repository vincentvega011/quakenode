# Research gap decision: skeptical review

**Decision date:** 2026-10-26  
**Review basis:** Full `context.md`, repository reconnaissance, prior-art report, and CSV matrix. Key primary sources in the audit were checked again for this decision. This is a decision memo, not a novelty declaration or a completed systematic review.

## Decision in brief

QuakeNode does not yet have a demonstrated research contribution: the repository has no implementation, selected dataset, or results. The broad “unified causal EEW testbed” is not novel on the evidence available. The closest prior work already covers target-site warning utility (Meier, 2017), EEW network congestion/failure simulation (QCN, 2014), complex operational scenario tests (ShakeAlert sequences, published 2023), and causal/streaming detector work (FisH, 2024 preprint). The strongest path is to ask a narrower empirical question about **whether controlled data-delivery faults change measured outcomes for existing EEW pipelines under paired causal replay**, with a predeclared dataset, fault model, and primary metric. This remains conditional on verifying that no existing repository already provides that exact combination.

### Contribution statement (2–3 precise sentences)

For a fixed, documented set of multi-station earthquake/noise records, QuakeNode could compare one or more existing EEW pipelines in a causal replay under matched no-fault, delay, packet-loss, and station-outage conditions, recording event-level detection latency and misses, plus target-site warning utility only where the data support it. The contribution would be the controlled, reproducible empirical comparison and its timing/fault protocol—not the first real-time EEW evaluation, a novel detector, or novelty by feature aggregation. If the faulted and idealized conditions do not materially change the predeclared outcomes, that is a valid negative result and falsifies the motivating hypothesis for the tested pipeline/data/scenarios.

## Evidence that constrains the decision

- **Meier (2017)** uses offline waveforms in pseudo-real-time, updates predictions every 0.5 s, and measures target-threshold correctness, warning times, false alerts, and missed alerts. The methods assume correct detection/association and explicitly neglect data transmission and processing delay. That is the closest prior work to the project’s “real-time utility versus offline score” premise. [Paper](https://doi.org/10.1002/2017JB014025).
- **Quake-Catcher Network (2014)** simulates network congestion/failure in a volunteer-sensor EEW network and evaluates detection delay and lost messages. This defeats any claim that network failure simulation in EEW is new. The publisher-level details accessible in the audit do not establish a modern, reusable waveform-to-target-warning benchmark; full text and artifact status need a closer check. [Paper](https://doi.org/10.1016/j.procs.2014.05.041).
- **ShakeAlert synthesized-sequence testing (2023 publication)** tests production algorithms on sequences assembled from real records and evaluates source/ground-motion performance and alert timeliness. Its scenario stress testing is relevant precedent, although the audited source did not establish general packet-level delivery faults or a public general-purpose test harness. [Paper](https://doi.org/10.1785/0220220088) · [USGS record](https://www.usgs.gov/publications/testing-shakealert-earthquake-early-warning-system-using-synthesized-earthquake).
- **FisH (2024 preprint)** evaluates per-time-step single-station predictions with historical context and no post-arrival information for online picking; seconds after P are information-accrual time, not end-to-end network/alert latency. A public implementation was not verified. [Preprint](https://doi.org/10.48550/arXiv.2408.06629).
- **The 2026 event/noise classifier** evaluates short windows with 2–3 seconds of P-wave context, compares classifiers and STA/LTA, and decomposes computational preprocessing and inference latency. It does not establish transport or arrival-time fault evaluation; code is available from authors on request. [Paper](https://doi.org/10.1007/s12145-026-02099-6).
- **ObsPy and SeisBench** already provide significant waveform/stream and detector/model infrastructure. QuakeNode should show a specific experimental benefit to justify a new layer rather than reimplement I/O or a model catalog. [ObsPy](https://docs.obspy.org/master/packages/obspy.core.html) · [SeisBench](https://github.com/seisbench/seisbench).
- The reconnaissance documents no application, test harness, dataset, station/event metadata, or supported runtime in this workspace. The context says a synthetic fixture is acceptable for software invariants but cannot establish seismological performance. Real target-site warning utility also requires suitable ground-motion observations and common timeline semantics.

## Candidate A — Unified reproducible testbed

### 1. Precise novelty claim to test

A public, runnable framework couples causal sample availability, controllable data-delivery faults, multi-station event/alert processing, and target-site warning-utility metrics under one versioned experiment configuration. The claim cannot be “first real-time EEW testbed”; it would be “a specific integration enables a controlled comparison that existing components/papers did not make straightforward.”

### 2–4. Closest prior work, what it does, and residual gap

Closest works are Meier (2017), QCN (2014), ShakeAlert sequence evaluation (2023), FisH (2024), and toolkits ObsPy/SeisBench. Meier already supplies pseudo-real-time target utility but assumes detection/association and removes transmission/processing delays. QCN already simulates network faults and measures detection/message effects but focuses on network topology in a volunteer sensor system. ShakeAlert tests operational algorithms against difficult synthetic event scenarios and alert timeliness. FisH supplies a model-level streaming evaluation. ObsPy and SeisBench provide data/model plumbing.

The residual gap is not established by stacking these citations. The audit has not demonstrated a single publicly reusable tool covering all four layers, but the audit is targeted rather than exhaustive and QCN details are incomplete. The gap could collapse after deeper repository/supplement searches. Even if the software combination is new, feature integration alone is not scientific novelty: it matters only if the resulting controlled experiment changes or clarifies conclusions about latency, failure sensitivity, method rankings, or target warning utility.

### 5. Evidence needed

A public source release with an auditable time model and minimal adapter interface; one documented waveform/event/station selection; explicit detector/fusion/alert semantics; seeded faults and a no-fault control; manifests and event-level outputs; tests for no-future access and timestamp invariants. An experiment must compare the same cases and pipeline with/without stream constraints and faults, and show how the integrated protocol changes the outcome or enables a finding not visible in component-level tests. A synthetic-only demonstration establishes software behavior, not EEW efficacy.

### 6–8. Difficulty, prerequisites, likely objection

- **Implementation: high.** It spans replay, adapters, transport semantics, fusion, alert lifecycle, reporting, and interfaces; the repository is currently empty.
- **Evaluation: high.** Needs credible input data, station/event labels, fair detector adaptations, a valid fault model, and possibly target-site shaking records.
- **Prerequisites:** versioned waveforms; sample rates/units/station IDs; event catalog and station geometry; license review; explicit packet/sample semantics; event matching; target-site ground-motion data if warning utility is claimed; reproducible fault seeds.
- **Strongest reviewer objection:** “This is a software integration project whose parts already exist; where is the methodological or empirical advance, and why do the chosen synthetic/network faults represent anything operational?”

### 9–10. Falsification and contribution type

The integration’s scientific premise is weakened if a paired comparison shows that causal/fault conditions do not change any meaningful, predeclared metric or method ranking within uncertainty, or if results depend on arbitrary fault choices and evaluation assumptions. This would not falsify the software artifact’s existence, but it would falsify the proposed scientific motivation for the broad framework. Type: **systems + benchmark**, with a seismology component only if real waveform and target utility data support claims.

## Candidate B — Benchmark how network faults change existing EEW pipelines

### 1. Precise novelty claim to test

For specified existing pipelines and a fixed event/station set, measure how controlled delay, loss, and station outages change detection/event latency, missed detections, false triggers, and (where supportable) target-site warning-time outcomes relative to paired no-fault controls. The possible contribution is the experimental result and protocol; “fault injection exists” is not novel.

### 2–4. Closest prior work, what it does, and residual gap

QCN (2014) is the nearest direct overlap: it emulates network congestion/failure and reports detection-delay and message-loss changes. Meier (2017) evaluates end-user utility but explicitly neglects transmission and processing delays. OpenEEW documents live MQTT sensors and a stale-station status example but not a controlled benchmark. ShakeAlert sequence work evaluates event-complexity scenarios, not necessarily communication faults.

A remaining, provisional gap is a paired fault-sensitivity benchmark that preserves waveform identity while changing only the delivery process, runs existing EEW logic, and reports event-level outcomes with explicit fault and metric denominators. QCN’s age/system scope and lack of a verified target-warning/fault-matrix artifact suggest a distinct empirical study may be possible, but full text/artifact access and broader prior art must be checked. It is not defensible yet to claim no such study exists.

### 5. Evidence needed

Pre-register a small scenario grid and primary endpoint. Run the same events, station set, detector parameters, and event matching in the ideal condition and each fault condition. Save every dropped/delayed packet/sample, seed, configuration, code version, event-level result, and exclusions. Include at least a transparent baseline detector and a second existing pipeline only if it can be adapted fairly. Report uncertainty across events and stochastic seeds; use target-site warning metrics only with a defensible observed/modelled threshold and shared time base.

### 6–8. Difficulty, prerequisites, likely objection

- **Implementation: medium–high.** A single-process replay and three faults are tractable; realistic multi-station scheduling/fusion and detector adapters add complexity.
- **Evaluation: medium–high.** A public dataset may support detection/picking but not target-site shaking; the latter can make the study high difficulty or block it.
- **Prerequisites:** licensed records with continuous event and noise windows; station/event metadata; station sample rate/time integrity; known unit/preprocessing; fixed detector versions/parameters; fault model/seed policy; no-fault baseline; metric denominators. For warning utility: target-site observations or defensible ground-motion predictions and an alert-delivery model.
- **Strongest reviewer objection:** “Your network faults are arbitrary simulator knobs, not calibrated communication behavior, and the only novelty beyond QCN is a modern rewrite. Why should the measured effects generalize?” Address this with transparent scenario levels, measured traces if available, and deliberately narrow claims.

### 9–10. Falsification and contribution type

The main hypothesis (“delivery faults materially change outcomes”) is falsified for the tested systems and scenarios if predeclared differences in primary metrics are practically negligible with uncertainty excluding a meaningful effect, or if performance/rankings remain robust across plausible fault levels. A null result still constrains the tested conditions, but is not a positive fault-sensitivity claim. Type: **benchmark + systems**, with **seismology** only when waveform/ground-motion interpretations are supported.

## Candidate C — Causal streaming adapter/protocol for offline detectors

### 1. Precise novelty claim to test

A protocol and adapter layer can replay identical waveform records incrementally and compare existing offline detector outputs with causally available outputs, exposing whether full-record/window evaluation changes trigger timing, detection rate, false triggers, or method ranking. It is not a new picker library or the first streaming detector.

### 2–4. Closest prior work, what it does, and residual gap

FisH (2024) directly evaluates online per-step outputs, so causality at the model level is established prior art. The 2026 classifier paper uses short post-onset windows and measures compute latency. SeisBench supplies reusable pretrained detector/picker APIs and benchmarks; ObsPy supplies incremental SeedLink callbacks and waveform structures.

A plausible gap is a *comparative* protocol that applies selected existing methods to exactly the same as-of prefixes/arrival schedule, records model-specific input windows and output timing, and directly contrasts offline and causal results. The audit does not establish that no such benchmark exists. The scientific value depends on showing material leakage or ranking/timing differences, not merely wrapping APIs.

### 5. Evidence needed

Select at least two detectors with distinct input assumptions and public weights/code. Establish a clean event-level holdout; specify causal prefix/window rules, preprocessing, normalization, warm-up, trigger/re-arm semantics, and gap behavior; compare full-window/offline and as-of/causal evaluation without retuning on test events. Save traces of data visible at every decision, output timestamps, parameter manifests, and results. A synthetic future-spike fixture should first prove the adapter’s causality invariant.

### 6–8. Difficulty, prerequisites, likely objection

- **Implementation: medium.** A narrow adapter is manageable, but many offline models are not inherently streamable; bidirectional context, whole-window normalization, padding, state reset, and chunk boundaries can alter outputs.
- **Evaluation: medium.** Easier than target utility, but fair model adaptation and event-level split discipline remain substantial.
- **Prerequisites:** licensed waveform/noise records; onset labels and event-level split IDs; sample rate/units/preprocessing metadata; detector code/weights/license; explicit causal input rules; compute environment and timing measurement rules.
- **Strongest reviewer objection:** “You changed the detector while streaming it, so this is an unfair comparison; alternatively, the causal result is just the expected consequence of giving a model less context.” A strong design separates information-limited performance from compute latency and reports both, preserves model defaults where possible, and validates adapters against original offline behavior.

### 9–10. Falsification and contribution type

The hypothesis that offline evaluation misstates causal performance is weakened/falsified for the selected models/data if causal replay yields materially equivalent detection/false-trigger rates and timing, with stable rankings and no future-context leakage in the offline protocol. Conversely, a rank change is only meaningful if splits, thresholds, and input data are fair. Type: **ML evaluation + benchmark + systems**; seismology contribution depends on what the selected records can support.

## Candidate D — Nepal-focused scenario study

### 1. Precise novelty claim to test

Using a documented Nepal-relevant event/station set, quantify how observed station geometry/availability and specified delivery conditions affect EEW detection or warning-time outcomes at named target sites. This is a regional empirical study, not a claim that a generic platform is novel or that an operational warning system is suitable for Nepal.

### 2–4. Closest prior work, what it does, and residual gap

The context lists NSET, SEG, and Duke/Tribhuvan Kathmandu project material as regional context, but the audit/reconnaissance did not establish a licensed, analysis-ready Nepal waveform + station metadata + event catalog + target-site ground-motion dataset. The general closest method precedents are Meier’s target-site utility analysis, Swiss loss-based warning-time analysis, and QCN/ShakeAlert scenario work. Whether an existing Nepal-specific EEW feasibility or performance study already answers the precise question was not resolved in the prior-art audit.

Any gap remains unverified until a focused Nepal literature/data review. Geographic focus alone is not novelty. A defensible regional contribution would need new data, a regional coverage/latency finding, or a transparent assessment of how local conditions alter a stated metric.

### 5. Evidence needed

A data inventory and license ledger first; then a coverage map, station metadata quality assessment, event/station completeness analysis, selected geographic/time window, and comparison with relevant Nepal studies. Only afterward define replay/fault cases and target-site rules. If suitable target-site ground motion is unavailable, report detection/latency or scenario-based coverage and do not call it observed warning time.

### 6–8. Difficulty, prerequisites, likely objection

- **Implementation: medium** after data acquisition; **high** if adapters/quality control must be built for heterogeneous archives.
- **Evaluation: high** because metadata, station history, event coverage, and target shaking data may be incomplete or access-controlled.
- **Prerequisites:** licensed Nepal waveform data; stable station IDs, coordinates, channels, rates, response/units; event catalog and onset references; station operational/availability history; network telemetry measurements for realistic faults; target-site records/models; informed local interpretation.
- **Strongest reviewer objection:** “This is a small, possibly sparse or biased dataset dressed as regional relevance; there is no evidence that the selected stations or events represent Nepal’s EEW problem.”

### 9–10. Falsification and contribution type

The regional hypothesis fails if available data do not support the proposed station/event/target coverage, or if documented local conditions do not produce the claimed changes in outcomes. An infeasible data audit is itself a reason to pause, not a reason to synthesize unsupported metadata. Type: **seismology + benchmark/systems**, contingent on data.

## Candidate E — Clock-domain and latency-accounting conformance protocol

### 1. Precise novelty claim to test

Define and test a common timing contract separating recorded sample time, data availability/arrival time, processing/emission time, event/alert decision time, and delivery/target threshold time; provide conformance fixtures that distinguish information-accrual time from compute/network/alert latency. This is a narrow protocol artifact, not a claim that timestamping itself is novel.

### 2–4. Closest prior work, what it does, and residual gap

The QuakeNode context itself already identifies these clock domains. Meier reports pseudo-real-time predictions but neglects transmission/processing. FisH reports seconds after P as information accrues. The 2026 classifier paper times preprocessing/inference, not network delivery. The Swiss framework incorporates reported data latency into scenario warning-time estimates. Together these sources demonstrate the need to distinguish timing components, while also showing that pieces are already measured.

The remaining gap is a reusable conformance vocabulary/artifact that makes incompatible “latency” definitions visible and allows two evaluations to be compared. The audit does not prove that no standards or operational timing contracts exist; those should be searched before claiming a field-wide standardization gap.

### 5. Evidence needed

A short specification with typed clock domains, transformations, allowed comparisons, uncertainty/timestamp-quality fields, and tests using synthetic traces with known delay, clock offset, gaps, and reorder. Apply it to at least two published/available detector adapters and report an explicit latency decomposition. Demonstrate that naive single “real-time latency” numbers can reverse or obscure a comparison. Without such an empirical demonstration, this remains useful engineering documentation rather than a research result.

### 6–8. Difficulty, prerequisites, likely objection

- **Implementation: low–medium.** Schemas and synthetic conformance cases are tractable; real-world clock uncertainty and transport measurements are harder.
- **Evaluation: medium.** Needs either two distinct pipelines or measured latency sources to show the protocol changes interpretation.
- **Prerequisites:** explicit clock mapping; sample-rate/time metadata; simulated or observed arrival times; processing measurements; common time-base rules; uncertainty and synchronization quality where available.
- **Strongest reviewer objection:** “This is careful bookkeeping, not a scientific contribution, and the literature already uses distinct waveform and wall-clock timing even if papers do not share vocabulary.”

### 9–10. Falsification and contribution type

If the contract does not expose any material ambiguity or alter latency conclusions in compared methods, its research significance is low (though it could remain a software-quality artifact). Type: **systems/methods**, with a limited benchmark contribution only if used comparatively.

## Scoring

Scores are 1–5. For “low duplication risk,” **5 means little apparent duplication risk; 1 means high risk**. These are decision aids, not measured quantities. “Evidence of gap” is intentionally conservative because the prior-art audit is targeted, QCN full text/artifacts were not fully inspected, and the repository has no data or implementation.

| Direction | Evidence of a real gap | Scientific significance | Small-team feasibility | Fair evaluation | Reproducibility / open-source value | Low duplication risk | Main reason for the scores |
|---|---:|---:|---:|---:|---:|---:|---|
| A. Unified testbed | 2 | 4 | 1 | 2 | 4 | 1 | Potentially useful integration, but very broad; direct predecessors cover most components; feasibility and fair end-to-end validation are poor before data/protocol selection. |
| B. Fault-impact benchmark | 3 | 4 | 3 | 4 | 4 | 2 | Clear empirical question and paired controls are possible; QCN is direct prior art and the fault model/data realism are major risks. |
| C. Causal detector comparison | 3 | 3 | 4 | 4 | 5 | 3 | Existing streaming model work prevents a broad claim, but a carefully controlled cross-model adapter benchmark is tractable and reproducible. |
| D. Nepal scenario study | 2 | 3 | 1 | 2 | 2 | 2 | Regional significance could be high, but data/metadata availability and representativeness are unverified; location alone does not create novelty. |
| E. Timing conformance protocol | 3 | 2 | 5 | 4 | 5 | 3 | Narrow and feasible; gap is plausible from incompatible latency definitions, but standardization/bookkeeping alone may not rise to a research contribution. |

### Why each score is not higher

- **A:** The audit cannot support a gap across all layers, and integrating them without demonstrating a changed scientific conclusion risks a software-only contribution. High implementation burden increases scope failure.
- **B:** A clearly testable question improves fairness, but QCN already simulates congestion/failure. Novelty must be the tested pipeline/metrics/protocol or a substantive empirical result. Lack of transport measurements threatens external validity.
- **C:** Causal evaluation is relevant and easy to reproduce with public waveform/model assets, but FisH already does online stepwise evaluation and 2026 work already measures short-window accuracy/compute latency. A protocol-only paper may be incremental.
- **D:** The prior-art audit did not find enough Nepal-specific data evidence to establish either feasibility or a regional gap. Do not raise the score based on motivation alone.
- **E:** A small team can implement it quickly and conformance tests would support all later work, but a useful timing schema does not automatically constitute publishable research.

## Recommendation

### Primary direction: B, narrowed to one paired fault-sensitivity experiment

Start with one existing, transparent detector/fusion path and a small, licensed, multi-station data selection. Treat fixed delay first as a timing-accounting check; a predictable latency shift by itself is not an interesting result. Make packet loss and station outage (or a predeclared interaction) the primary perturbations, and measure event-level misses/association changes and warning utility only where the records support a defensible common timeline. Compare fault-free and faulted runs on the same events and detector parameters. This choice is strongest because it can produce an empirical result that is not merely a software feature list, while retaining a clear falsification condition.

Before implementation expands, do one targeted prior-art check for public EEW network simulators and compare QCN’s full methods/code. If an existing framework already supports the same controlled waveform-to-outcome comparison, stop claiming a benchmark gap and adapt/reproduce it instead of duplicating it.

### Fallback direction: C, a small causal evaluation protocol for existing detectors

Use if realistic network fault distributions or target-site data cannot be justified. This direction can still test whether offline model evaluation overstates performance under as-of inputs and can be limited to a few publicly available models/datasets. Its result must distinguish reduced input information from compute/transport latency, and must not claim first streaming detection.

### Tempting direction to avoid for now: A, the full unified platform

Do not start by implementing every proposed subsystem or building a general framework. The repository is empty; this expands the verification surface before the research question, dataset, or timing model has been secured. A “platform” can consume the entire effort while yielding no defensible empirical result. Build only components needed to test the primary question.

D should remain conditional, not the default fallback. Revisit it after an explicit data/metadata/license inventory establishes that Nepal-relevant records can support a fair evaluation.

## What we must NOT claim

- QuakeNode is the first real-time EEW testbed, first causal EEW evaluation, or first system to study EEW network failures.
- Prior work only evaluates offline accuracy. Meier (2017), FisH (2024), ShakeAlert scenario studies, and the 2026 latency-aware classification paper directly contradict that broad statement.
- Adding causal replay, fault injection, fusion, and utility metrics is novel merely because they are combined in one repository.
- Simulated packet delay/loss/outage is “realistic” without measured or otherwise justified distributions and clear assumptions.
- Synthetic fixtures demonstrate seismological detection performance or Nepal suitability.
- A model’s milliseconds of inference, seconds after P, detector latency, alert latency, and end-user warning time are interchangeable metrics.
- A target-site warning-time claim is supported without observed/modelled shaking thresholds, an explicit event match, a delivery time, and a common clock.
- A regional Nepal result is representative without documented station/event coverage and metadata.
- A null result is a failure. It can refute the hypothesis for the declared pipeline, data, and fault envelope; report that scope honestly.

## Decision gates before committing to a paper claim

1. **Data gate:** select the dataset and verify its license, waveform units/rates, timestamps, station geometry, event/noise labels, and relevant splits. If target utility is required, verify target-site shaking data and timing.
2. **Prior-art gate:** inspect QCN full methods and search for subsequent network-failure EEW simulators/benchmarks and public artifacts; inspect supplements/source for any candidate methods used.
3. **Protocol gate:** write the clock model, packet/sample semantics, event matching, fault parameters, denominators, primary outcome, and falsification threshold before examining experiment results.
4. **Feasibility gate:** demonstrate one synthetic causal replay invariant and one detector adapter on a small fixture. Do not treat this as a performance result.
5. **Contribution gate:** proceed only if the chosen experiment distinguishes its contribution from the named nearest work and can be run with the available data/team. Otherwise narrow to a methods/software artifact or pause.

## Open questions that could change this decision

- Does the full QCN paper or an associated artifact already implement a causal waveform stream and event-level utility metrics beyond the abstract-level evidence checked here?
- Is there an open simulator or benchmark not covered by the targeted audit that already performs paired network-fault comparisons on EEW detector outputs?
- Which dataset supplies station-aligned continuous waveform/noise records plus event and target-site metadata under usable terms?
- Are fault distributions based on measured telemetry, or will the study explicitly be a sensitivity analysis over hypothetical parameter ranges?
- Can existing offline detectors be adapted without changing their semantics, and does a fair causal baseline exist for each?
- What is the practical effect threshold that would count as a meaningful change, and how will uncertainty be estimated with a potentially small number of events?
