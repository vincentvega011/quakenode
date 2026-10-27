# Novelty gap assessment: preprocessing causality pilot

**Checked:** 2026-10-26  
**Scope:** focused assessment of the candidate comparison of INSTANCE full-window preprocessing and causal streaming preprocessing. This is not an exhaustive systematic review.

## Decision

The broad QuakeNode claim of an integrated causal replay, faults, fusion, and warning-utility testbed is not defensible as a new contribution. Prior work already covers real-time EEW comparison, multistation progressive replay, event-level matching, target-site utility, and EEW network congestion/failure scenarios.

The narrow same-record question remains a **candidate gap, not an established novelty claim**: on a frozen reviewed-P INSTANCE subset, measure whether the released full-window count-processing product changes prefix values and one fixed detector's P-relative trigger decisions/timing compared with a specified causal stream path on the same original records. The sources reviewed do not report that exact paired comparison. They also do not prove that it has never been studied. The result could be scientifically useful as a reproducibility boundary for using curated ML windows in incremental detector evaluation, but only if it demonstrates a nontrivial, stable effect or a well-supported negligible-effect bound and is not an arbitrary filter-choice comparison.

**Novelty status: unresolved.** Access/matching and exact transformation details are also unresolved. Do not implement the main pipeline. A bounded data/artifact feasibility check is justified; full experiment implementation is conditional on evidence gates below.

## Closest prior work

