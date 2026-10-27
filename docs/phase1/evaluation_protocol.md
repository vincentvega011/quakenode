# QuakeNode Phase 1 evaluation protocol

**Status:** preregistration draft; no implementation, data request, or outcome analysis has occurred.  
**Version/date:** 0.1 / 2026-10-26  
**Basis:** context.md and Phase 1 repository reconnaissance, prior-art audit/matrix, research-gap decision, and dataset feasibility report.

## Study summary

Test whether simulated loss of one-second waveform packets changes causal detection performance of a fixed, single-station STA/LTA detector on eligible HNZ records in the official INSTANCE v3 sample. Replay each event-station trace under the same packetized no-fault control and predeclared fault conditions. The primary comparison is 5% independent packet loss versus no fault. Lower/higher loss, fixed delay and one onset-aligned outage are sensitivity checks. This measures sensitivity to a specified simulated fault model; it does not measure real communication reliability. Warning utility and multi-station fusion are out of scope.

## 1. Primary research question

For eligible HNZ event-station traces in the INSTANCE v3 sample, how does independent loss of 5% of one-second packets change restricted detection time for a fixed causal STA/LTA detector relative to packetized no-fault replay?

## 2. Primary hypothesis

**Hypothesis H1:** 5% independent one-second packet loss increases equal-event-weighted mean restricted detection time relative to no-fault replay.

A 0.5 s change is the predeclared minimum practically relevant effect. This is an exploratory engineering margin equal to half the packet interval; it is not derived from observed network measurements.

## 3. Null/no-effect interpretation

Let Δ be the paired mean change in restricted detection time, fault minus control, in seconds.

- Directional evidence consistent with H1: two-sided 95% confidence interval lower bound above 0 s and point estimate Δ at least +0.5 s.
- Practical equivalence for this setup: 90% confidence interval fully within [−0.5 s, +0.5 s].
- An interval spanning no effect and a relevant effect is inconclusive.
- An interval wholly below 0 s contradicts the predicted direction.
- No support for H1 does not establish real-network robustness; it applies only to this detector, sample, replay and fault model.

No sample-size or power claim is made. The eligible HNZ event count is unknown pending metadata inspection.

## 4. Outcomes and definitions

### Primary outcome: restricted detection time (RDT)

For eligible event-station trace i, let tP_i be the station-trace catalog P-pick on the recorded sample-time axis. Let tE_i,s be the detector emission time for replicate s on the simulation/arrival clock. Set horizon H = 10 s.

RDT_i,s = min(tE_i,s − tP_i, H) if a trigger is emitted in [tP_i, tP_i + H]; otherwise RDT_i,s = H.

RDT has units of seconds and lies in [0, 10]. Assigning H to a miss incorporates missed detections in the primary outcome. A trigger emitted before P is not an event detection and is counted separately as a pre-P trigger. A trigger at the horizon counts only if emitted by P+10 s.

For each trace, average fault-minus-control RDT across the 20 random loss realizations. Average trace differences within each event, then average event means equally, so an event with more stations does not get greater weight. Primary contrast: 5% packet loss versus no fault.

### Secondary outcomes

1. Miss fraction by 10 s: traces with no matched trigger by P+10 divided by all eligible event-station traces; report proportion and percent, also equal-event weighted.
2. Conditional detection latency: tE − tP among matched traces only, in seconds. Report with misses because conditioning on detected traces can hide failures.
3. False trigger rate on labeled noise: unmatched trigger count / valid analyzed HNZ noise trace-hours. Report raw count and valid trace-seconds. This is a sampled-window rate, not a continuous operational alert rate.
4. Pre-P trigger fraction: event traces with one or more emissions before P / eligible event traces.
5. Dose-response sensitivity: RDT and miss fraction at 1% and 10% independent packet loss.
6. Outage sensitivity: RDT and miss fraction for three consecutive dropped packets beginning at the packet boundary nearest to P−1 s (ties earlier); record the actual offset from P. This is an onset-aligned stress case, not a measured outage distribution.
7. Fixed-delay timing check: RDT under constant extra 250 ms packet delay without loss. Detected emissions should shift by approximately 0.25 s, subject to packet boundaries. Failure triggers timing review before interpretation.

