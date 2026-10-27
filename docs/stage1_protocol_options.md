# Stage 1 protocol options (DRAFT: not a pre-registration)

Research prototype, not an operational warning system. Nothing in this file has been run on real waveforms: no detector, no preprocessing comparison. It proposes candidate frozen recipes and the analysis plan so that you can decide; the chosen one then goes into a pre-registration that is committed before any real-data comparison. Numbers about trace lengths come from metadata only (the 1,000 drawn traces, before exclusions). The completed fetch left **830 comparable traces** (170 empty INGV responses, no other exclusions; 238 events, 141 stations); the comparable-cohort versions of these tables are in `docs/cohort_stage1_summary.md` and differ by under 1.5 percentage points (for example W = 12 s with at least 5 s of scored pre-P data: 76.1% instead of 75.6%).

## 1. Constraints that come from the data

Stage 1 compares two arms on the same trace: the **release arm** (INSTANCE HDF5 Z array, `int32`, the "release product", decision D1) and the **causal arm** (raw INGV miniSEED counts for the same 12,000-sample window, decision D3), through an identical chain and identical packetization.

**Trace layout.** The P sample is `trace_P_arrival_sample` (decision in `quakenode.data.TraceRecord`). In the 1,000 drawn traces:

| quantity | min | Q1 | median | Q3 | max |
|---|---|---|---|---|---|
| pre-P length (s) | 14.71 | 17.03 | 18.28 | 19.69 | 25.12 |
| post-P length (s) | 94.88 | | 101.72 | | 105.29 |

Percentiles of pre-P length: 5% 15.68 s, 10% 16.12 s, 90% 20.64 s, 95% 21.12 s. Fraction with at least T seconds before P: 5 s, 10 s, 15 s: 100% (15 s: 99.9%); 20 s: 19.8%; 30 s, 60 s, 80 s: 0%. This matches the paper's "randomly selected buffer time ranging between 15 and 20 s before the P-wave onset" with some windows starting earlier (Sect. 2.1.3); the release windows were then fixed at 120 s. So a detector gets **14.7 to 25.1 s of data before P** (median 18.3 s) and at least 94.9 s after.

**Pick uncertainty.** `trace_P_uncertainty_s` in the drawn traces: 0.1 s for 548 traces, 0.3 s for 216, 0.6 s for 190, 1.0 s for 46 (median 0.1 s). My earlier statement that the stated uncertainty is 1 s referred to the first trace inspected and was wrong for the cohort. The P sample and the sample implied by `trace_P_arrival_time` differ by exactly +1 sample (10 ms) in 246 of the 1,000 traces and agree in 754. A 10 ms effect is 10% of the smallest stated uncertainty (0.1 s), so it is small but not negligible against a +-0.1 s margin; the protocol therefore includes a +-1 sample sensitivity analysis.

**Warm-up scorability.** Fraction of the 1,000 traces for which scoring can start at least m seconds before P when the detector needs warm-up W seconds (i.e. P - W >= m):

| W (s) | m = 0 | m = 1 | m = 3 | m = 5 |
|---|---|---|---|---|
| 10 | 100% | 100% | 100% | 99.9% |
| 12 | 100% | 100% | 99.9% | 75.6% |
| 15 | 99.9% | 91.7% | 56.2% | 19.8% |
| 20 | 19.8% | 6.3% | 0.6% | 0.1% |
| 30 | 0% | 0% | 0% | 0% |
| 80 | 0% | 0% | 0% | 0% |
| 82 | 0% | 0% | 0% | 0% |

**SeisComP's default chain cannot be scored.** The SeisComP filter documentation (https://www.seiscomp.de/doc/base/filter-grammar.html, read 2026-10-26) says: "The default filter applied by scautopick for making detections is RMHP(10) >> ITAPER(30) >> BW(4,0.7,2) >> STALTA(2,80)", with "an STA/LTA filter with a short-time time window of 2 seconds and a long-term time window of 80 seconds". The LTA alone is 80 s, and the 30 s taper also exceeds the longest pre-P length (25.1 s). **0% of the traces can be scored under that chain** (every W >= 30 s row above is 0%). Any statement about "the SeisComP default" cannot be tested on these windows.

