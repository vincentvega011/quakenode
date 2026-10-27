# Results: pre-registered INSTANCE detrend/cast reproduction check

Research prototype, not an operational warning system. Protocol, sample, exclusions, criteria and decision rule are exactly those in `docs/preregistration_detrend_check.md` (commit `9057ac0731ad6f0bac2f155dffc4064dd2242b5c`, committed before the script was run). The script is `scripts/run_detrend_check.py`, run at repository commit `36ed2071e43aa24cd8515b69ee3305744dbae580` (working tree clean, `git_dirty = false`) on Python 3.11. Per-trace CSV, summary JSON, request log (URL, HTTP status, bytes, sha256 of every request) and manifest are under `data/instance_sample/detrend_check/` and `data/raw/detrend_check/` (not committed). Seed 20261101. Sample list sha256: `8a436d78e5699b33396c2cf4d985d84316f3f3c133b1c71bf0c756656724ae9e`. Summary `results_sha256`: `3f64857a8f7d027fd86e3a9f228dab838ebdb513fde6d376cb1cb522cb87b703`. Dataset hashes: events CSV `7ab05e91...`, events counts HDF5 `29fc51fc...` (full values in `docs/instance_access.md`).

## Sample and exclusions

200 traces were drawn (100 IV/HH, 100 IV/HN, channel Z; the 11 earlier-inspected traces excluded from the pool). No replacements. Exclusions are applied in the pre-registered order:

| reason | count | detail |
|---|---|---|
| `fetch_failed` | 73 | all 73 are HTTP 204 (empty body, no error): 20 HH, 53 HN. Stations: 68 start with `T1`, 5 with `T0` (these look like temporary-deployment station codes; that is a reading of the codes, not verified) |
| `native_rate_not_100hz` | 38 | all HN, all raw 200 Hz; 20 distinct stations (not compared; listed in the summary JSON) |
| `gaps_or_overlaps` | 1 | `11054551.IV.TERO..HN` (more than one trace in the response) |
| `raw_does_not_cover_window` | 0 | |
| `hdf5_all_zero` | 0 | |
| **comparable** | **88** | **80 HH, 8 HN** |

So the confirmatory comparison is essentially an HH comparison. Only 8 HN traces were comparable: 53 HN requests returned nothing, and 38 HN traces were archived at 200 Hz while the release is 100 Hz.

Alignment (nearest raw sample, lag 0): the best lag within +-2 samples was 0 for all 88 comparable traces (0% nonzero; the pre-registered lag finding was **not** triggered).

## Success criteria (counts, proportion, Wilson 95% interval)

"Reproduces" = max abs residual <= 1 count. Residual = HDF5 minus the cast transform output.

| variant | pooled | HH | HN |
|---|---|---|---|
| T1-floor | 0/88 (0.0%; 0.0% to 4.2%) | 0/80 (0.0%; 0.0% to 4.6%) | 0/8 (0.0%; 0.0% to 32.4%) |
| T1-rint | 2/88 (2.3%; 0.6% to 7.9%) | 0/80 (0.0%; 0.0% to 4.6%) | 2/8 (25.0%; 7.1% to 59.1%) |
| T1-trunc | 84/88 (95.5%; 88.9% to 98.2%) | 77/80 (96.2%; 89.5% to 98.7%) | 7/8 (87.5%; 52.9% to 97.8%) |
| T2-floor | 2/88 (2.3%; 0.6% to 7.9%) | 0/80 (0.0%; 0.0% to 4.6%) | 2/8 (25.0%; 7.1% to 59.1%) |
| T2-rint | 2/88 (2.3%; 0.6% to 7.9%) | 0/80 (0.0%; 0.0% to 4.6%) | 2/8 (25.0%; 7.1% to 59.1%) |
| T2-trunc | 9/88 (10.2%; 5.5% to 18.3%) | 5/80 (6.2%; 2.7% to 13.8%) | 4/8 (50.0%; 21.5% to 78.5%) |

"Approximately explains" = max abs <= 2 and RMS <= 1.5 (95% needed):

