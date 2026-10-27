# Minimal pilot specification: offline versus causal preprocessing

**Status:** proposed feasibility pilot; not preregistered, not implemented, and not an evaluation of system-level EEW performance.  
**Decision dependency:** do not begin detector comparisons until a raw-to-release waveform pair, metadata mapping, and data terms are verified.

## Question and scope

For a fixed set of INSTANCE reviewed-P waveform prefixes, does full-window offline preprocessing make earlier processed samples or a fixed detector's decisions depend on waveform samples that would not yet have arrived, compared with an explicitly causal streaming path applied to the same source record?

The first aim is to measure preprocessing dependence and its consequences for one detector on picked traces. It does not estimate earthquake recall, operational false alerts, warning time, network fault effects, or user utility.

## Fixed inputs and prefix perturbations

Freeze a trace manifest from metadata before evaluating detector outcomes. Each row must include event ID, network/station/location/channel, raw file checksum, release HDF5 key/checksum, sample start and rate, units, P-pick time and reference, original archive request, gaps, and inclusion/exclusion reason. Require a verified raw-to-release match. If no such pair exists for a trace, exclude it before analysis.

For each eligible trace, define prefix cutoff indices from the P pick and native sample clock, not from detector results: one cutoff at the fixed pre-P warm-up end and one at the predeclared early post-P horizon. The actual offsets must be frozen after metadata inspection and documented in seconds and sample indices. On a copy of each raw trace, leave samples through cutoff k bit-identical and apply one future-only perturbation to samples after k: (1) constant offset, (2) linear ramp, and (3) seeded bounded noise. Amplitudes are chosen from a metadata-only development trace or stated signal-scale rule before test outcomes; record the exact vector or PRNG seed. The same prefix set and perturbations are applied to both preprocessing arms.

The unperturbed, full-window trace is the paired control. A perturbation is a diagnostic counterfactual, not a physical fault model.

## Preprocessing arms

### Offline comparator

Primary comparator: the released INSTANCE digital-count HDF5 trace, if raw/release identity and alignment can be established. The paper documents 120-second windowing, mean and linear-trend removal, and resampling to 100 Hz before release. This is an opaque release-product comparator unless exact code, options, versions, and padding/edge behavior are recovered. Label it noncausal because the full-window trend estimate uses later samples.

Optional exact-reproduction arm: retrieve source miniSEED and reproduce the paper's complete count preprocessing only after exact detrend implementation, resampling implementation/options, gap handling, and trace boundaries have been recovered. Do not call a generic detrend/resample implementation an exact reproduction. If exact settings remain unavailable, report release-product comparison only.

### Causal streaming candidate

Preferred pilot arm: decode the same original miniSEED incrementally at its verified native sample rate and use no transformation requiring future samples. A no-filter raw-count arm is the simplest causal reference if the fixed detector is meaningful on those counts. If baseline removal is needed, preregister a stateful one-sided filter selected from a documented EEW method or separate development data; do not tune on the pilot traces.

Candidate for evaluation, not a preapproved scientific choice: recursive one-pole baseline estimation, m[n] = alpha m[n-1] + (1-alpha)x[n], y[n] = x[n]-m[n], with alpha = exp(-2 pi fc/fs). Freeze fs and fc from verified metadata and an independent method or development set. Initialize m from the first observed sample; carry state across every packet boundary; suppress scoring for a fixed warm-up; on a gap, emit no fabricated samples, reset filter and detector state, and require the fixed contiguous rewarm interval. Record gap and reset times. Do not resample in the pilot unless a causal resampler and its state, phase, delay and rate conversion are separately specified and tested.

The causal arm must use recorded sample time for the waveform grid and simulated arrival time for availability. Every output carries the latest input's simulated arrival watermark; no output may use any sample whose arrival is later. Detector emission time is separate from sample time and simulated arrival.

## Detector and outcomes

