# Adversarial pre-mortem: QuakeNode Phase 1 experiment

**Review date:** 2026-10-26  
**Reviewer stance:** independent, skeptical review of the proposed first experiment before implementation.  
**Verdict: NO-GO — revise the data plan and primary claim before coding the main pipeline.**

## Verdict and reason

The current protocol cannot support its central causal interpretation with the selected INSTANCE sample. The published digital-count traces are detrended over the complete 120 s window before distribution; this transformation uses samples that would not yet have arrived during an early replay decision. The event records are also selected from stations with reviewed P arrivals that contributed to preferred catalog locations, so a trace-level “miss fraction” is conditional on a station/event record already having a catalog P pick. That is not network or event detection recall.

The proposed 1 s Bernoulli drops and onset-aligned blackout are explicitly exploratory, not based on observed telemetry. They can support a narrow sensitivity analysis after the causality problem is fixed, but they do not establish how real packet loss affects EEW. Finally, the prior-art gap is not defensible as written: QCN directly simulates EEW network congestion/failure; CREW already operates as a real-time EEW testing/comparison facility; PRESTo/SeisComP studies already compare continuously streamed real-time simulation and target warning metrics; and the 2026 EPIC Alaska paper packages a multi-station replay test suite with event matching and misses. These works do not all inject the same packet-loss model, but they substantially narrow the possible contribution.

Do not implement the main experiment as a causal EEW benchmark on the current INSTANCE processed sample. First revise the data source/preprocessing and the claim, then re-review the amended protocol. Synthetic causal tests can be built separately as software checks, but they cannot replace real detector evidence.

## What was reviewed

Read all files in docs/phase1, including the prior-art audit and matrix, research-gap decision, dataset feasibility report, evaluation protocol, architecture decision, and ADR, as well as context.md and experiments/configs/phase1_protocol.yaml. Relevant protocol locations include:

- Causal/no-future requirements: context.md sections 6, 8, 11 and 26.
- INSTANCE selection/preprocessing caveats: dataset_feasibility.md, especially “Required fields,” “Proposed event/station selection criteria,” and “Metrics.”
- Primary RDT, data selection, detector, fault and clock rules: evaluation_protocol.md sections 4–12.
- Proposed causal API: architecture_decision.md sections 4–9.
- Existing close prior art and limits: prior_art_audit.md and research_gap_decision.md.

The repository still has no implemented application code, test harness, data file, or dependency stack. This is a protocol review, not a review of observed experiment output.

## Findings by severity

“Confirmed” means established by the reviewed protocol, project files, or cited source. “Plausible/unverified” means the review found a serious risk but the actual data/run has not been inspected.

