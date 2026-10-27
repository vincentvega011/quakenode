# Causal preprocessing audit

**Checked:** 2026-10-26  
**Status: REQUIRES SCOPE CHANGE.** The proposed replay input is processed over complete 120-second windows before it reaches replay. It cannot support a strict causal-input claim.

## Scope and finding

The proposed YAML selects the INSTANCE v3 sample, HNZ, digital counts, 100 Hz and 120 s. It sets no additional preprocessing, but that does not undo processing already applied to the HDF5 product. The official INSTANCE paper §2.1.5 documents the digital-count preparation: remove traces with gaps, trim, create 120 s windows, remove mean and linear trends, resample to 100 Hz, then calculate SNR/quality metadata and assemble HDF5. Thus the selected release traces are not raw causal inputs. Whole-record mean/trend estimation uses future samples relative to any early replay cutoff.

No exact event/station/channel trace IDs have been frozen: the config uses event_ids: null and the sample has not been inspected. The current object is a selection rule (qualifying HNZ traces), not an enumerated cohort.

The paper does not give the exact detrend call/options or resampling kernel in the inspected methods. No data, HDF5 trace, loader, cache or application code exists in the workspace. The documented full-window detrend establishes a causal defect in the proposed design; its numerical effect on STA/LTA times or fault contrasts is **unmeasured**. Do not claim either a large or negligible effect.

The paper's separate physical-unit branch applies instrument response removal with frequency corners 0.01, 0.04, 25 and 40 Hz, a cosine frequency taper, and a 5% endpoint cosine taper. The protocol does not select this branch. Those whole-record operations must not be substituted into a causal input path.

## Exact proposed path

The current proposal is: official INSTANCE v3 sample/HDF5 → proposed data adapter → one-second packetization → fault scheduler/replay → fixed STA/LTA. The YAML has no waveform/metadata paths or checksum; access is unverified and data are not downloaded. The architecture describes an HDF5 adapter, not raw archive retrieval. There is no code path to inspect.

The source paper's route is:

1. Retrieve archived EIDA miniSEED for selected bulletin earthquakes/stations.
2. Select stations with manually reviewed P picks used in preferred event locations; require phase residuals and location weights by paper criteria.
3. Download nominal 125 s source intervals around P and cross-check file/phase metadata.
4. Remove traces with gaps, trim and create 120 s windows.
5. Remove mean and linear trend over the waveform; resample to 100 Hz.
6. Calculate SNR/quality metadata and publish digital counts in HDF5.
7. QuakeNode would packetize this already transformed HDF5 array.

The paper says actual trace starts can vary due to MiniSEED record boundaries and missing pre-P data. A correct absolute sample-time/P-pick mapping is not yet verified. Retrospective SNR and 161-sample Hampel spike metadata may depend on post-P samples; they must not be fed to an online detector or used as though available at arrival time.

| Operation | Future dependence / status |
|---|---|
| Reviewed-P event/station selection | Not a waveform transform, but it conditions the evaluation cohort on retrospective reviewed picks. Confirmed. |
| Source gap exclusion | Paper says gapped traces are excluded; no fill is described. Changes cohort; actual quality flags uninspected. |
| Trim/window | Not intrinsically noncausal, but full-window array availability does not mean samples arrived. Trace start/time map unverified. |
| Mean removal | Applied over the full trace; future-dependent. Confirmed. |
| Linear detrend | Full-trace trend fit uses future values. Confirmed and sufficient to fail current causal claim. |
| Resample to 100 Hz | Applied; exact algorithm/options not specified in inspected methods. Future support unknown; cannot assume causal. |
| Count filtering/normalization | Not listed in documented count preprocessing. Actual HDF5 not inspected; unverified. Protocol adds none. |
| Response removal/tapers | Physical-unit branch only; not selected and not causal as described. |
| HDF5 cache | No local file or cache implementation. Unknown. |
| One-second packet/replay | Proposed only. Causal only if loader/preprocessor cannot inspect future packets and state updates only on arrival. |
| STA/LTA | Proposed rolling windows; no implementation. Causal only if state sees received samples, gaps stay explicit, and emissions wait for arrival. |