| variant | pooled | HH | HN |
|---|---|---|---|
| T1-floor | 84/88 (95.5%; 88.9% to 98.2%) | 77/80 (96.2%; 89.5% to 98.7%) | 7/8 (87.5%; 52.9% to 97.8%) |
| T1-rint | 88/88 (100.0%; 95.8% to 100.0%) | 80/80 (100.0%; 95.4% to 100.0%) | 8/8 (100.0%; 67.6% to 100.0%) |
| T1-trunc | 88/88 (100.0%; 95.8% to 100.0%) | 80/80 (100.0%; 95.4% to 100.0%) | 8/8 (100.0%; 67.6% to 100.0%) |
| T2-floor | 10/88 (11.4%; 6.3% to 19.7%) | 6/80 (7.5%; 3.5% to 15.4%) | 4/8 (50.0%; 21.5% to 78.5%) |
| T2-rint | 10/88 (11.4%; 6.3% to 19.7%) | 6/80 (7.5%; 3.5% to 15.4%) | 4/8 (50.0%; 21.5% to 78.5%) |
| T2-trunc | 13/88 (14.8%; 8.8% to 23.7%) | 9/80 (11.2%; 6.0% to 20.0%) | 4/8 (50.0%; 21.5% to 78.5%) |

Descriptive only, exact reproduction (max abs = 0):

| variant | pooled | HH | HN |
|---|---|---|---|
| T1-floor | 0/88 (0.0%; 0.0% to 4.2%) | 0/80 (0.0%; 0.0% to 4.6%) | 0/8 (0.0%; 0.0% to 32.4%) |
| T1-rint | 0/88 (0.0%; 0.0% to 4.2%) | 0/80 (0.0%; 0.0% to 4.6%) | 0/8 (0.0%; 0.0% to 32.4%) |
| T1-trunc | 0/88 (0.0%; 0.0% to 4.2%) | 0/80 (0.0%; 0.0% to 4.6%) | 0/8 (0.0%; 0.0% to 32.4%) |
| T2-floor | 0/88 (0.0%; 0.0% to 4.2%) | 0/80 (0.0%; 0.0% to 4.6%) | 0/8 (0.0%; 0.0% to 32.4%) |
| T2-rint | 0/88 (0.0%; 0.0% to 4.2%) | 0/80 (0.0%; 0.0% to 4.6%) | 0/8 (0.0%; 0.0% to 32.4%) |
| T2-trunc | 0/88 (0.0%; 0.0% to 4.2%) | 0/80 (0.0%; 0.0% to 4.6%) | 0/8 (0.0%; 0.0% to 32.4%) |

## Residual distributions (comparable traces; counts)

Pooled (88):

| variant | max abs: median / p90 / p99 / max | RMS: median / p90 / p99 / max |
|---|---|---|
| T1-floor | 2 / 2.0 / 3.0 / 3 | 1.204 / 1.237 / 1.289 / 1.392 |
| T1-rint | 2 / 2.0 / 2.0 / 2 | 0.996 / 1.006 / 1.015 / 1.016 |
| T1-trunc | 1 / 1.0 / 2.0 / 2 | 0.698 / 0.718 / 0.735 / 0.751 |
| T2-floor | 15 / 166.6 / 882.5 / 1823 | 8.072 / 95.395 / 509.587 / 1052.011 |
| T2-rint | 15 / 165.6 / 882.5 / 1823 | 8.072 / 95.392 / 509.586 / 1052.011 |
| T2-trunc | 14.5 / 165.6 / 881.5 / 1822 | 8.022 / 95.237 / 509.203 / 1051.911 |

HH (80):

| variant | max abs: median / p90 / p99 / max | RMS: median / p90 / p99 / max |
|---|---|---|
| T1-floor | 2 / 2.0 / 3.0 / 3 | 1.207 / 1.239 / 1.298 / 1.392 |
| T1-rint | 2 / 2.0 / 2.0 / 2 | 0.997 / 1.006 / 1.015 / 1.016 |
| T1-trunc | 1 / 1.0 / 2.0 / 2 | 0.700 / 0.720 / 0.737 / 0.751 |
| T2-floor | 24 / 203.7 / 969.0 / 1823 | 13.019 / 116.579 / 559.465 / 1052.011 |
| T2-rint | 23.5 / 202.7 / 969.0 / 1823 | 13.018 / 116.575 / 559.464 / 1052.011 |
| T2-trunc | 23 / 202.7 / 968.0 / 1822 | 12.967 / 116.532 / 559.107 / 1051.911 |

HN (8):

| variant | max abs: median / p90 / p99 / max | RMS: median / p90 / p99 / max |
|---|---|---|
| T1-floor | 2 / 2.3 / 2.9 / 3 | 0.962 / 1.063 / 1.111 / 1.116 |
| T1-rint | 2 / 2.0 / 2.0 / 2 | 0.838 / 0.967 / 0.970 / 0.971 |
| T1-trunc | 1 / 1.3 / 1.9 / 2 | 0.501 / 0.587 / 0.620 / 0.624 |
| T2-floor | 3 / 6.3 / 6.9 / 7 | 1.545 / 3.124 / 3.439 / 3.474 |
| T2-rint | 3 / 6.3 / 6.9 / 7 | 1.544 / 3.061 / 3.394 / 3.431 |
| T2-trunc | 2 / 5.3 / 5.9 / 6 | 1.099 / 2.675 / 3.000 / 3.036 |

