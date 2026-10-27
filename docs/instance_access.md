# INSTANCE sample access and pairing inspection

Research prototype, not an operational warning system. This note is **data inspection only**: no detector, filter or preprocessing comparison was run on real data, and nothing was tuned. Waveforms are not in the repository (`data/` is gitignored); only hashes, sizes and aggregate numbers are recorded here.

Date of inspection: 2026-10-26. Python 3.11.17, h5py 3.16.0, obspy 1.5.1, numpy 2.4.6.

## 1. What was done (commands)

```bash
pip install -e ".[dev,data]"                      # data extra = h5py, obspy
curl -sSIL https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2   # headers
shasum -a 256 data/Instance_sample_dataset_v3.tar.bz2
bzip2 -t data/Instance_sample_dataset_v3.tar.bz2  # integrity: OK
tar -tjvf data/Instance_sample_dataset_v3.tar.bz2 # listing
tar -xjf data/Instance_sample_dataset_v3.tar.bz2 -C data/instance_sample
python scripts/inspect_instance_sample.py --out data/instance_sample/inventory.json
python scripts/pair_instance_traces.py --trace 11032751.MN.AQU..HH --out data/instance_sample/pairing_candidate.json
python scripts/pair_instance_traces.py --random-iv 10 --seed 20261026 --out data/instance_sample/pairing_iv10.json
```

The archive was already present in `data/` (placed there by the user); it was not re-downloaded. Its file modification time is 2026-10-26; the actual download date was not recorded and is therefore unknown.

### Archive

| item | value |
|---|---|
| URL | https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2 |
| local size | 1,777,063,900 bytes |
| server `Content-Length` (HEAD, 2026-10-26) | 1,777,063,900 bytes (match); `Last-Modified: Fri, 10 May 2024 17:04:13 GMT`; ETag `"69ebd7dc-6181c86672af4"` |
| sha256 | `e5a2308f46149dc81e8cb1d824346cc8b7c6ef45e8dd82d15f7bbfe4955bb8dc` |
| `bzip2 -t` | OK (complete stream) |

Extracted files (sha256):

| file | bytes | sha256 |
|---|---|---|
| metadata/metadata_Instance_events_10k.csv | 12,678,854 | `7ab05e91e1a97278f24ac77818c6c6e6914dfcb8f59920618d5e4dec2b031c8f` |
| metadata/metadata_Instance_noise_1k.csv | 309,808 | `35b5c2a63649ba39071658aaa277553840a7e91df6cdd907022dc47835c58f82` |
| data/Instance_events_counts_10k.hdf5 | 1,444,058,504 | `29fc51fc7c3d5ecae73a45386979da19d0f624f0f1e1218e1c5f6954750e9fd0` |
| data/Instance_events_gm_10k.hdf5 (ground-motion units; not used) | 1,444,057,200 | `8fe6334f55b1d789868d291f2e42ef50b62f3bb569ea2a279209324f4002ffed` |
| data/Instance_noise_1k.hdf5 | 144,404,872 | `5f5aa4f566fdcc77f225e4d9c1be29f14249294596431f8ce3c6fcebf1878359` |

## 2. Inventory (from `scripts/inspect_instance_sample.py`)

Event metadata CSV: 10,000 rows, 115 columns. Noise CSV: 1,000 rows. All `trace_name` values parse as `source_id.NET.STA.LOC.CHANNEL_FAMILY` (LOC may be empty); 0 unparseable.

| quantity | events | noise |
|---|---|---|
| rows / unique `trace_name` | 10,000 / 10,000 | 1,000 / 1,000 |
| `trace_dt_s` | 0.01 (100 Hz) for all rows | 0.01 for all rows |
| `trace_npts` | 12,000 (120 s) for all rows | 12,000 for all rows |
| channel family (last `trace_name` field) | HH 3,893; HN 3,550; EH 2,517; HL 40 | HH 501; HN 299; EH 195; HL 4; EN 1 |
| distinct stations (net, sta) | 363 | 428 |
| networks | IV 9,697; MN 106; GU 72; OX 42; XO 24; SI 19; NI 13; BA 4; IX 8; ST 8; TV 3; HL 2; OT 1; RF 1 | IV 788; MN 64; OX 39; GU 33; ST 15; IX 10; OT 10; NI 8; 3A 5; AC 4; HL 4; SI 4; TV 4; XO 4; BA 3; ZM 3; YD 2 |
| `trace_eval_P` | `manual` for all 10,000 (this is the only value present) | column absent |
| rows with `trace_P_arrival_sample` | 10,000 (range 1457 to 6701) | 0 (column absent) |
| `trace_deconvolved_units` | mps 6,410 (= HH + EH); mps2 3,590 (= HN + HL) | column absent |
| `source_type` | earthquake 9,984; quarry blast 16 | column absent |