## 2. Documented sources I actually read (used for the recipes)

- **[S1]** SeisComP filter grammar, https://www.seiscomp.de/doc/base/filter-grammar.html: default chain above; `RMHP(timespan)` "A high-pass filter realized as running mean high-pass ... the running mean is subtracted from the single amplitude values"; `BW_BP` "realized as a causal recursive IIR (infinite impulse response) filter"; "Filters in SeisComP are recursive allowing real-time application. Therefore, filter artefacts, e.g. ringing, are always visible at the beginning of the traces or after data gaps."
- **[S2]** `scautopick` page, https://www.seiscomp.de/doc/apps/scautopick.html: `trigOn` default 3, `trigOff` default 1.5; "a pick is set to the time when this threshold is exceeded (pick time) and the picker is set inactive. The picker is reactivated for this stream once the STA/LTA ratio falls to the value of 1.5". The module page text says the Butterworth filter is "of third order" while the default string and [S1] say fourth order (`BW(4,...)`): the documentation is inconsistent; I use the default string.
- **[S3]** ObsPy 1.5.1 trigger tutorial, https://docs.obspy.org/tutorial/code_snippets/trigger_tutorial.html: LTA "typically, it's an order of magnitude larger than the STA duration"; a quoted Han (2009) caption: "The length of the LTA energy collection window is five to ten times the length of the STA energy collection window"; examples `classic_sta_lta(trace.data, int(5 * df), int(10 * df))` with thresholds 1.5/0.5 and `recursive_sta_lta(..., int(5 * df), int(10 * df))` with 1.2/0.5, both unfiltered on an example trace; a network coincidence example with `st.filter('bandpass', freqmin=10, freqmax=20)  # optional prefiltering`, recursive STA/LTA windows "0.5 and 10 second", thresholds 3.5 on / 1 off.
- **[S4]** ObsPy API (installed 1.5.1): `obspy.signal.filter.bandpass(..., corners=4, zerophase=False)`; so the default filter is causal.
- **[S5]** Zuccolo et al. (2021), https://doi.org/10.3389/feart.2021.686272 (full text): SeisComP's default "involves subtraction of the running mean for a given time window, a single application of a one-sided cosine taper at the beginning of new data streams, a Butterworth bandpass filter, and a Short Time Average over Long Time Average (STA/LTA) filter ... calculated continuously in two partially overlapping time windows"; "The picker is re-initialized after a data gap."

I could **not** find, in anything I read, a documented default of "1 s STA / 10 s LTA after a causal 1 to 10 Hz bandpass", so it is not used. The recipes below keep documented structure and values and change only what the trace length forces; each deviation is listed.

## 3. Candidate frozen recipes

All three use causal processing only, a sample-by-sample (streaming) implementation, and identical parameters in both arms. The package already has a Phase 1 "RMS ratio with a preceding non-overlapping LTA" detector; none of these recipes use it, because it is not a documented external recipe (see decision 2).

### Recipe A: SeisComP structure with windows scaled to the traces

Chain: `RMHP(10) >> BW(4, 0.7, 2) >> STALTA(2, 10)`, trigger on 3, off 1.5 ([S2]), re-arm when the ratio falls to 1.5.