## Verdict under the pre-declared rules

- **Explains the release** (>= 95% of comparable traces reproduced, max abs <= 1): **T1-trunc only**, 84/88 = 95.5% (Wilson 88.9% to 98.2%). It passes by 0.5 percentage point (one trace fewer would have failed), and the lower interval bound is below 95%.
- **Approximately explains** (>= 95% with max abs <= 2 and RMS <= 1.5): T1-rint 88/88 and T1-trunc 88/88 and T1-floor 84/88. T2 (window mean only) fails everywhere (RMS up to 1052 counts), so the release is not a mean-only removal.
- **Pre-registered decision rule:** because T1-trunc explains the release, the offline arm of the later study *may* be the reproduced transform T1-trunc, labeled as a reproduction of the release.

Caveats that must travel with the verdict (all stated now, none changes the verdict):

1. **No transform reproduces any trace exactly.** The count of traces with max abs = 0 is 0/88 for every variant. "Reproduces" here means within one count, which is the pre-registered tolerance. The best transform leaves a median max abs of 1 and an RMS of about 0.7 counts.
2. **The result is an HH result.** HH: 77/80 (96.2%; 89.5% to 98.7%). HN: 7/8 (87.5%; 52.9% to 97.8%), too few traces to support a statement about HN. Whether the transform holds for the HN family (and for the 200 Hz HN traces, which were resampled in the release) is unknown. The pre-registered pooled rule is met, the family-level rule for HN is not testable with 8 traces.
3. The sample is IV network only, one component (Z), and only traces INGV serves at 100 Hz as a single trace.
4. Because the release is not reproduced bit-for-bit, using the released HDF5 array itself remains the cleanest "release product" arm; the reproduced transform would carry the +-1 count caveat above.

I did not add the transform to the package: a within-one-count, not exact, reproduction on 88 traces seemed too weak to preserve as "the INSTANCE release transform". The tested implementations are in `scripts/run_detrend_check.py` with unit tests.

## EXPLORATORY (not pre-registered; cannot change the verdict)

Code: `scripts/explore_detrend_check.py` (run on the cached data of the 88 comparable traces).

- **E1. Residual structure of T1-trunc.** `HDF5 - trunc(y)` (y = T1 float output) is, for y > 0: 0 on 292,975 samples, -1 on 226,706, +1 on 9,138; for y < 0: 0 on 286,712, +1 on 230,719, -1 on 9,736 (+2 on 14). So the released magnitude is mostly equal to, or one count smaller than, the truncated magnitude, with the same behaviour on both signs. The sign of y is not what separates the two cases.
- **E2. What separates them is the fractional part.** Among samples with |y| >= 2, the share where the released magnitude is one count below `floor(|y|)` is 93% to 85% for frac(|y|) between 0.0 and 0.4, 71% for 0.4 to 0.5, 16% for 0.5 to 0.6, and 3.7% or less above 0.6 (full table in `exploratory.json`). That is a threshold near frac(|y|) = 0.5: `|HDF5| ~ floor(|y| - 0.5) = round(|y|) - 1`. On the earlier single trace the exact relation was `HDF5 = x - sign(x)`.
- **E3. Rule `round(y) - sign(round(y))`.** Checked after seeing E2 (so it is a post-hoc description, not a confirmation): residual max abs 0 on 2/88 traces, <= 1 on 83/88, <= 2 on 88/88; median 747 of 12,000 samples differ per trace and the median RMS is 0.25 counts. That is closer than any pre-registered variant (RMS about 0.7 for T1-trunc) but still not exact, which fits with the exact fit procedure or cast of the authors differing slightly from mine. I do not know why the release would shrink magnitudes by one count after rounding.
- **E4. Who is missing.** 68 of the 73 empty responses are stations whose codes start with `T1` (5 start with `T0`), pointing to temporary-network stations not served by INGV dataselect. All 38 non-100 Hz traces are HN at 200 Hz, spread over 20 stations (for example ATCC 4, NRCA 6, RM33 5, FEMA 3, MURB 3); they share the HN family and several stations, but they are not one network or one station.