Reviewed (manual) P pick by family: HH 3,893; HN 3,550; EH 2,517; HL 40 (all of them). There is no automatic-pick row in this sample, so "manual versus automatic" cannot be examined here.

Gap indicators: the CSV has no data-gap field. `source_gap_deg` is the azimuthal gap of the earthquake location, not a waveform gap. Per-component `trace_{E,N,Z}_spikes` flags exist; 1,030 event rows have a nonzero spike flag on at least one component. No component of any event trace in the HDF5 is all zeros.

Metadata self-consistency of the P pick: `(trace_P_arrival_time - trace_start_time)/dt - trace_P_arrival_sample` is 0 for 7,803 rows, +1 for 2,090 rows and -1 for 107 rows. So the stated P sample and the stated P time differ by one sample (10 ms) in about 22% of rows; which of the two is authoritative is unknown.

Noise partners: the CSVs contain no explicit event-to-noise pairing field, so this is a coincidence count only. Event traces with at least one noise trace at the same network+station: 8,731 of 10,000. With the same network+station+location+family: 7,165 (HH 3,045/3,893; HN 2,175/3,550; EH 1,910/2,517; HL 35/40).

### HDF5

All three files: top-level groups `data` and `data_format`; no file-level, group-level or dataset-level attributes. Events counts file: 10,000 datasets under `data/`, every one `int32`, shape `(3, 12000)`. Noise file: 1,000 datasets, `int32`, `(3, 12000)`. The ground-motion events file is `float32`.

`data_format` (documented inside the files) for the counts and noise files: `component_order = b'ENZ'`, `dimension_order = b'CW'` (channel, window), `unit = b'counts'`, `instrument_response = b'not restituted'`, `measurement = b'velocity/acceleration'`. So row 0 is E, row 1 is N, row 2 is Z **according to the file's own `data_format`**; this is documented, not assumed. (Whether the rows are really the E/N/Z channels of that station was not independently checked, except for Z in the pairing test below.)

Cross-check: every one of the 10,000 event `trace_name` values and every one of the 1,000 noise `trace_name` values exists as a dataset, and there are no HDF5 datasets without a CSV row (0 mismatches either way). `11032751.MN.AQU..HH` exists (`int32`, `(3, 12000)`).

## 3. Candidate pairing test: `11032751.MN.AQU..HH`

Z was read as row index 2 because the file's `component_order` is `ENZ`.

Raw data: INGV FDSN dataselect, `network=MN station=AQU location=-- channel=HHZ`, format miniSEED. Request URL pattern: `https://webservices.ingv.it/fdsnws/dataselect/1/query?network=MN&station=AQU&location=--&channel=HHZ&starttime=...&endtime=...&format=miniseed`. Two downloads were made (the first for 16:23:00 to 16:25:30, the second, by the pairing script, for trace start minus 15 s to start plus 135 s). Both succeeded (HTTP 200). Saved under `data/raw/` (not committed):

| file | bytes | npts | sha256 |
|---|---|---|---|
| MN.AQU..HHZ.2016-12-04T162300_162530.mseed | 28,160 | 15,562 | `2dcb8804aea8ca54b196b749ed9f99f35e3372ff8bd75294876ae88468dee119` |
| 11032751.MN.AQU.HHZ.Z.mseed (pairing script) | 27,648 | 15,280 | `52f347ddfad7a277e49e3930742de553027d672df848562f63d08967d3201ff6` |

The raw traces are single-trace, 100 Hz, STEIM1, `int32`.

Alignment facts:

- Sample rate: raw 100 Hz = 1/`trace_dt_s`. Samples: 12,000 in the HDF5.
- Metadata `trace_start_time` = 2016-12-04T16:23:14.51Z. The raw sample grid starts at 16:22:57.186598Z, so the metadata start is 1732.3402 raw samples after the raw start: the nominal start is not on the raw sample grid, 3.402 ms (0.34 sample) off the nearest sample (index 1732). The metadata time is evidently rounded to 10 ms.
- Best integer lag by normalized cross-correlation (demeaned window, lags -100 to +100): **0 samples**, NCC 0.9999956. Lag ±1 gives 0.8860. No shift was applied anywhere.
- The HDF5 Z values are integers (`int32`), range -2465 to 2592, mean 0.0723, median 0. The raw window (indices 1732 to 13731) has mean 809.079, so the HDF5 values are **not** raw counts but have a baseline removed.

