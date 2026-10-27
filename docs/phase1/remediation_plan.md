# Phase 1 remediation plan after NO-GO

**Date:** 2026-10-26  
**Decision:** Do not implement the original packet-loss study or main pipeline. The selected INSTANCE data product violates the intended causal-input assumption; reviewed-P selection restricts metrics; the broad contribution overlaps existing EEW work.

## Blocker classification

| Blocker | Classification | Evidence | Minimum evidence to clear |
|---|---|---|---|
| 1. Future-dependent preprocessing | **Requires scope change** | INSTANCE v3 digital counts are documented as 120 s windows with mean/linear detrending and resampling to 100 Hz before HDF5 release. Current protocol selects this product. Exact resampler and numerical impact unknown; no loader/data/cache exists locally. | Matched raw archive input; inspect one raw/release pair; document all transforms/time/rate/cache; freeze justified causal preprocessing/state independently; pass full-chain future, arrival, chunk and gap tests; amend/re-review protocol. |
| 2. Reviewed P picks and metric claims | **Requires scope change** | Stations selected where reviewed picks contributed to preferred locations under residual/weight criteria. One HNZ trace detector, selected noise windows, no fusion, alert delivery or target threshold. HNZ sample schema not inspected. | Restrict to P-picked trace behavior; verify HNZ event/noise rows, fields, time joins and counts; define exclusions/denominators. Event recall, operational false rate and warning utility require additional data/methods below. |
| 3. Research contribution | **Unresolved** for a narrow candidate; broad contribution rejected | QCN directly simulates EEW network congestion/link failure with delay/message-loss metrics. EPIC Alaska replays real multistation waveforms progressively, associates triggers, matches events, and reports misses/errors/alert evolution. Exact preprocessing comparison not artifact/literature checked. | Inspect QCN full methods/code artifact and EPIC suite/supplement/license; targeted online/offline preprocessing search; show a meaningful paired outcome. If gap collapses, pause or make a conformance/reproducibility artifact without research novelty claim. |

## Blocker 1: remediation

Configured path: INSTANCE v3 HDF5 → proposed adapter → packetizer/replay → STA/LTA. The dataset paper documents the upstream count path: gap-record exclusion, trim, 120 s window, full-window mean/linear detrend, resample 100 Hz, metadata calculation, HDF5. Saying “no additional preprocessing” does not eliminate this upstream future dependence. The paper does not specify exact resampling implementation in inspected methods. The physical-unit response-removal/taper branch is not selected.

No pipeline, waveform, cache, test or outcome exists here. Therefore this is a source-supported design defect, not an observed measured bias.

Disqualify the processed HDF5 counts as causal primary input. Investigate original miniSEED retrieval for a frozen subset via EIDA. EIDA says most datasets are CC BY 4.0 but terms are network-specific and some data restricted; verify contributors, access, original rates and matching before acquisition/redistribution. Prefer native-rate cohort; otherwise specify and test one-sided causal resampling.

If required, choose a documented causal EEW preprocessing recipe or independent development cohort. Freeze filter coefficients/state, initialization, warm-up/scored start, chunk carry, gap reset and rewarm. Do not zero-fill/interpolate or tune on evaluation outcomes. Required tests: alter only future samples and prove all earlier preprocess/detector outputs unchanged; delay/alter future packets and prove logs through cutoff unchanged; test chunk invariance and gap recovery. Exercise decode→preprocess→cache→replay→detector. Tests are not yet implemented or run.

Separate preprocessing from detector effects with paired arms on identical raw records, P references, windows, detector code/parameters, packet schedule, gap policy and fault masks: causal online path; exact full-window release-product comparator labeled noncausal; optional raw native-rate ablation. Recover the resampler or describe comparator as opaque product. No per-arm retuning.

## Blocker 2: metric/population remediation