There is no “accuracy” metric. No PGA, PGV, target threshold, target-site warning time or warning-utility outcome is planned.

## 5. Dataset, selection and inclusion/exclusion

### Dataset and access status

Use only the official INSTANCE version 3 sample and matching event metadata version 3 from the [INGV dataset page](https://www.pi.ingv.it/banche-dati/instance/). The official page reports 1.7 GB compressed / 2.74 GB expanded, 10,000 events and 1,000 noise waveforms, and CC BY 4.0. The [2021 dataset paper](https://doi.org/10.5194/essd-13-5509-2021) describes fixed 120 s, 100 Hz three-component windows and event/station/trace metadata.

No data are stored in this repository, and no download was done. The source documents public links but actual transfer success was not tested. Verify exact sample contents, schema, version/checksum, license notices and access before implementation.

### Event-trace inclusion

Include every sample event-station trace that meets all criteria:

- unambiguous event ID and station-trace catalog P pick;
- HNZ vertical accelerometer channel;
- 100 Hz and valid trace start/sample-time mapping;
- at least 10 s contiguous pre-P data for LTA warm-up and data through P+10 s;
- digital-count representation available consistently for events and noise; do not mix counts with response-removed physical units;
- no source quality flag for gaps, clipping, spikes or processing faults;
- unique trace identity or resolvable duplicate under the rule below.

Do not select on detector output, amplitude, post-trigger behavior or fault outcome. Publish the number included/excluded at each step and exclusion reasons.

### Duplicates, multiple traces and noise

Distinct event-station pairs remain separate trace observations. If an identical event/network/station/location/channel appears more than once, retain the record with best pre-existing source quality status; if tied or unavailable, retain lexicographically smallest stable trace ID. Never resolve duplicates using amplitude, SNR or detector outcome.

Use all eligible HNZ noise windows in the same counts representation and with valid timing/sample rate and quality status. Sum valid trace-seconds for the exposure denominator; do not call sampled windows continuous station-hours. These are curated, independently selected event-free snippets, not ongoing monitoring.

### Feasibility gate before outcomes

Metadata-only inspection may map field names, counts, joins, data access and licensing; do not inspect detector outputs. Confirm HNZ event and noise records exist, P-pick and trace-start semantics are clear, 100 Hz timing is consistent, windows cover warm-up and horizon, and event/station/trace joins are stable. If HNZ, needed timing or consistent representation is absent, stop and amend/re-review before detector outcomes. Do not quietly substitute another channel, dataset, data representation or detector.

## 6. Split strategy and tuning

No model is fitted and no threshold search is performed; a train/test split is not needed. Freeze all detector, matching, selection and metric parameters before replay. Feasibility metadata inspection cannot be used to tune settings from detector outcomes. Any change made after seeing outcomes makes the revised analysis exploratory and requires a new untouched split or a newly preregistered dataset.

## 7. Detector and fusion

### Fixed baseline detector

Use causal classic STA/LTA on HNZ vertical digital counts:

- sample rate 100 Hz;
- STA 0.5 s (50 samples);
- LTA 10 s (1,000 samples), preceding and not overlapping the STA window;
- on threshold 3.5; rearm threshold 1.5;
- score R[n] = trailing mean-square STA / max(preceding non-overlap mean-square LTA, epsilon);
- trigger on first processed sample crossing the on threshold; rearm at/below off threshold;
- require 10 s contiguous warm-up before trigger evaluation;
- freeze epsilon and numeric precision before implementation.

No extra filtering, resampling, normalization or unit conversion is allowed. INSTANCE’s published detrending/resampling is part of that named dataset version and must be disclosed. This is an interpretable engineering baseline, not an assertion of state-of-the-art EEW performance.

### Fusion

No fusion or event association is used. Detect each station trace independently; equal event weighting is only for statistical aggregation. Multi-station fusion is excluded because sample event joins and simultaneous station coverage remain unverified.

## 8. Time model and gap behavior

Keep six notions distinct:

1. Recorded sample time: UTC time assigned to each sample from trace start, sample index and rate.
2. Packet-ready time: recorded time of the last sample in a packet.
3. Simulated arrival time: packet-ready time plus scenario delay; dropped packets have no arrival.
4. Detection emission time: replay-clock time at which the detector can emit after processing an arriving packet.
5. Event association time: not applicable; no fusion/association in this protocol.
6. Alert issuance and alert delivery time: not applicable; no alert state machine or end-user transport is implemented.

Packets contain one second / 100 samples and are anchored to trace start. All samples in a packet are unavailable until packet arrival; process them in sample order, but timestamp any trigger emission at packet arrival. Map C0 simulation time to the trace UTC axis. Added delay changes arrival/emission time, never recorded sample time.

A lost packet is a missing interval, never zeros or interpolated samples. Reset STA/LTA state at every gap and require a fresh contiguous 10 s warm-up before triggering. Record gaps and warm-up periods. This gap policy is part of the treatment.

## 9. Control and faults

Every scenario uses identical records/windows, detector settings, packetization, matching rules and metric code.

| ID | Condition | Role |
|---|---|---|
| C0 | No injected fault; one-second packetization retained | Primary control; causal packet delivery, not offline whole-record scoring |
| F1 | Independent Bernoulli packet loss p=0.05 per one-second packet | Primary fault |
| F1a/F1b | Same model at p=0.01 and p=0.10 | Exploratory dose response |
| F2 | Drop exactly three consecutive packets beginning at the packet boundary nearest to P−1 s (ties earlier); record the actual offset from P | Exploratory 3 s onset-aligned outage |
| F3 | Add exactly 0.25 s to every packet-ready time; no loss | Timing-accounting sanity check |

No empirical network trace/failure distribution is available. Packet rates, loss probabilities, blackout and delay are **exploratory engineering stress values**, not measured or representative network parameters. One-second packetization is a replay design choice. Do not extrapolate beyond these settings.

F1/F1a/F1b do not retry or reorder. F2 drops exactly three full packets; its start boundary is the nearest trace-start-anchored packet boundary to P−1 s (ties earlier), and the realized offset from P is recorded. F3 adds 250 ms to every packet-ready time.

## 10. Runs and seed policy

- C0: one deterministic run per trace; verify deterministic output/checksum.
- F1, F1a, F1b: 20 predetermined random realizations per trace and condition. This is a Monte Carlo stability choice, not a power calculation.
- Derive per-trace masks deterministically from a logged master seed plus dataset version, event ID, station/location/channel ID, scenario and replicate index using a documented stable hash-to-integer method. Never depend on process order.
- Reuse replicate indices across probabilities but generate Bernoulli masks with each scenario’s probability; masks need not be nested.
- F2/F3: one deterministic run per trace.
- Save master/derived seeds, mask or mask checksum, config checksum, software/runtime versions.

## 11. Matching and unmatched records

Use the station-trace catalog P-pick, not event origin time, as the primary reference. Match a detector trigger only to its own trace and only if emitted in [P, P+10 s]. The first qualifying trigger is the event detection; additional triggers in the interval are duplicates and are reported separately. Pre-P triggers are not matched to the later event. Triggers after P+10 are misses. Noise-window triggers are unmatched and count as false triggers. Events with invalid picks/timing are excluded before replay with a reason; do not impute. Catalog events with no eligible trace are reported as excluded, not detector misses. Ambiguous joins are excluded by frozen rules, never resolved by detector output.

## 12. Statistical summaries and uncertainty

1. For each trace, calculate control RDT and mean fault RDT over the 20 F1 masks; subtract control.
2. Average trace differences within each event; average event means equally.
3. Report mean paired Δ (seconds), median and interquartile range of event-level differences, and event-level distribution.
4. Obtain two-sided 95% event-cluster bootstrap CI with 10,000 resamples of event IDs and a logged bootstrap seed. Resample events, not components, samples, stations or fault masks independently.
5. Report scenario-specific RDT, misses and conditional latency with confidence intervals and all denominators/exclusions.
6. Report within-trace mask variation separately from between-event uncertainty.
7. For noise, report false-trigger count, valid exposure seconds/hours and a descriptive Poisson rate interval; caveat that selected station/time windows may be dependent. Provide station-stratified rates where possible.
8. If the eligible event count or bootstrap support is too small for stable intervals, show event-level points and descriptive intervals, label inference imprecise, and make no confirmatory claim. Do not retroactively invent a minimum sample size or power.

## 13. Threats to validity

- INSTANCE is a curated catalog/quality-selected window dataset, not unbiased live traffic; 120 s noise snippets do not represent continuous operations.
- Faults are artificial; no observed communication data support their rates or representativeness.
- One-second batching adds latency even in control; results depend on this packet protocol.
- STA/LTA is only one simple detector; no generalization to ML, operational pipelines or fusion.
- HNZ coverage may be limited; sample preparation, counts, instrument gain and station/channel variation can affect threshold behavior.
- Resetting LTA after gaps is a consequential, explicit engineering choice; other buffering policies can differ. No interpolation/zero-fill is permitted.
- Catalog P picks have uncertainty; they are reference labels, not exact rupture times.
- Same-event station traces are dependent; equal event weighting and event-cluster bootstrap address but do not remove all dependence.
- Eligible cohort size/quality are unknown until metadata inspection; a small subset may yield descriptive-only evidence.
- Detector emission latency is not end-user warning time; this study has no target site or alert delivery model.

## 14. Interpretation criteria

**Supports H1:** primary estimate is positive, 95% event-cluster CI excludes zero positively, and point estimate is at least +0.5 s. The supported claim is limited to the fixed detector, eligible INSTANCE sample and specified 5% packet-loss replay.

**Weakens/falsifies H1:** 90% CI entirely within ±0.5 s indicates practical equivalence for this setup; 95% CI entirely below zero contradicts the direction. A positive estimate under 0.5 s with broad uncertainty is inconclusive. Failed C0/F3 timing checks or failed data validation invalidate intended interpretation regardless of apparent effect.

## 15. What the study cannot conclude

It cannot estimate actual network loss/delay/jitter/outages/clocks/recovery; deployed-system reliability; multi-station fusion, event association, alert issuance or delivery; target-site warning time, avoided damage or public-safety benefit; generalization to other regions, channels, instruments or pipelines; realism or prevalence of chosen fault values; or that QuakeNode is the first real-time EEW testbed. Integration alone is not claimed as novelty.

## 16. Stop criterion

Stop before implementation/outcome analysis if: (a) official sample/access/license/version cannot be verified; (b) consistent HNZ event/noise traces, trace starts, P picks, 100 Hz mapping or required contiguous windows are missing; (c) stable event/station joins cannot be made; (d) preprocessing/quality gaps cannot be distinguished from injected faults; (e) causal replay would expose future samples or silently fill gaps; or (f) continuing requires changing channel, dataset, detector, selection or primary metric after outcome inspection.

For (a)–(d), switch only to synthetic-fixture software checks (no detector-performance claim) or write a new protocol for a verified continuous dataset. For (e), repair timing and preregister again. A low eligible count does not authorize a convenient silent data swap; report feasibility counts and decide whether a revised descriptive question is worthwhile.

## 17. Reproducibility checklist

- [ ] Protocol version/date and timestamped amendments/reasons.
- [ ] Dataset DOI/release, retrieval date, filenames, SHA-256, license and source notices.
- [ ] Actual metadata schema mapping and unknowns.
- [ ] Frozen event/station selection, exclusions, duplicate decisions and event IDs.
- [ ] Channel, sample rate, representation/units, trace starts, P-pick source and timing convention.
- [ ] Detector equations, thresholds, epsilon, arithmetic, reset/rearm/warm-up behavior.
- [ ] Packetization, clock definitions, fault generator, seeds and masks/checksums.
- [ ] Matching rule, horizon, metrics and denominators.
- [ ] Source revision, dependency lock, OS/runtime, command, config checksum and output schema.
- [ ] Event-level results, exclusions, analysis script, bootstrap seed/intervals and deviations.
- [ ] Synthetic fixture clearly separated from real-waveform detector findings.
- [ ] No waveform redistribution until applicable terms and repository policy are verified.

## 18. Prior-art boundary

Phase 1 identifies QCN (2014) as prior EEW network congestion/failure simulation, Meier (2017) as pseudo-real-time target-site utility that omitted transport/processing delays, and ShakeAlert/FisH as relevant real-time/scenario or streaming evaluation work. This protocol does not claim fault injection or real-time EEW evaluation is new. A possible contribution is a controlled paired causal replay result for one fixed detector and named fault model on a public sample. Exact benchmark novelty remains provisional and requires focused prior-art verification before publication claims.
