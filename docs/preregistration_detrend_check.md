# Pre-registration: is the released INSTANCE Z array a reproducible transform of the INGV miniSEED?

Research prototype, not an operational warning system. **This file is committed before any code for the check is run.** Its commit hash is recorded in the results manifest. Anything not declared here is EXPLORATORY and cannot change the verdict.

## Context and honesty note

The candidate transforms below were suggested by an earlier exploratory probe (`docs/instance_access.md`) of 11 traces: the candidate `11032751.MN.AQU..HH` and 10 seeded IV traces. Those 11 traces are **excluded from the confirmatory pool** so that the confirmatory sample is fresh:

```
11032751.MN.AQU..HH
1107931.IV.SALO..HH  11138771.IV.COR1..EH  11091901.IV.T1245..HH  11251911.IV.PTQR..HH
11212081.IV.APEC..HH  11271611.IV.SMA1..EH  11069371.IV.CESI..HH  11032751.IV.GUMA..HN
11211211.IV.T1216..EH  11280401.IV.CAMP..HH
```

Documented preprocessing (`docs/instance_preprocessing_facts.md`): trim to the nearest sample to the start time, 120 s window, removal of mean and linear trends, resampling at 100 Hz. The integer cast and the detrend span are not documented.

## Question

Does the released INSTANCE Z-component HDF5 array (`data/Instance_events_counts_10k.hdf5`, row 2 of each `(3, 12000)` dataset; the file's `component_order` is `ENZ`) equal a reproducible transform of the original INGV miniSEED?

## Candidate transforms (the only confirmatory ones)

Let `w` be the raw 12,000-sample window as float64, and `i = 0..11999`.

- **T1**: `y = w - L(i)`, where `L` is the least-squares line `np.polyfit(i, w, 1)` over the exact 12,000-sample window.
- **T2**: `y = w - mean(w)` over the exact window.

Each is followed by one of three casts to integer: `rint` (round half to even), `trunc` (toward zero), `floor`. That makes **six variants**: T1-rint, T1-trunc, T1-floor, T2-rint, T2-trunc, T2-floor.

**T3 (literal reading of the authors' steps) is omitted.** The documented steps reduce to T1 (mean and linear trend removal over the window is a least-squares line removal) followed by an undocumented cast, and resampling to 100 Hz is a no-op on 100 Hz data. A separate T3 would not differ from T1's cast variants.

## Sample

- Source: the event metadata CSV `metadata_Instance_events_10k.csv` (sha256 `7ab05e91e1a97278f24ac77818c6c6e6914dfcb8f59920618d5e4dec2b031c8f`).
- Pool: rows with network `IV` and channel family `HH`, and separately `IV` with `HN`, minus the 11 traces above. Channel requested: family + `Z` (`HHZ`, `HNZ`).
- Draw: for each family, sort the pool by `trace_name` (plain string sort), then `random.Random(20261101).sample(sorted_pool, 100)` (a fresh generator per family). So **100 HH + 100 HN** traces, 200 in total. The drawn names and their sha256 are saved with the results.
- If a trace is excluded, it is **not replaced**; exclusions are counted and listed.

## Raw data

INGV FDSN dataselect, `https://webservices.ingv.it/fdsnws/dataselect/1/query`, parameters `network=IV`, `station`, `location` (from the trace name, `--` if empty), `channel` (family + `Z`), `starttime = trace_start_time - 15 s`, `endtime = trace_start_time + 120 s + 15 s`, `format=miniseed`. Requests are sequential, one second apart, and cached on disk with sha256 and URL logged.

## Pre-declared exclusions (each counted, each trace listed with its reason; checked in this order)

1. `fetch_failed`: INGV returns an empty body or an error.
2. `native_rate_not_100hz`: the raw sampling rate is not 100 Hz. These are reported separately (counts and stations) and **not compared**.
3. `gaps_or_overlaps`: the response contains more than one trace (gap or overlap) after reading with ObsPy, with no merging.
4. `raw_does_not_cover_window`: the raw trace does not cover the 12,000 samples starting at the aligned index.
5. `hdf5_all_zero`: the HDF5 Z array is all zeros.

All remaining traces are **comparable**.

## Alignment

The window starts at the raw sample nearest to `trace_start_time` on the raw sample grid: `k0 = round((trace_start_time - raw_start) / 0.01)`. No shifting. The comparison is at lag 0. For information only, the best lag within +-2 samples by normalized cross-correlation (demeaned) is reported per trace. **Pre-registered rule:** if the best lag is nonzero for more than 5% of comparable traces, that is reported as a finding; the check is **not** re-run with shifts as a confirmatory analysis.

## Residual and success criteria (fixed now)

Residual `r = hdf5 - cast(T(w))` (integer counts), per trace: `max|r|` and `RMS(r)`.

- A variant **reproduces** a trace if `max|r| <= 1`.
- A variant **explains the release** if it reproduces **>= 95%** of the comparable traces (pooled over both families).
- A variant **approximately explains** the release if **>= 95%** of comparable traces have `max|r| <= 2` and `RMS(r) <= 1.5`.
- Proportions are reported with Wilson 95% intervals, per family and pooled, for every variant. The decision uses the point proportions; the intervals are for reporting.
- If several variants explain the release, all are reported; the one with the most traces at `max|r| = 0` is preferred, ties broken by the listing order above.
- Descriptive only (not a criterion): the number of traces with `max|r| = 0`.
- If a variant explains the release pooled but not within one family, that is stated as a caveat in the verdict.

## Decision rule (recorded in advance)

- If a variant **explains the release**, the offline arm of the later study may be that reproduced transform, labeled as a reproduction of the release.
- Otherwise (including "approximately explains" only), the offline arm must be the **released HDF5 array itself**, labeled as the release product, with the residual caveat.

## Reproduction details

Script: `scripts/run_detrend_check.py`. Outputs (not committed): a per-trace CSV and a summary JSON under `data/instance_sample/`, a request/sha256 log, and a manifest including this file's commit hash, the repository commit, the sha256 of the CSV and HDF5, and the seed. The results are written up in `docs/detrend_check_results.md`. Any additional analysis goes in a section labeled EXPLORATORY.