| ID | Severity / status | Issue and evidence | Impact | Required mitigation |
|---|---|---|---|---|
| 1 | **Critical — confirmed design defect** | INSTANCE paper says digital-count preparation removes mean and linear trends from each 120 s trace and resamples it to 100 Hz before HDF5 release. The replay protocol then treats these prepared traces as causal inputs and prohibits only additional preprocessing. Whole-window detrending makes early output depend on future samples. The source methods are explicit: [INSTANCE paper, §2.1.5](https://essd.copernicus.org/articles/13/5509/2021/#section2). | Detector API isolation alone does not establish causality. A cutoff/prefix test on the already-detrended trace can pass while the upstream data transformation has leaked future context. The central “causal replay” claim would be false. | Use raw archived samples and perform only specified causal preprocessing online; or explicitly relabel the study as fault sensitivity on globally preprocessed clips, remove causal-performance claims, and define that narrower estimand. Recheck resampling/filter implementation and its temporal support. |
| 2 | **High — confirmed selection limitation** | INSTANCE selects stations with P-wave onset picks used in the preferred event location, requires low phase residuals and meaningful location weights. Its paper describes manual review and these station-selection rules. [INSTANCE paper, §2.1.2](https://essd.copernicus.org/articles/13/5509/2021/#section2). | The denominator excludes operating station/event cases with no accepted P pick. The protocol’s miss fraction is recall conditional on curated, analyst-picked station traces; it cannot estimate station-level or system-level event recall. Fault-induced misses can be measured only among those selected traces. | Name the metric “miss fraction among eligible catalog-picked HNZ traces.” If recall is a central claim, use a source that includes all available station streams or define the target population and ascertainment process independently of picks. |
| 3 | **High — confirmed prior-art overlap; residual gap unproven** | QCN’s 2014 paper explicitly emulates network congestion and failure in an EEW network and measures detection delay and lost messages. [QCN 2014 paper](https://doi.org/10.1016/j.procs.2014.05.041). CREW is an EEW testing center that runs methods on live SeedLink network feeds, compares software, and publishes performance including lead time and ground-motion estimates. [EPOS CREW](https://www.epos-eu.org/tcs/near-fault-observatories/services/crew). PRESTo/VS(SC) work evaluates continuous-streaming real-time simulation, effective processing time and warning-time ground-motion predictions. [Zuccolo et al. 2021](https://doi.org/10.3389/feart.2021.686272). A 2026 EPIC study supplies a 530-event multi-station Alaska replay test suite, progressive real-time replay, trigger association, event matching and misses; it states that telemetry latency/warning-time analysis was omitted. [EPIC Alaska 2026](https://doi.org/10.1785/0120260139), dataset DOI cited by paper: [10.5281/zenodo.19897535](https://doi.org/10.5281/zenodo.19897535). | “Fault injection in EEW is new,” “causal replay is new,” “real-time EEW benchmarking is new,” and “no public replay suite exists” are untenable. A single STA/LTA experiment may be an incremental sensitivity note, not a novel general benchmark. QCN’s exact detailed fault implementation remains incompletely inspected in the earlier audit; that is a gap in the audit, not evidence of novelty. | State a claim no broader than the exact experimental delta. Inspect QCN full text/artifacts and the EPIC test-suite repository/data, including terms. Expand prior-art search to CREW and relevant operational test platforms before selecting a paper claim. If the question is already answered at the needed level, reproduce or pause. |
| 4 | **High — confirmed construct mismatch** | The protocol uses one HNZ channel, a per-trace STA/LTA trigger, a station P pick, and no event association, fusion, alert issuance or delivery. It explicitly defers these systems. | This is a sensor-channel P-trigger sensitivity experiment, not an evaluation of an EEW pipeline’s event detection, event fusion, or end-user warning behavior. “Event detection,” “station outage,” and “fault impact on EEW” would overstate the construct unless carefully qualified. | Call outcomes “per-trace trigger,” “catalog-picked trace miss,” and “channel-stream outage.” Do not call the blackout a station outage when only HNZ samples are removed. Treat end-to-end EEW as out of scope. |
| 5 | **High — plausible/unverified data feasibility blocker** | INSTANCE sample page documents 10,000 events/1,000 noise waveforms and CC BY 4.0, but Phase 1 has not downloaded or inspected it. HNZ channel coverage, the sample’s exact HDF5 contents, metadata field mapping, consistent HNZ event/noise representation, P timing joins, duplicates and usable counts remain unresolved in dataset_feasibility.md and the YAML. | The protocol’s inclusion rules may yield no or very few HNZ traces. If noise windows are not comparable or P picks are unavailable, primary/secondary metrics cannot be calculated as specified. | Complete the metadata-only feasibility audit, verify exact sample/version/checksum/license and a small waveform read before implementing the full adapter. Freeze a count/exclusion report. If channel or fields fail, amend/re-review; do not substitute channels after seeing outputs. |
| 6 | **High — confirmed arbitrary model, valid only as sensitivity analysis** | F1’s 1%, 5%, 10% loss, one-second packets, F2’s onset-aligned three-packet blackout and F3’s 250 ms fixed delay are explicitly marked exploratory and have no telemetry basis. They do not represent an observed distribution. | Findings can show the detector’s response to those selected artificial cases only. They cannot support “realistic network fault” or expected deployed-system effect claims. The onset outage also uses the P-pick to place the failure at the most informative moment. | Either obtain an empirical arrival/loss/outage trace and derive scenarios from it, or title/report the result as a synthetic fault-parameter sensitivity analysis. Keep F2 as a deliberately adversarial stress case, not a typical outage. |
| 7 | **High — confirmed confounding by gap semantics** | Every missing packet resets STA/LTA state and disables triggers until a fresh 10 s LTA warm-up. Random packet loss therefore creates an algorithmic blind interval much longer than the missing packet. The protocol fixes one reset policy and has no alternative-policy sensitivity. | A large measured effect may be mostly “reset and rewarm for 10 s,” not the effect of a one-second packet loss itself. Different plausible implementations (buffer, preserve state, reinitialize with shorter warm-up) could reverse the outcome. | Define this as the treatment mechanism and report it prominently. Before a broad claim, add a prespecified gap-policy sensitivity comparison or justify reset/warm-up from the actual detector implementation being evaluated. Keep the primary detector semantics otherwise identical across conditions. |
| 8 | **High — confirmed timing/chunk-size dependence** | All conditions use one-second packets, and a detector emits only when an arriving packet is processed. C0 is correctly packetized, but its emissions are quantized to packet arrivals. Faults and F3 are defined relative to the same packetization. | Results are conditional on one-second batching. Changing to 100 ms packets could change latency, loss granularity, number of drop opportunities and effects. RDT is not an intrinsic sample-level detector latency. | State that the estimand is specific to 1 s batches. Before generalizing, run a predeclared packet-size sensitivity (for example 100 ms and 1 s) while preserving equal delivered samples and fault exposure in seconds. Do not tune chunk size based on observed result. |
| 9 | **Medium — confirmed metric boundary** | RDT is emission time minus a station P-pick, capped at 10 s, with misses assigned 10 s. It is a coherent bounded trigger-timing/miss composite. Noise false-trigger exposure is summed over selected 120 s snippets; the INSTANCE paper says noise windows are selected from catalog-event-free periods and can still contain regional/teleseismic event energy. [INSTANCE paper, §3](https://essd.copernicus.org/articles/13/5509/2021/#section3). | RDT is not a target warning-time metric. Noise rate is false triggers per sampled trace-hour, not false alerts per continuous operational hour; some “noise” triggers may be real uncatalogued/regional events. The 10 s miss penalty and P reference dominate interpretation. | Keep warning utility out of scope. Label the noise rate exactly as a selected-window trigger rate; report raw count/exposure and metadata-screened sensitivity. Report RDT components (miss fraction and conditional latency) alongside the composite. |
| 10 | **Medium — plausible statistical uncertainty risk** | Primary CI bootstraps event IDs after averaging 20 random masks per trace. The protocol reports mask spread separately but does not incorporate Monte Carlo mask uncertainty in the event bootstrap interval. Event count is unknown. | CI may understate uncertainty if only 20 masks poorly estimate each trace’s expected fault response; event clustering helps dependence but does not account for all seed noise. | Use a nested event/replicate bootstrap or increase mask replicates by a predeclared convergence rule. Report between-event and within-mask variance separately. No power claim is currently made, which is appropriate. |
| 11 | **Medium — confirmed baseline limitation** | The baseline is a single fixed STA/LTA detector with thresholds 3.5/1.5 and 0.5 s/10 s windows; parameters are frozen without a development calibration. There is no comparator detector. | A result may be peculiar to this arbitrary setting and channel. The test cannot establish that “EEW pipelines” in general are sensitive or robust. If the detector has near-zero or near-perfect detections, RDT can saturate. | Keep STA/LTA as a transparent software baseline but report trigger distribution and saturation. A second detector is not automatically required; if the scientific claim generalizes beyond this detector, add a preregistered second existing pipeline and preserve its own input semantics. Do not tune on the test sample. |
| 12 | **Medium — confirmed limitation** | Equal-event weighting across trace effects is reasonable for an event-weighted estimand, but each event’s station set is determined by data availability and catalog-pick selection; station geometry is not modeled as a factor. | The estimate describes the sample’s picked station-trace population, not a fixed network or target-site geometry. Dense events may contribute more station conditions within an event mean, and station outages cannot be interpreted at network level. | Report event and trace counts, station/site distribution, distance/SNR/channel strata, and per-event station counts. Keep station-level outage/network coverage claims out. |
| 13 | **Medium — plausible novelty/contribution risk** | No second pipeline, event fusion, warning utility, or measured transport trace is included. The implementation is mostly an adapter, packet scheduler, STA/LTA and metrics around components already available in seismic toolkits. | A paper may be judged as software integration without an insight beyond an expected monotonic loss effect. | Predefine a result that would alter an engineering decision (e.g., a fault envelope changes a pipeline’s miss/latency tradeoff) and use a real/justified fault envelope. If no nontrivial result is expected beyond “dropping data can hurt a trigger,” treat this as a technical implementation exercise, not a research contribution. |
| 14 | **Low — confirmed strength** | The protocol pairs each event/station trace across C0 and faults, freezes detector parameters, fixes the eligible set and metrics, records seeds, and includes a no-fault control. | This is a sound comparison structure once the input and causal preprocessing problems are fixed. | Preserve this pairing, report masks and denominators, and do not change settings after outcomes. |

## Specific questions answered

### 1. Is the claimed gap already addressed?

**Partly, and enough to defeat the broad claim.** QCN directly studies EEW network congestion/failure and detection delay/lost messages. CREW already provides a real-time testing/evaluation facility for comparing EEW software on network data and reporting lead-time/ground-motion metrics. Zuccolo et al. compare two EEW algorithms in continuous-streaming simulation with effective processing time and warning-time utility. The 2026 EPIC Alaska paper contributes a reusable 530-event replay test suite and uses progressive replay, station triggering/association, catalog matching, misses and false-event records. Real SCSN/ShakeAlert telemetry has also been analyzed during Ridgecrest, including latency severe enough that some station data arrived too late for an algorithm: [Stubailo et al. 2021](https://doi.org/10.1785/0220200211).

None of those sources, from what I could verify, establishes the exact same modern “5% independent 1 s drops on HNZ STA/LTA clips” result. That exactness is not a meaningful novelty claim by itself. The unresolved potential contribution would need to be an empirically justified, paired fault-sensitivity result with a clear difference from QCN and existing real-time replay/test platforms. QCN full methods and the EPIC data repository/license still need artifact-level inspection. The audit is not exhaustive.

### 2. Does INSTANCE support every metric?

**It supports only a narrow subset, conditional on the sample actually containing usable HNZ rows.** The dataset has trace-level P arrivals, HNZ strong-motion records, 120 s/100 Hz windows, and labeled noise excerpts in the published full collection. Thus trace-level STA/LTA timing and selected-noise-window trigger rates are plausible.

It does not provide continuous noise exposure, natural packet timing/failure, a target alert-delivery time, or an unconditional station/event miss denominator. The catalog-driven selection intentionally requires manually reviewed P picks used in preferred locations. Its event traces are also globally detrended/resampled before release. Therefore it does not support the protocol’s claim to causal raw-stream behavior or operational recall as currently framed.

### 3. Could future samples leak?

**Yes; under the selected data representation, they already have.** The detector interface can prevent direct access to future array elements, but the full-trace detrend upstream invalidates a pure as-arrived claim. Resampling/filter temporal support is not specified in enough detail to assume it is causal either. Causality must cover the entire input transformation chain, not only the replay loop.

### 4. Are matching and false-trigger definitions defensible?

They are defensible **as restricted signal-trigger metrics** if named precisely. Matching a station trigger to that trace’s P pick within P to P+10 s is understandable. A miss penalty in RDT is explicit and avoids silently dropping missed records. The design should not call it event detection recall or user warning time. The noise denominator should be selected HNZ trace time and the result described as triggers per sampled noise trace-hour; it is not continuous false-alarm rate. Dataset authors warn that noise windows may contain regional/teleseismic energy.

### 5–6. Are faults plausible, and could other choices explain the effect?

The current fault parameters are arbitrary stress-test values by the protocol’s own admission. That is acceptable for sensitivity analysis, not an operationally representative fault study. The measured effect is strongly entangled with three selected mechanics: one-second packet batching, resetting STA/LTA for a full 10 s after any 1 s loss, and placing the F2 blackout near a known P pick. These choices can produce the result even when the fault itself is brief. The result must be described as conditional on these mechanics or include prespecified sensitivity comparisons.

### 7–8. Is the design paired and are baselines meaningful?

The paired comparison is one of the strongest parts: same trace, same parameters, same packetization, no-fault control, fixed eligibility, seeded masks. STA/LTA is a meaningful transparent baseline for a trigger-level study. But it is only one setting of one detector on one channel type, and the protocol does not compare a second pipeline or fusion method. It cannot support claims about EEW pipelines generally. Its parameters are frozen—which avoids test tuning—but may saturate; report that rather than tuning after seeing test results.

### 9–10. Is scope manageable, and is this only integration?

The proposed code scope is small enough. Scientific scope is also narrow, but perhaps too narrow for a standalone research contribution: a single detector, artificial packet probabilities, no measured network trace, no association, no target utility. The likely conclusion “a dropped packet can delay or suppress a trigger” is predictable. A technical report could still be useful if it exposes a counterintuitive interaction (for example, gap-reset policy dominates packet loss) and makes a carefully bounded reproducible result. That contribution is not yet established.

### 11–13. Likely reviewer objections

- **Seismology reviewer:** The dataset contains only analyst-picked, quality-screened P traces; your “misses” do not include stations/events without a pick. HNZ sampling/units and globally detrended clips are not a continuous observatory stream. No target-site ground motion or warning utility is measured.
- **Systems reviewer:** The 5% drop rate and 1 s packet model are invented; why should they represent telemetry? The 10 s LTA reset turns a one-second gap into a long algorithm outage. One channel is dropped, not an actual station/network path. Where is the measured arrival-time baseline?
- **ML/evaluation reviewer:** There is one fixed hand-selected baseline and no model comparison. Why this detector/threshold? Are inputs causally preprocessed? Are event-level splits and denominators meaningful? Does the bootstrap include random fault-mask variability?
- **All reviewers:** The closest prior work includes QCN fault simulation and modern causal/replay evaluation platforms; what finding could not have been produced by extending an existing test suite?

### 14. Most likely misleading result

The highest-risk failure is to observe a large increase in RDT/misses and attribute it to “network packet loss in real-time EEW.” In actuality, the estimate could be driven by full-window detrending, a one-second batch boundary, a single HNZ trace, a hand-selected P-picked cohort, and a forced ten-second detector reset after each gap. The number would be reproducible but would not measure the broad system property implied by the claim.

## Confirmed defects versus risks

### Confirmed defects or limits in the current study design

- The source INSTANCE digital traces have whole-window mean/linear-trend removal before replay; this contradicts strict causal input semantics.
- Event records are selected based on reviewed P picks used in preferred event locations; recall is conditional on selected picked traces.
- The protocol measures per-channel trigger latency and sampled-window false triggers, not event-fusion performance or warning utility.
- Fault levels are exploratory and not empirically grounded; they cannot be called realistic.
- A three-packet gap on HNZ is not a station outage in a multi-station system.
- The study has no second detector/fusion pipeline and cannot generalize to “EEW pipelines.”
- Prior art already covers much of the broad gap; novelty of the exact fault extension is not established.

### Plausible risks that require data or artifact inspection

- Whether the 1.7 GB sample contains enough HNZ event and HNZ noise traces with consistent digital counts, picks, time fields and 100 Hz sample mapping.
- Whether trace start and P-pick metadata can be joined without ambiguity in the sample version.
- Whether any additional resampling step used in release notebooks has noncausal filter support.
- Whether the 20 fault masks per trace adequately estimate Monte Carlo expectation; current CI does not include mask resampling.
- Whether the QCN full paper or artifact has a closer trigger-level fault methodology than the abstract reveals.
- Exact license/access/volume and runnable status of the EPIC Alaska test-suite repository cited by the 2026 paper.
- Whether a fixed STA/LTA threshold yields useful non-saturated triggers on the actual HNZ sample.

## Blockers to clear before main-pipeline implementation

1. **Resolve input causality.** Choose raw waveforms plus causal preprocessing, or explicitly abandon the causal-replay claim for this first experiment. Document each resampling/filter/detrending operation and its support.
2. **Resolve the target population.** Either narrow the estimand to trigger sensitivity conditional on catalog-picked HNZ traces, or identify data that include unpicked/failed stations so recall can be estimated meaningfully.
3. **Run a metadata-only data feasibility check.** Verify sample access, HNZ counts/noise coverage, joins, timestamps, checksums and license; produce cohort/exclusion counts before looking at detector outputs.
4. **Rename and narrow the claim.** This is not currently an end-to-end EEW network benchmark. Name the unit “HNZ channel-stream trigger” and say warning utility and fusion are not measured.
5. **Re-open prior art.** Inspect QCN methods/artifact, CREW capabilities, and the EPIC Alaska replay/test-suite data and license. Compare the proposed contribution against those specific systems.
6. **Justify the fault envelope or constrain inference.** Obtain telemetry-derived delay/loss/outage traces, or retain the values as exploratory hypothetical stress levels and avoid “realistic network” language.
7. **Predeclare chunk/gap sensitivity.** At minimum define how batching and reset/warm-up choices affect the estimand. Do not code a generalized fault engine until these semantics are settled.
8. **Fix uncertainty reporting.** Include stochastic-mask uncertainty in the primary interval or predeclare a convergence rule for replicate count.

Until blockers 1–5 are resolved, coding the main experiment risks making an invalid causal or novelty claim expensive to unwind. The synthetic causality fixture and a metadata-only adapter probe are safe preparatory work, but their results must not be presented as seismic performance.

## Sources checked for this review

Checked on 2026-10-26; source pages/paper passages were reviewed, not datasets downloaded.

- INSTANCE preparation, selection and noise caveats: Michelini et al. (2021), [ESSD paper](https://doi.org/10.5194/essd-13-5509-2021).
- QCN network fault simulation: [2014 paper](https://doi.org/10.1016/j.procs.2014.05.041).
- CREW testing center: [EPOS official service description](https://www.epos-eu.org/tcs/near-fault-observatories/services/crew).
- Continuous real-time algorithm comparison and target warning evaluation: Zuccolo, Cremen & Galasso (2021), [Frontiers paper](https://doi.org/10.3389/feart.2021.686272).
- Multi-station replay suite, event association and outcome evaluation: [EPIC Alaska study (2026)](https://doi.org/10.1785/0120260139); paper cites [Zenodo test-suite DOI 10.5281/zenodo.19897535](https://doi.org/10.5281/zenodo.19897535). The paper DOI page was reviewed; direct Zenodo record metadata/license were not independently retrieved in this check.
- Observed network/telemetry latency and ShakeAlert consequences: Stubailo et al. (2021), [SRL paper](https://doi.org/10.1785/0220200211).
- Target-site warning utility and its assumptions: Meier (2017), [JGR paper](https://doi.org/10.1002/2017JB014025).