## Causal alternative (not yet validated)

Do not use the processed HDF5 counts as the primary input for a causal study. First investigate retrieving the matching original miniSEED for a frozen subset, plus StationXML and bulletin picks. EIDA Italy documents waveform/station services; its policy says most datasets are CC BY 4.0 but terms must be checked per network and some data may be restricted. The exact networks contributing HNZ records, terms, availability, original rate, and matching to release traces remain unverified. Archive access is a candidate route, not proof.

Prefer a frozen native-rate cohort so no resampling is required. If a uniform rate is essential, restrict to a verified rate or design a one-sided causal resampler and test it. Do not use a generic batch resampler.

If filtering/detrending is necessary, select a documented causal EEW recipe or use a separate development cohort; freeze it before evaluation. A stateful one-sided IIR filter is only a candidate. Record coefficients, state, initialization, precision, warm-up and scored start. Compare zero-state initialization (with predeclared settling exclusion) with a fixed contiguous pre-event warm-up; choose based on independent evidence and transient checks. Do not assume steady-state initialization is valid without checking its stationarity assumption.

Carry state unchanged across packet boundaries. On a gap, never zero-fill/interpolate. If reset is selected, reset both filter and detector and suppress results until a fixed contiguous rewarm interval completes. Record the gap and recovery. Delayed packets are unavailable until arrival; reordering needs a separate buffering policy and is outside the current draft.

## Required causality tests

These are specifications only; no tests are implemented or run.

1. **Future counterfactual:** process x through sample k. Create x2 identical through k but change only later samples (offset, ramp, impulse, random tail). Fresh replay must produce identical preprocessing outputs, detector statistics, decisions and emissions through k (bitwise or under a declared tolerance).
2. **Arrival cutoff:** delay packets after simulated time T and alter their payloads. Logs and outputs with arrival/emission time ≤T must remain unchanged.
3. **Full-chain coverage:** tests must span decoding, trimming, resampling, filtering, normalization, cache, packetizer and detector—not only detector API.
4. **Chunk partition:** one-sample, irregular and declared packet chunks with carried state must yield the same sample-index scores/decisions; only defined emission quantization may vary.
5. **Gap policy:** known gaps create no samples; verify reset, no output through rewarm, then normal operation.
6. **Offline negative control:** alter only future waveform tail before full-window detrend/resampling; show whether the earlier release-path output changes. If so, label it noncausal.
7. **Detector hand check:** manually verify STA/LTA windows, warm-up, trigger/rearm, and no emission before all inputs arrive.

Any preprocessing cache needs raw checksum, parameters, code/version and a causal/noncausal label. Passing a prefix test on pre-detrended data does not establish end-to-end causality.

## Fair comparison separating processing from detector

Use identical raw records, P references, time mapping, detector code/parameters, score windows, packetization, gap policy, no-fault schedule and pre-generated masks in all arms:

| Arm | Input |
|---|---|
| A: causal primary | Original miniSEED delivered incrementally through frozen causal preprocessing. |
| B: offline comparator | Exact INSTANCE processed HDF5 product or reproduced full-window transform, explicitly noncausal. Recover its resampling implementation or call it a release-product comparison. |
| C: optional ablation | Raw native-rate input without detrend/resample, only if rates/detector assumptions support it; not presumed scientifically valid. |

Keep detector parameters fixed across arms; processing is the changed factor. Pair trigger latency, miss-by-horizon and selected-noise-window counts per trace. For fault interaction, reuse masks across arms and predeclare the interaction; do not tune chunk size or thresholds after seeing outcomes.

## Evidence

- Michelini et al. (2021), *INSTANCE – the Italian seismic dataset for machine learning*, methods §§2.1.2–2.1.6 and 2.2–2.3: [DOI 10.5194/essd-13-5509-2021](https://doi.org/10.5194/essd-13-5509-2021). Checked 2026-10-26.
- Official [INSTANCE release page](https://www.pi.ingv.it/banche-dati/instance/). Checked 2026-10-26.
- [EIDA Italy data policy](https://eida.ingv.it/en/datapolicy) and [waveform access](https://www.eida.ingv.it/en/getdata). Checked 2026-10-26.