Use one deterministic single-channel STA/LTA trigger as a signal-processing probe, not as an operational EEW baseline. Freeze short/long window lengths, threshold, trigger/rearm rule, warm-up, units/scaling, and evaluation horizon using a documented recipe or separate development data. Keep every detector parameter identical across the two preprocessing arms. If no independently defensible settings are found, report prefix-output dependence only and do not claim detector performance.

Primary outputs:

1. **Prefix-output difference:** for arm a and perturbation q, compute max absolute difference and root mean square difference through sample k between the unperturbed and future-perturbed processed prefixes. Report signal units and normalized scale only if the normalization denominator is predeclared and causal. For a causal arm this should be zero up to numerical tolerance; for the offline arm it quantifies future dependence.
2. **Detector decision change:** whether first trigger before a frozen sample/time horizon changes under future-only perturbation, paired by trace and prefix. Report changed-decision count / eligible trace-prefix pairs, with explicit denominator.
3. **P-relative trigger timing:** first detector trigger emission time minus reviewed P sample time, in seconds, on the unperturbed raw/release paired trace. Report distribution and per-trace paired difference; do not call it warning time. Report misses by fixed horizon as censored/no-trigger outcomes, with count and denominator.

Secondary outputs: trigger count before P in the declared context window, detector statistic maximum, and filter warm-up duration. These characterize artifacts and transients. No accuracy score without an explicit denominator. No false-alert rate from event windows.

## Controls and fairness

- Use identical raw records, prefix indices, event/pick reference, evaluation windows, detector implementation and parameters in both arms.
- Keep packet boundaries and delivery schedule identical. Include a one-sample and irregular-chunk causality software test, but use one frozen chunk schedule in the real-data comparison.
- Run an ideal clean-arrival schedule only; no injected network faults in this pilot.
- Apply the identical future-only perturbation vectors and seeds to both arms.
- Do not tune either arm on test traces. Choose filter parameters independently and freeze them in the manifest.
- Report the offline product's 100 Hz conversion separately if native rates differ. A sample-aligned comparison requires a declared common grid; otherwise compare matched physical-time prefixes and disclose interpolation/resampling differences.
- Never treat processed release arrays as raw causal input.

## Repetitions, uncertainty, and reproducibility

This is a deterministic counterfactual experiment: repeat every perturbation with a fixed stored vector/seed and a fresh process state. There are no Monte Carlo repetitions to inflate sample size. Report all trace-level paired values, eligible denominators, exclusions, and event-clustered summaries. A one-trace software pilot cannot estimate population uncertainty. For a later cohort, use event-level resampling or other clustering that preserves multiple traces from the same event; define the method before examining outcomes.

Required artifacts: trace manifest; original request metadata; archive/release source and license records; checksums; preprocessing source/settings and package versions; causal filter coefficients/state initialization/warm-up/gap policy; detector configuration; prefix/perturbation table; deterministic seed; per-prefix arrays or hashes; per-trace raw outputs; metric code/version; run command; environment lock; and a report of all failed/excluded traces. Do not redistribute restricted waveform data; retain identifiers/checksums and lawful retrieval instructions instead.

## Interpretation and stop rules

The counterfactual establishes whether a specified offline transform can change prefix values when only future samples change. A detector-decision difference establishes consequence for that detector and selected traces only. It does not show that one arm is more seismologically accurate or that a real EEW system gains/loses warning time.

Stop before detector evaluation if any of these apply: no exact raw/release match; unresolved time/pick reference; unverified data permissions; no justified fixed detector settings; no reproducible offline path; or causal counterfactual/chunk/gap tests fail. If the causal path must be tuned on evaluation outcomes, narrow the work to a preprocessing conformance/causality note.

## Data and question limits

INSTANCE reviewed-P traces support conditional behavior around known picked arrivals, not complete catalogs or system denominators. Selected noise snippets may support a separate, explicitly sampled-window statistic once labels and duration are checked. EPIC Alaska is an alternative replay suite, but the archive files are currently unverified and EPIC's existing progressive replay makes a generic replay contribution weak. Do not compute false alert rate, system missed-event rate, target-site threshold exceedance, or warning time from this pilot.
