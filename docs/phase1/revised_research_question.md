# Revised research question after the NO-GO

**Date:** 2026-10-26  
**Status:** candidate only; not a preregistration or authorization to implement. Raw waveform access, record matching, metadata, causal preprocessing and prior-art artifact review remain open.

## Candidate question

> For INSTANCE catalog-picked HNZ traces that can be matched to their original archived miniSEED, how much does the full-window count-processing product change a fixed STA/LTA detector's P-relative trigger behavior compared with causal processing of the same source waveform?

Primary outcome candidate: paired per-trace first qualifying trigger emission time relative to reviewed P, with frozen horizon and explicit horizon penalty for misses. Report miss-by-horizon, pre-P/duplicate triggers and selected-noise-window counts separately. Population is only the matched, quality-screened, reviewed-P trace subset. This does not estimate system-wide event recall, continuous false-alert rate, network reliability, target warning time or user utility.

This makes the identified processing problem testable; it does not assume causal preprocessing is more accurate. Choose and freeze causal processing using an existing documented EEW recipe or an independent development cohort. If the causal path cannot be justified without evaluation-outcome tuning, stop at a software/data conformance note.

## Candidate paired experiment

1. **Input:** retrieve original miniSEED for a frozen metadata-selected subset, with StationXML and bulletin picks. Match records by event ID, network/station/location/channel and sample-time map. Publish match/exclusion counts and checksums; verify network terms first.
2. **Causal arm:** incremental raw delivery; prefer verified native-rate cohort. No whole-record detrend, zero-phase filter, full-window normalization, future-supported resampling or retrospective quality feature in the online path. If filtering is needed, freeze coefficients, initialization, warm-up and scoring start independently of test outcomes.
3. **Offline arm:** exact INSTANCE processed HDF5 product or reproduced full-window transform, labeled noncausal. Recover exact resampling implementation/version; otherwise describe it as release-product comparison.
4. **Control fairness:** same raw records, P references, detector code/parameters, scoring windows, packetization, gap policy, no-fault condition and pre-generated fault masks. No per-arm tuning. Optional raw/no-detrend ablation only for suitable native rates.
5. **Falsification:** if paired effects lie in a predeclared negligible range with informative uncertainty, material effect is unsupported for this detector/cohort. An effect limited to arbitrary filter initialization/transients is not general evidence.

## Closest prior work and distinction

| Prior work | Already does | Candidate distinction (not a novelty claim) |
|---|---|---|
| Portnoi, Schlachter & Taufer (2014), [QCN network impact](https://doi.org/10.1016/j.procs.2014.05.041) | Discrete-event QCN sensor/client/server and network simulation; congestion/link failures, message delay/loss and topology/rerouting comparisons using modeled observations for the 1986 Oceanside event. | Candidate uses matched real source waveforms and isolates preprocessing effect for one trigger; network failure simulation is not new. |
| Williamson et al. (2026), [EPIC Alaska replay](https://doi.org/10.1785/0120260139) | Progressive multistation real-waveform replay through EPIC; trigger association, catalog event matching, misses/false events, source errors and evolving alerts on 530 events. Paper says replay timing lacks measured telemetry latency. | Candidate is much narrower/single-trace and examines input processing, not event-level EEW. |
| Zuccolo et al. (2021), [real-time EEW evaluation](https://doi.org/10.3389/feart.2021.686272) | Streaming simulations comparing PRESTo and SeisComP/VS, effective processing time and target warning utility. | Candidate excludes fusion/utility and tests preprocessing on matched traces. |
| Michelini et al. (2021), [INSTANCE](https://doi.org/10.5194/essd-13-5509-2021) | Curated reviewed-P 120 s windows, count traces detrended/resampled to 100 Hz, and separate response-removed physical product. | Candidate measures whether the released count product changes incremental trigger results versus matched raw inputs. |

QCN and EPIC materially narrow the broad testbed gap. Meier (2017) already evaluates pseudo-real-time target shaking/warning utility; the audited method assumes correct detection/association and omits transmission/processing delays ([DOI 10.1002/2017JB014025](https://doi.org/10.1002/2017JB014025)). CREW is an operational EEW testing facility that runs methods on live network data and reports performance ([EPOS CREW](https://www.epos-eu.org/tcs/near-fault-observatories/services/crew)). ShakeAlert synthesized-sequence testing exercises operational algorithms and alert timeliness on challenging scenarios ([DOI 10.1785/0220220088](https://doi.org/10.1785/0220220088)). Zuccolo et al. compare streaming EEW algorithms and warning utility. These works establish that real-time evaluation, event-level testing, network/latency concerns and utility measures are not novel in isolation. The same-record preprocessing comparison is only a candidate distinction. Inspect QCN full methods/artifact, EPIC suite repository/supplement/license, and specific online/offline seismic preprocessing literature before any novelty claim. The empirical contribution must be a stable, consequential paired result or a well-supported limit; an adapter is insufficient.

## Hard gates

- EIDA provides the exact original miniSEED for a small frozen subset and each contributing network's terms are verified.
- Raw/HDF5 correspondence, timing, sample rate, units, channel and gaps reconcile.
- Exact INSTANCE transform is recovered, or the offline arm is explicitly opaque release product.
- Causal preprocessing/state is justified independently of evaluation outcomes.
- Full-chain future-counterfactual, arrival-cutoff, chunk and gap tests pass.
- QCN/EPIC artifact checks and targeted prior-art search do not collapse the narrow question.

If any gate fails, do not run detector performance comparisons. Synthetic tests establish software invariants only. Do not switch dataset/channel after looking at outcomes.

**Permissible eventual claim:** “For this matched reviewed-P subset, the released full-window product changed (or did not materially change) this fixed detector's P-relative trigger outcomes relative to the declared causal processing path.”

Do not claim first real-time EEW evaluation, realistic operational fault impact, system-wide misses/false alerts, user warning time, or general EEW robustness.