- Documented values kept: RMHP 10 s, Butterworth order 4 and corners 0.7/2 Hz, STA 2 s, trigOn 3, trigOff 1.5.
- Deviations (forced by the trace length, not by outcomes): LTA 80 s to 10 s (5 times the STA, inside the "five to ten times" statement in [S3]); the 30 s `ITAPER` is dropped (it would cover the whole pre-P period).
- Warm-up: the LTA needs 10 s, the RMHP 10 s, and [S1] says the Butterworth start-up artefacts are visible at the beginning but gives no duration. **Scoring starts at W = 12 s** (LTA 10 s plus one more STA length, 2 s, as a settling allowance): 100% of the 1,000 traces have P - W >= 0, 99.9% have at least 3 s of scored pre-P data, 75.6% at least 5 s. W = 15 s would score 99.9% / 56.2% / 19.8% (m = 0 / 3 / 5).
- Causal arm: raw counts (integers as stored, no scaling) through the chain; the first W seconds are processed but not scored; the RMHP running mean is a trailing mean over the samples seen so far, up to 10 s (initial transient: the mean of the available samples). [S1] does not say how SeisComP initializes it and I did not read its source, so this is an assumption to be recorded.
- Release arm: the HDF5 Z counts (`int32`) through the identical chain, identical W.

### Recipe B: causal baseline removal only

Chain: `RMHP(10) >> STALTA(2, 10)`, trigOn 3, trigOff 1.5, W = 12 s. Same documented values as A without the bandpass. This is the version most sensitive to the question, because the only conditioning is the documented running-mean high-pass.

### Recipe C: ObsPy tutorial coincidence-style example

Chain: causal Butterworth bandpass 10-20 Hz (`corners=4`, `zerophase=False`) then recursive STA/LTA with STA 0.5 s and LTA 10 s, trigOn 3.5, trigOff 1 ([S3], [S4]); W = 12 s (LTA 10 s plus settling). Deviation: the example is for a 4-station local network of small events, not a regional catalogue; the 10-20 Hz band is shown as "optional prefiltering". It is included as an independent documented source, not as the preferred one.

### Recommendation

Primary **A**, secondary **B**, optional **C**. A is the closest to a deployed, documented chain; B isolates the baseline-removal question; C checks that a different documented family does not change the conclusion. Do not tune any of them: parameters are frozen from the sources above before any real-data run, and only reported sensitivity analyses (below) are allowed.

## 4. What the two arms are, exactly

- Window: 12,000 samples at 100 Hz; sample k at window time k/100 s. Release arm: `load_release_z`. Causal arm: `load_raw_window` (nearest raw sample to `trace_start_time`, no shifting; the sub-sample offset is reported, never applied; segments outside the window do not matter; any gap inside the window excludes the trace).
- Packetization: `make_stream_packets` with the same packet length for both arms (proposal: 100 samples; the choice does not change sample-clock results), so the sample, ready and arrival clocks are identical and only values differ.
- Processing: streaming chain with chunk state, equivalence-tested against whole-array reference implementations (ObsPy/SciPy) before use; future-sample counterfactual test for the full chain (alter only samples after T, earlier outputs must be bit-identical).
- Cohort: 1,000 drawn IV/HH traces minus pre-declared exclusions (`docs/cohort_stage1_summary.md`).

## 5. Outcomes and statistics (proposal)

- **Reference:** the reviewed P sample `P` (`trace_P_arrival_sample`), with tolerance `u` = the trace's own `trace_P_uncertainty_s` (documented metadata).
- **Trigger:** the first sample at or after the scoring start where the STA/LTA ratio is at or above trigOn while armed. After a trigger the detector is inactive until the ratio falls to trigOff ([S2]); later triggers are duplicates and are counted, not scored.
- **Primary outcome per trace and arm:** `D` = time of the first **qualifying** trigger minus P, where qualifying means `-u <= D <= H`. Proposed horizon `H` = 5 s (a free choice with no source: decision 4); sensitivity at 2 s and 10 s.
- **Miss:** no qualifying trigger. **Pre-P trigger:** a trigger with `D < -u` after the scoring start (counted separately per arm; it does not stop later qualifying triggers from counting). **Duplicates:** triggers after the first qualifying one.
- **Paired analysis:** for traces with a qualifying trigger in both arms, `d = D_causal - D_release`. Report the median and the mean of `d` with 95% bootstrap CIs (10,000 resamples, fixed seed) **clustered by event** (traces of one event share the source; the 1,000 traces come from about 258 events). Report the paired 2x2 table of hit/miss, the miss-rate difference (causal minus release) with a clustered bootstrap CI, discordant counts, and an exact McNemar test as a secondary figure that ignores clustering (stated as such).
- **Negligible-effect margins (proposal):** `|median d| <= 0.1 s` and `|miss-rate difference| <= 2 percentage points`, declared "negligible" only if the whole 95% CI lies inside both margins. Justification: 0.1 s is the smallest stated P uncertainty and 55% of the traces carry it; it is also 10 times the 10 ms sample/time disagreement and 10 sample intervals. For 2 percentage points: with about 800 comparable traces and a discordant fraction of 5% or less, the paired-difference CI half-width is roughly 1.5 points, so 2 points is about the smallest margin the sample could resolve; this reasoning is arithmetic on assumed counts and must be re-checked once the comparable count is final.
- **Pre-declared sensitivity analyses (reported, never used to choose the recipe):** P shifted by +-1 sample; `H` 2 s and 10 s; `u` fixed at 0.5 s instead of per-trace; W 12 s versus 15 s; packet length 1, 100, 1000. **Pre-declared strata:** event magnitude tercile, epicentral distance tercile, release-trace amplitude (RMS) tercile.