Limit primary claim to **P-pick-conditioned per-trace trigger timing**. Denominator: eligible records with stable trace ID, unambiguous reviewed P and verified sample-time mapping under frozen rate/quality criteria. A trace miss is no trigger in [P,P+H] divided by all eligible picked traces. Report pre-P/duplicate emissions and conditional latency together with misses. Never call this event recall.

Use noise only as selected-window trigger propensity: raw count divided by analyzed valid seconds/hours. Do not call these windows true negatives or infer continuous false-alert rate. Verify HNZ noise availability before use.

Warning time stays out of scope: it needs a target physical-unit waveform/response, explicit threshold time, alert issuance/delivery and a common clock. Event-level recall needs continuous or systematic station streams, station availability, independent sufficiently complete catalog, fusion and frozen event matching. Operational false-alert rate needs long continuous exposure and adjudication of potentially uncatalogued events.

## Blocker 3: contribution remediation

Reject the broad “unified testbed” novelty claim. QCN (2014) already simulates network congestion, link failure, message delay/loss and topology/rerouting for EEW. Williamson et al. (2026) already uses actual multistation waveforms in progressive EPIC replay, trigger association, event matching, misses/false events, source errors and alert evolution; its paper says replay timing lacks measured telemetry latency. Zuccolo et al. also establish real-time-style EEW simulation and target utility. These abstractions differ, but cover much of the claimed seam.

Candidate narrower question: does full-window INSTANCE count processing materially alter this fixed detector's P-relative outcomes versus causal processing of the same raw waveforms, and possibly the paired packet-loss contrast? This is not established as novel. Check artifacts and specific literature first. A contribution must show a meaningful, stable empirical consequence; software integration alone is not enough. If none emerges, pause or report only conformance/reproducibility.

## Ordered gates before reconsidering GO

1. Metadata-only v3 audit: actual HNZ event/noise rows, field names, P references, starts/rates/units, quality flags, duplicates, joins and exclusion counts.
2. Verify per-network terms and availability for a small frozen subset; obtain only a bounded matching miniSEED/StationXML sample after access is understood.
3. Inspect raw/release correspondence and recover transform provenance or label the release arm opaque.
4. Freeze causal preprocessing independently and revise population/metric definitions.
5. Implement and run full-chain future, arrival, chunk and gap tests with command/output recorded.
6. Inspect QCN methods/artifact and EPIC suite/supplement/terms; search specific online/offline preprocessing prior art.
7. Amend protocol/config and obtain independent review before main pipeline work.

Stop real-waveform work if raw records cannot be legally accessed/matched; time/rate/P metadata is ambiguous; filter/state depends on test outcomes; future tests fail; cohort is insufficient for stated inference; or prior work already answers the narrow question. Synthetic fixtures prove software behavior, not seismic detector performance.

## Recommendation

**NO-GO for the proposed first experiment and main pipeline.** The minimum evidence needed to reconsider is: (1) a verified matched raw miniSEED subset and network terms; (2) an independently frozen causal path with full-chain future-counterfactual tests passing; (3) a metadata-derived eligible-cohort report supporting only picked-trace metrics; and (4) artifact-level prior-art review showing a consequential, nonduplicative question. No blocker is resolved by this document alone.

## Sources checked 2026-10-26

- Michelini et al. 2021, [INSTANCE DOI 10.5194/essd-13-5509-2021](https://doi.org/10.5194/essd-13-5509-2021); [official release page](https://www.pi.ingv.it/banche-dati/instance/).
- EIDA [data policy](https://eida.ingv.it/en/datapolicy), [waveform access](https://www.eida.ingv.it/en/getdata).
- Portnoi et al. 2014, [QCN DOI 10.1016/j.procs.2014.05.041](https://doi.org/10.1016/j.procs.2014.05.041).
- Williamson et al. 2026, [EPIC Alaska DOI 10.1785/0120260139](https://doi.org/10.1785/0120260139).
- Zuccolo et al. 2021, [DOI 10.3389/feart.2021.686272](https://doi.org/10.3389/feart.2021.686272).