Residuals = HDF5 minus hypothesis, nominal alignment (raw window starting at index 1732), counts. "Full trace" means the mean or line is taken over the whole downloaded trace; the b and c1 numbers therefore depend on the length of the download (shown for the 15,280-sample file, and for the 15,562-sample file in brackets).

| hypothesis | max abs | RMS |
|---|---|---|
| (a) identical to raw | 810.0 | 809.007 |
| (b) raw minus mean of the full downloaded trace | 2.013 [1.972] | 1.418 [1.389] |
| (c1) raw minus least-squares line over the full downloaded trace | 3.614 [3.630] | 1.691 [1.695] |
| (c2) raw minus least-squares line over the exact 12,000-sample window | 1.320 | 1.012 |
| (d) raw minus mean of the exact 12,000-sample window | 1.079 | 1.0015 |

**No hypothesis reproduces the HDF5 values to within float precision.** The best (d, c2) leave residuals of about one count RMS. After rounding or truncating the hypothesis to integers, the residual for (d) is still non-zero for 11,974 samples with rounding (max abs 1) and for 5,947 samples with truncation (max abs 1).

Post-hoc observation on this one trace (not in the pre-listed hypotheses; found by inspecting the integer residual): with `x = raw_window - 809` (809 = floor, round and trunc of the window mean 809.079), `HDF5 - x` is -1 for the 6,027 samples where `x > 0`, +1 for the 5,947 samples where `x < 0` and 0 for the 26 samples where `x = 0`. That is, `HDF5 == x - sign(x)` exactly, for all 12,000 samples (0 mismatches). The signal magnitude is reduced by one count toward zero. I have no explanation for this.

### Replication on other traces (exploratory)

The same script was run on a seeded random sample of 10 IV-network traces (seed 20261026, drawn from the sorted list of IV trace names). Each request took about 2 s and returned 14 to 41 KB (about 21 s total).

| trace | outcome | NCC at nominal (best lag) | RMS / max abs residual: (c2) line over window | RMS: (d) mean over window | post-hoc rule `x - sign(x)` mismatches (floor/round/trunc c) |
|---|---|---|---|---|---|
| 1107931.IV.SALO..HH | ok | 0.50556 (0) | 0.768 / 2.002 | 330.577 | 11990 / 11990 / 11990 |
| 11138771.IV.COR1..EH | ok | 0.9999984 (0) | 1.006 / 1.203 | 1.006 | 11944 / **0** / 11944 |
| 11091901.IV.T1245..HH | empty response from INGV dataselect (station not found in INGV station service either) | - | - | - | - |
| 11251911.IV.PTQR..HH | ok | 0.99552 (0) | 0.997 / 1.675 | 50.855 | 11931 / 11931 / 11932 |
| 11212081.IV.APEC..HH | ok | 0.99977 (0) | 1.050 / 1.547 | 16.521 | 11788 / 11789 / 11788 |
| 11271611.IV.SMA1..EH | ok | 0.9999987 (0) | 1.035 / 1.526 | 1.294 | 7229 / 7252 / 7229 |
| 11069371.IV.CESI..HH | ok | 0.99173 (0) | 0.862 / 1.888 | 142.797 | 11976 / 11976 / 11976 |
| 11032751.IV.GUMA..HN | raw is **200 Hz**, HDF5 is 100 Hz (CSV `trace_dt_s` 0.01) | 0.00197 (-41), not comparable | - | - | - |
| 11211211.IV.T1216..EH | empty response from INGV dataselect | - | - | - | - |
| 11280401.IV.CAMP..HH | ok | 0.99865 (0) | 1.011 / 1.533 | 2.354 | 10337 / 10323 / 10337 |

What this shows, and what it does not:

- For all 7 comparable 100 Hz IV traces, the best integer lag is 0 and (c2) removing a least-squares line fitted over the exact 120 s window leaves RMS residuals of 0.77 to 1.05 counts (max abs at most 2.0), together with the candidate (RMS 1.012). Removing only the window mean (d) fits well when the trend is small (COR1, SMA1, candidate) and badly otherwise (RMS 16 to 330). So the data are **consistent with** a linear detrend over the full 120 s window followed by an integer cast, to about one to two counts. This is not an exact match, and nothing was fitted beyond the pre-listed hypotheses.
- The post-hoc `x - sign(x)` rule does **not** generalise: it is exact on the candidate (mean-removed) and on COR1 (round), and fails elsewhere (the 7 other traces would need the detrended baseline, which was not tested because that would be guessing beyond the list).
- One trace shows that the HDF5 can be resampled from the archive rate (200 Hz raw, 100 Hz HDF5). This one trace is not enough to say how common that is among HN traces.
- 2 of 10 traces (IV temporary-looking station codes) were not available from INGV dataselect.

## 4. Licences and terms (as stated by the pages, URLs given)

- INSTANCE release page (https://www.pi.ingv.it/banche-dati/instance/): "Creative commons license: Attribution 4.0 International (CC BY 4.0)"; dataset DOI https://doi.org/10.13127/instance; paper doi:10.5194/essd-13-5509-2021.
- EIDA Italy data policy (https://eida.ingv.it/en/datapolicy): "In the majority of cases the data are openly distributed under the Creative Commons Attribution 4.0 International (CC BY 4.0)"; "In case the explicit statement on the license is still missing you usually can assume it to be the CC BY 4.0 license"; cite datasets by DOI.
- INGV FDSN station service (`https://webservices.ingv.it/fdsnws/station/1/query?network=MN&level=network&format=xml`, queried 2026-10-26): network MN "Mediterranean Very Broadband Seismographic Network", `restrictedStatus="open"`, DOI `10.13127/sd/fbbbtdtd6q`. The same query for IV: "Italian Seismic Network", `restrictedStatus="open"`, DOI `10.13127/sd/x0fxnh7qfy`.
- Not checked: network-specific pages for each of the other 12 networks in the sample, and the exact citation text required by each.

## 5. Proven versus unknown

Proven (this session, with the numbers above):

- The archive is complete and its hash is recorded; metadata and HDF5 agree key-for-key; all traces are 3 x 12,000 `int32` at 100 Hz with `component_order` ENZ stored in the file.
- Every event pick in the sample is labelled `manual`; HN is 3,550 of 10,000 traces.
- For `11032751.MN.AQU..HH`, the raw INGV Z trace has the same sample rate and aligns at lag 0, but the HDF5 values are baseline-removed and match no pre-listed hypothesis exactly (RMS residual about 1 count under (d) and (c2)).
- Across 7 further 100 Hz traces, subtracting a window-wide least-squares line leaves about 1 count RMS residual.

Unknown / not established:

- The exact INSTANCE processing (detrend type, integer cast rule, any taper or resampling). The INSTANCE paper's preprocessing description was not consulted for this note.
- Why `HDF5 == x - sign(x)` holds for the candidate, and whether it is a coincidence.
- Which of the stated P sample or P time is authoritative (they differ by one sample in about 22% of rows).
- How often HN traces were resampled (one example only), and why two stations were not available at INGV.
- Licence terms for networks other than MN and IV.
- Whether a channel-family choice (HN versus HH) is scientifically better for the Phase 1 question; only the counts are known.

## 6. Verdict on pairing HDF5 with raw miniSEED at scale

Technically feasible and cheap: one request per trace, about 2 s and 14 to 41 KB each, so a few hundred traces take minutes. Matching key is `NET.STA.LOC.CHANNEL_FAMILY+Z` and a time window around `trace_start_time` (the metadata start is rounded to 10 ms, so the raw sample grid may be offset by a sub-sample; use the raw sample times, report the offset). IV is 97% of the sample and is served by INGV dataselect; the other networks would need EIDA (federated) and were not tested.

Limits seen in the 10-trace probe: 8 of 10 returned data; 1 of the 8 returned a different sampling rate (200 Hz vs 100 Hz); the HDF5 is not raw counts (a baseline has been removed over the 120 s window, to within about 1 to 2 counts), so an exact bit-level pairing is not possible and any use needs a stated tolerance. For the Phase 1 question (released full-window detrended counts versus causal processing of the same raw waveform) the probe is consistent with the released product being a full-window linear detrend of the raw counts, but the evidence is 8 traces and a residual of about 1 count; it should not be presented as established until the cast and resampling behaviour are understood. Selecting traces for a real comparison should require: data available, same sampling rate, lag-0 NCC above a threshold fixed in advance, and no gaps (single miniSEED trace in the response).