## 6. Honest prediction note (what to expect, and what is informative)

I have not looked at any real-data result, so this is reasoning, not a finding.

- Both arms pass through a causal baseline remover (RMHP) before the STA/LTA. The release array has had a least-squares line removed over the whole 120 s window, which uses samples after P, and the raw counts carry offsets of the order of hundreds to thousands of counts (in the IV traces compared earlier the absolute window mean ranged from about 36 to 14,100 counts for HH/EH Z). With RMHP(10) the offset is removed within the first seconds by either arm, so the main expected difference is the **start-up transient** (inside the unscored first W seconds) plus the small low-frequency ramp that the whole-window fit introduces into the pre-P noise, which RMHP removes only up to its lag. In Recipe A the Butterworth band (0.7-2 Hz) removes more of that ramp, so I would expect the smallest differences there and the largest in B.
- **A result inside the margins is informative**: it would support using the release product as a stand-in for causally processed data **for chains that contain a causal baseline remover**, and it would say so with an interval, on IV/HH only.
- **A result outside the margins is informative too**, but would need the strata and a per-trace look (a few large-offset or large-event traces driving a median shift versus a broad shift) before any interpretation.
- Either way, the result is about STA/LTA triggers relative to the reviewed P sample on this cohort. It says nothing about ML pickers (Stage 2), HN channels, warning times at target sites or system-level false-alert rates.

## 7. Decisions I need from you

1. **Recipe set:** A primary, B secondary, C optional (as recommended), or something else?
2. **STA/LTA definition:** implement ObsPy's `classic_sta_lta` or `recursive_sta_lta` semantics (with equivalence tests against ObsPy), or SeisComP's "partially overlapping windows" form (source not read), instead of the Phase 1 RMS-ratio detector? A, B and C above are specified by name and window lengths only.
3. **Start-up handling:** scoring start W (12 s proposed, 15 s alternative), the RMHP initialization (mean of samples seen so far), and omitting `ITAPER`.
4. **Qualifying window:** `H` = 5 s and per-trace `u` as the pre-P tolerance, or other values; whether pre-P triggers should disqualify a trace instead of being counted separately.
5. **Margins:** +-0.1 s and +-2 percentage points, or different ones.
6. **Re-arming:** use the SeisComP re-arm rule (as written above) or "first trigger only", as in the Phase 1 code.
7. **Bootstrap clustering by event** (proposed) and the bootstrap seed.
8. **Grid-offset exclusion:** as written it can never trigger (nearest-sample alignment bounds the offset at 0.5 sample). Keep it as a reported distribution, or replace it with a rule such as excluding offsets above a smaller bound?
9. **P reference:** `trace_P_arrival_sample` as authoritative with a +-1 sample sensitivity (proposed).
10. **Packet length** for the streaming run (100 proposed).