| Work | Exact relevant methods/results | Relation to candidate |
|---|---|---|
| Michelini et al. 2021, INSTANCE, [DOI 10.5194/essd-13-5509-2021](https://doi.org/10.5194/essd-13-5509-2021) | Publishes catalog-selected 120 s traces around reviewed phases. Count traces are detrended for mean and linear trend and resampled to 100 Hz before HDF5 assembly; paper also describes a separate physical-motion processing branch. | Defines the offline release path whose causal suitability is questioned. Paper's objective is a ML dataset; it does not, in inspected methods, quantify future-tail perturbation effects on incremental processing or fixed detector outcomes. Exact code/options and identical source/release pair are still to be verified. |
| Portnoi, Schlachter & Taufer 2014, QCN network impact, [DOI 10.1016/j.procs.2014.05.041](https://doi.org/10.1016/j.procs.2014.05.041) | Simulates network congestion and failures in the Quake-Catcher Network master-worker deployment and compares a multiple-server topology. Publisher abstract reports detection delay changing from about 1.8 s to 173 ms for congestion and lost trickle messages from 2,013 to 391 for network failure. Prior Phase 1 inspection describes message/network simulation around modeled observations. | Establishes that network failures and EEW timing impact are already studied. It does not answer same-record full-window versus causal waveform preprocessing. Its abstract and detailed implementation evidence have different verification status; reusable code/config/license are not established. |
| Williamson et al. 2026, EPIC Alaska replay, [DOI 10.1785/0120260139](https://doi.org/10.1785/0120260139) | Packages 530 Alaska events with per-event miniSEED and station/network metadata; runs progressive simulated-real-time EPIC replay, associates triggers, evolves source estimates and matches/misses/false events against ComCat; 345/530 events matched. | Direct prior art for multistation replay and event-level evaluation. Candidate focuses on processing dependence at one trace/prefix, not a new replay system. The data archive is not yet directly inspectable in this sprint. |
| Zuccolo, Cremen & Galasso 2021, [DOI 10.3389/feart.2021.686272](https://doi.org/10.3389/feart.2021.686272) | Compares PRESTo and SeisComP VS/scanloc in real-time playback using recorded and simulated streams, evolving source estimates, effective processing timing and target-site warning/ground-motion utility. | Establishes streaming algorithm comparison and utility evaluation. Candidate's preprocessing manipulation is narrower and does not assess warning utility. |
| CREW/EPOS, [official service page](https://www.epos-eu.org/tcs/near-fault-observatories/services/crew) | Describes a real testing facility using low-latency SeedLink, isolated software VMs, QuakeML alert standardization, and location/magnitude/lead-time/ground-motion metrics. | Counters a broad claim that a real-time EEW testing facility is missing. Candidate is not a replacement for such a facility. |
| Meier 2017, [DOI 10.1002/2017JB014025](https://doi.org/10.1002/2017JB014025) | Prior Phase 1 audit describes pseudo-real-time updates and target-site warning utility/false/missed outcomes with assumptions about detection/association. Detailed source was not freshly retrieved in this sprint. | Relevant to warning utility prior art; not a direct preprocessing comparison. Claim details require rechecking before publication. |
| 2026 real-time seismic classification study, [DOI 10.1007/s12145-026-02099-6](https://doi.org/10.1007/s12145-026-02099-6) | Uses detrending and bandpass preprocessing for time-frequency image inputs and evaluates classification across datasets including INSTANCE. The inspected article describes offline prepared-window classification, not a proven end-to-end incremental pipeline. | Shows that preprocessing/INSTANCE classification work is current. It challenges overly broad claims about unstudied preprocessing, although it does not establish the same-prefix causality comparison. |

## What might be new, stated narrowly

Potential contribution, if the evidence gates are met:

> For an explicitly enumerated, legally usable set of matched original INSTANCE records and released HDF5 traces, we quantify how future-only changes to the record alter earlier outputs of the documented full-window release path, and whether those changes alter a fixed, independently configured detector's decisions or P-relative trigger times compared with a declared causal processing path.

The methodological distinction is not “we integrated a replay framework.” It is a controlled paired experiment that isolates full-window preprocessing as a source of prefix dependence while holding waveform identity, detector, timing references, and evaluation windows fixed. The causality property itself is mathematically expected for an online transform; the empirical contribution must therefore be the documented release-path comparison and a measured detector consequence or a rigorous bound—not merely a test showing that a full-record linear detrend uses future samples.

If no detector consequence is found, the result can still be a narrow data/processing conformance note if it establishes a reproducible bound and explains when the released product is or is not valid for incremental evaluation. A code adapter alone is not a contribution.

## Reasons the gap may collapse

1. **Exact comparison may already exist.** The focused audit did not exhaustively search supplements, software repositories, or the signal-processing literature for offline-to-online detrending/resampling comparisons on the same seismic records.
2. **INSTANCE may not expose a matched raw source.** The paper's EIDA source descriptions do not prove that the small sample can be mapped to identical original miniSEED with matching sample starts and network permissions.
3. **The preprocessing recipe may be irreproducible.** The paper-level description does not fully specify detrend function/options or resampling kernel/phase/padding. Comparing to the release product is possible, but attributing observed differences to a reproducible exact algorithm may not be.
4. **Detector consequence may be trivial or arbitrary.** A result could depend on selected cutoff, filter initialization, warm-up, sample rate, or detector threshold. A fixed causal filter must be independently justified.
5. **No useful warning claim follows.** Reviewed-P clips do not establish system recall, false-alert rates, target-site shaking threshold exceedance, or warning time.
6. **Preprocessing is expected to differ.** Showing that global detrending changes under future-tail perturbations is not surprising; significance depends on the size, stability, and practical consequence of the difference.

## Minimum evidence before implementation

- Inspect actual INSTANCE sample metadata and choose records without detector-outcome selection.
- Obtain one small original miniSEED record only after size and per-network use terms are checked; match station/channel, event, sample rate, units, start time and P pick to a released HDF5 trace.
- Recover the exact offline transform or label the comparator honestly as the published release product, not exact reproduction.
- Freeze a causal transform, detector, warm-up, sample grid, cutoff indices and perturbation vectors independently of test outcomes.
- Pass full-chain future-counterfactual, chunk-boundary, state initialization and gap tests.
- Search the exact paired question in seismic preprocessing papers, supplements, repositories and conference proceedings; inspect QCN and EPIC artifacts where available. Archive search queries and inspected sources.
- Demonstrate a detector consequence that is stable across predeclared traces/perturbations, or report a sufficiently informative negligible-effect bound. A synthetic test alone is not evidence of a seismic detector effect.

## Verdict

**CONDITIONAL GO for a bounded pilot feasibility step; NO-GO for the main pipeline or any novelty claim today.** A real source and public dataset route are credible, and the experiment can be formulated falsifiably. But usable paired records, exact timing/provenance, full archive access conditions, and novelty beyond the focused search are not established. The minimum next action is to inspect small metadata only, verify one INSTANCE raw-to-release match and its network license, and inspect the EPIC record file listing. If those checks fail, pause detector implementation and reassess the question around a synthetic preprocessing conformance study, explicitly without claiming seismic performance.

## Sources and verification status

- INSTANCE release page: https://www.pi.ingv.it/banche-dati/instance/ — official release counts, sample size and CC BY 4.0; checked 2026-10-26.
- Michelini et al. (2021): https://doi.org/10.5194/essd-13-5509-2021 — dataset and preprocessing methods; checked 2026-10-26.
- Williamson et al. (2026): https://doi.org/10.1785/0120260139 — EPIC Alaska suite and replay methods; checked 2026-10-26.
- EPIC data DOI: https://doi.org/10.5281/zenodo.19897535; DataCite record https://api.datacite.org/dois/10.5281/zenodo.19897535 — metadata license CC BY 4.0, no file metadata; checked 2026-10-26. Zenodo record API returned HTTP 500.
- QCN: https://doi.org/10.1016/j.procs.2014.05.041 — publisher abstract verified; detailed artifact/reproduction status incomplete.
- Zuccolo et al. (2021): https://doi.org/10.3389/feart.2021.686272 — primary article on streaming EEW comparison and warning utility; checked in prior Phase 1 audit and reconfirmed by citation.
- CREW: https://www.epos-eu.org/tcs/near-fault-observatories/services/crew — official service description; checked in prior Phase 1 audit.
- Meier (2017): https://doi.org/10.1002/2017JB014025 — carried forward from prior audit; detailed source not freshly retrieved in this sprint.
- 2026 real-time classifier: https://doi.org/10.1007/s12145-026-02099-6 — current paper preprocessing context; checked 2026-10-26.
