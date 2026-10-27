# One-trace feasibility gate

**Checked:** 2026-10-26  
**Decision: BLOCKED**  
**Scope:** determine whether one INSTANCE waveform can be verified as an authorized pair of original EIDA miniSEED and released sample HDF5. No detector comparison was run.

**Follow-up update (2026-10-26):** an HTTP byte-range prefix exposed the sample-specific event metadata CSV inside the official sample archive. A sample-indexed candidate is now identified, and its corresponding original MN.AQU HHZ interval is available under the network's open access status. The HDF5 trace values were not read or compared. The decision remains blocked at waveform-level alignment; the earlier full-metadata candidate below was later confirmed absent from the sample CSV.

## Decision

The sample-index blocker is partly resolved: a sample-specific CSV is the first event-metadata member in the official archive and was recovered from a supported HTTP range prefix. The archive is 1,777,063,900 bytes; its HDF5 member is a single 1,444,058,504-byte file with no documented per-trace HTTP endpoint or independent sample HDF5 export. The 5 MiB compressed prefix needed to recover the CSV also decompresses into the beginning of the HDF5 member. It is not a clean way to retrieve just the desired HDF5 dataset.

The initial full-metadata candidate (10000541.MN.AQU..HH) is absent from the sample CSV and is excluded. A different candidate, 11032751.MN.AQU..HH, is explicitly present in the sample-specific metadata CSV and the full v3 metadata. Its original MN.AQU HHZ stream was retrieved after checking network status and exact interval availability. Event, station, channel family, sample rate, pick and rounded start metadata agree. However, no HDF5 values were read. The raw stream's first sample after trimming to the nominal window is 3.5 ms before the CSV trace start, which is reported only to 0.01 s; exact waveform alignment and preprocessing effects therefore remain unverified. Do not claim a paired waveform or run detector comparisons.

The test results below concern a synthetic one-pole streaming fixture only. They do not validate INSTANCE preprocessing, MiniSEED-to-HDF5 identity, or detector behavior.

## Initial candidate from full metadata (later confirmed absent from sample)

I downloaded and inspected the official **full v3 event metadata CSV** linked by INGV, not the sample archive. The metadata contains this candidate row:

| Field | Value from row |
|---|---|
| Event identifier | 10000541 |
| Event origin time | 2016-11-16T01:35:56.21Z |
| Network | MN (MedNet) |
| Station | AQU |
| Location | empty; FDSN request spelling is `--` |
| Channel family / metadata station_channels | HH (three-component family) |
| Candidate HDF5 key / trace_name | 10000541.MN.AQU..HH |
| Metadata trace start | 2016-11-16T01:35:48.20Z |
| Metadata sample interval / rate | 0.01 s / 100 Hz |
| Metadata point count | 12,000 |
| P evaluation | manual |
| P uncertainty | 0.1 s |
| P arrival time | 2016-11-16T01:36:05.11Z |
| P arrival sample | 1,691 |
| P time versus metadata start | 16.91 s, consistent with 1,691 samples at 100 Hz |
| Metadata unit field | `trace_deconvolved_units=mps`; this describes the deconvolved-unit metadata and does not itself identify which waveform file was read |
| Source-record identity | Candidate FDSN HHZ stream MN.AQU.--.HHZ; corresponding three-component HH streams are HHE/HHN/HHZ according to station metadata |
| Gap field | No per-trace gap field was present in the inspected row. Gap-free status is therefore unverified from this metadata. |
| Membership in sample archive | **Absent**; the follow-up scan of the sample-specific CSV found zero rows with this trace_name. |

This full-release key was not in the 10,000-row sample metadata CSV. It is not used as the current sample candidate. The full metadata row's count statistics and phase fields do not establish sample inclusion.

## Transfer sizes checked before waveform retrieval

| Resource | HTTP evidence | Size | Action |
|---|---|---:|---|
| Full v3 event metadata CSV, `metadata_Instance_events_v3.csv.bz2` | HEAD returned 200, `Content-Length: 286862604`, `Accept-Ranges: bytes` | 286,862,604 bytes compressed; official page lists 275 MB compressed / 1.8 GB expanded | Downloaded metadata only to `/tmp` to enumerate a row. SHA-256 recorded below; `bzip2 -tv` reported `ok`. No waveform was in this file. |
| Official sample v3 archive, `Instance_sample_dataset_v3.tar.bz2` | HEAD returned 200, `Content-Length: 1777063900` | 1,777,063,900 bytes compressed; official page lists 2.74 GB expanded | Not downloaded. It contains the sample waveforms and associated metadata; no separately linked sample metadata sidecar was found. |
| Full digital-count event HDF5 | Official release page | 39 GB compressed / 156 GB expanded | Not downloaded or requested. |
| Original EIDA MN.AQU HHZ response | HEAD returned 200 but no Content-Length | Estimated before GET: 12,000 samples × 4 bytes ≈ 48,000 bytes for a 120 s, 100 Hz, 32-bit uncompressed component, plus record headers. This is a planning estimate, not the returned size. | After open-network status and availability were verified, retrieved only HHZ for the candidate interval. Actual response: 15,872 bytes (MiniSEED encoding 10 / Steim-2). |

Checksums for files actually retrieved (both stored outside the workspace):

- Full v3 metadata archive `/tmp/instance_events_metadata_v3.csv.bz2`: SHA-256 `a641977fdcf63096dc9163f0bfd6eef29044a5da23eff9adb3ec41960a18cd4f`.
- Candidate raw waveform `/tmp/instance_MN_AQU_HHZ_20161116.mseed`: SHA-256 `4e44d7cde2f30c0d3f9dec83cb83c7e338f13eca15cb1f9f10152a9904252ce5`.
- No sample HDF5 file was retrieved, so no HDF5 checksum or waveform-to-waveform comparison exists.

The sample archive and metadata file sizes are exactly as observed in HTTP headers on 2026-10-26. The reported transfer bytes for the raw waveform are the actual response body size.

## Source-network terms and access checks

The candidate's network is MN. The official INGV network page reports **Restrizione Dati: open** and says the network is distributed under an open-definition-compliant license. The FDSN MN network record independently describes data access through EIDA/FDSN under an open-definition-compliant license. These sources support open access for research with citation. The page does not identify the specific license name in the text retrieved, so this report does not claim a particular license version or permission to redistribute the original MiniSEED. No raw waveform is committed to the repository; the copy is in `/tmp` only.

The INSTANCE release page states CC BY 4.0 for the dataset. The v3 metadata dataset's CKAN API record reports Creative Commons Attribution. These are release terms and do not replace source-network terms for the original data. Cite both INSTANCE (DOI 10.13127/instance) and the MN network (DOI 10.13127/sd/fbbbtdtd6q) in any later work. Before redistribution, verify the exact license notice applicable to the specific waveform response and obtain a clear reuse/redistribution statement if needed.

No credentials, tokens, or authenticated service were used. No EIDA waveform request was made until the MN network's open restriction status had been checked.

## Metadata-only station and availability checks

INGV station metadata for MN.AQU over the candidate epoch returned HHZ at 100 Hz, with channel epoch 2011-04-13 through 2017-12-31. Its sensor is listed as STRECKEISEN STS-2-120S. The request was limited to station metadata and did not request waveform samples.

INGV availability returned one open HHZ span for 2016-11-16T01:35:48.200000Z through 2016-11-16T01:37:48.200000Z, quality D, 100 Hz, one time span, restriction OPEN. This establishes service availability over the requested interval, not correspondence to INSTANCE's HDF5 values.

The dataselect HEAD response established content type `application/vnd.fdsn.mseed` but did not return a content length. The estimated size was therefore calculated from the metadata sample rate/duration before the GET; the later 15,872-byte actual body was not assumed in advance.

## Retrieved raw response and alignment evidence

The GET requested only the vertical HHZ channel and the nominal 120-second metadata interval, from 2016-11-16T01:35:48.20Z through 2016-11-16T01:37:48.19Z. INGV returned full MiniSEED records overlapping that interval:

- HTTP 200, 15,872 bytes, MiniSEED content type.
- SHA-256: `4e44d7cde2f30c0d3f9dec83cb83c7e338f13eca15cb1f9f10152a9904252ce5`.
- 31 records of 512 bytes each; no byte remainder.
- Parsed record headers identify one stream: MN.AQU, empty location, HHZ, 100 Hz.
- First record start: 2016-11-16T01:35:48.196500Z; last record start: 2016-11-16T01:37:45.596500Z.
- Header sample counts total 12,152; end-exclusive time computed from records is 2016-11-16T01:37:49.716500Z.
- MiniSEED blockette 1000 reports encoding 10 (Steim-2) and 512-byte records. Blockette 1001 reports timing quality 85 and microsecond offset 93 on the first record.
- Sequential record starts were contiguous under the parsed record sample counts; this is a MiniSEED-header check, not a complete decoded waveform gap audit.
- The first sample is 3.5 ms earlier than the metadata start. It is not an integer multiple of the 10 ms sample interval. Full-record delivery also extends beyond the nominal end. Exact trim/alignment cannot be declared without recovering the INSTANCE array and the complete preprocessing/sample-time convention.

The downloaded raw response is therefore a candidate source record, not an accepted matched record. A station code, event time and similar waveform context are not sufficient proof of identity.

## Synthetic software checks

Added [test_streaming_preprocessing_contract.py](../../tests/test_streaming_preprocessing_contract.py). It contains a deliberately small one-pole high-pass recurrence solely as a synthetic stateful example. Its coefficient `alpha=0.91` is arbitrary test data, not a scientific filter choice or INSTANCE parameter.

Command run:

    python3 -m unittest -v tests/test_streaming_preprocessing_contract.py

Output summary: 2 tests ran and passed. The tests check (1) altering only future synthetic samples does not alter earlier outputs and (2) carrying state across uneven chunk boundaries produces the same values and final state as processing the full sequence at once. These tests do not touch the downloaded waveform, decode the sample HDF5, prove end-to-end causality for an application, or validate seismic preprocessing.

No detector was run. No tests for a data adapter, INSTANCE preprocessor, HDF5 alignment, detector settings, or recorded-time mapping exist.

## Commands and requests run

Commands are listed here so that the evidence can be repeated. The metadata and waveform outputs were written to `/tmp`, not into the project tree.

1. Repository/document inspection: `find . -maxdepth 4 -type f -not -name '.DS_Store' -print | sort`; read the current feasibility, causal audit, and draft protocol.
2. Size checks: `curl -sSI -L --max-time 20 URL` for the official v3 metadata and sample archive. The sample URL was `https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2`.
3. Read-only catalog probe: `curl -sS -L --max-time 20 'https://data.ingv.it/api/3/action/package_show?id=471'`; the parent catalog record did not enumerate the trace files. A CKAN search identified record 997, “INSTANCE Events Metadata, version 3”; its package record likewise did not provide the waveform/sample membership list.
4. Metadata retrieval: `curl --fail --location ... 'https://repo.pi.ingv.it/instance/metadata_Instance_events_v3.csv.bz2' -o /tmp/instance_events_metadata_v3.csv.bz2`; then `shasum -a 256 ...`, `bzip2 -tv ...`, and Python `bz2`/`csv` parsing for the header and trace row.
5. Network license/access research: official INGV MN network page, FDSN MN record, EIDA/ORFEUS data page, and official INSTANCE release page.
6. Station metadata request (metadata only): `https://webservices.ingv.it/fdsnws/station/1/query?net=MN&sta=AQU&starttime=2016-11-16T01%3A35%3A48&endtime=2016-11-16T01%3A37%3A49&level=channel&format=text`.
7. Availability request (no waveform samples): `https://webservices.ingv.it/fdsnws/availability/1/extent?network=MN&station=AQU&location=--&channel=HHZ&starttime=2016-11-16T01%3A35%3A48.20&endtime=2016-11-16T01%3A37%3A48.20&format=text`.
8. Size probe: HEAD request to the matching FDSN dataselect query; server returned no Content-Length.
9. One-channel waveform GET, only after the open network status and exact interval availability had been checked: FDSN dataselect for MN.AQU.--.HHZ from 2016-11-16T01:35:48.20Z to 2016-11-16T01:37:48.19Z.
10. MiniSEED header parser: ephemeral Python standard-library script checked fixed headers, record identifiers, sample-rate factors, record continuity and blockette 1000/1001. No parser was added to the repository.
11. Synthetic test run: `python3 -m unittest -v tests/test_streaming_preprocessing_contract.py`.

## Sources consulted

- INGV, official INSTANCE release and download listings: https://www.pi.ingv.it/banche-dati/instance/ — checked 2026-10-26. Page identifies CC BY 4.0, points to the sample archive and lists archive sizes.
- INGV Open Data Portal, INSTANCE dataset record: https://data.ingv.it/en/dataset/471 — checked 2026-10-26. Describes EIDA as the waveform source, preprocessing/resampling, HDF5/CSV formats, and event/noise scope.
- INGV, INSTANCE Events Dataset v1 record: https://data.ingv.it/en/dataset/476 — checked 2026-10-26. Describes three-channel event traces and source archive. The v3 event metadata API record is CKAN id 997.
- Michelini et al. (2021), INSTANCE paper: https://doi.org/10.5194/essd-13-5509-2021 — dataset construction, reviewed picks and preprocessing.
- INGV MedNet network page: https://eida.ingv.it/it/network/MN — search-indexed official page checked 2026-10-26; reports restriction OPEN and an open-definition-compliant license. Direct page retrieval returned 502 in this session.
- FDSN MN network record: https://www.fdsn.org/networks/detail/MN/ — identifies MN/MedNet and the open-definition-compliant license; checked 2026-10-26.
- ORFEUS EIDA overview: https://orfeus-eu.org/data/eida/ — directs users to EIDA policy for attribution, citation and usage; checked 2026-10-26.
- INGV web services directory: https://data.ingv.it/metadata/web_service_ita — official listing for MN FDSN station, availability and dataselect services; checked 2026-10-26.
- Official INSTANCE GitHub README: https://github.com/INGV/instance — confirms sample archive contains 10,000 events and 1,000 noise waveforms with associated metadata and documents the large sample transfer; checked 2026-10-26.

## Remaining limitations and exact blocker

1. The sample archive has no independently linked metadata/index file. Its full archive is 1.78 GB compressed; it was not downloaded to inspect one trace.
2. The selected key comes from the full v3 metadata, not verified sample metadata. Its presence in sample HDF5 is unknown.
3. The original response is a plausible single-component raw record, but exact identity is not established. The trace-start offset, FDSN full-record over-read, absence of released HDF5 samples, and unknown exact resampling/detrend implementation prevent verified alignment.
4. The event metadata row has no per-trace gap field. Parsed record continuity alone does not prove gap-free original data or match the release's gap checks.
5. The MN network is marked open, but the retrieved network page does not state a specific license identifier. Keep the original waveform local and do not redistribute it until the precise terms are clear.
6. No preprocessing comparison, detector comparison, statistical result, or data-dependent synthetic test was run.

Exclusion record: candidate `10000541.MN.AQU..HH` is excluded from any detector or preprocessing outcome denominator because sample HDF5 membership, sample values, and exact alignment have not been verified. It remains a metadata/raw-source candidate only.

**Next evidence needed:** obtain a small, official sample-level index or a one-trace export from the data publisher that identifies the sample HDF5 key and values without transferring the whole sample archive; then verify an exact record/time mapping and recover the release preprocessing details. Until then, this gate remains **BLOCKED**.

## Follow-up evidence: sample-specific index and second candidate

### Artifact and partial-access result

The exact artifact was the official v3 sample URL `https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2`. A HEAD request returned HTTP 200, `Accept-Ranges: bytes`, and `Content-Length: 1777063900`. A request for `Range: bytes=0-5242879` returned HTTP 206 and `Content-Range: bytes 0-5242879/1777063900`.

The range prefix is enough to recover the sample event metadata member, but not because the server exposes a file-level seek API. The archive is a bzip2-compressed tar stream. The first sample metadata file is embedded at the beginning of that stream; decompression is sequential. A local binary search over the already retrieved prefix showed the compressed prefix had to reach 3,476,439 bytes before the complete event CSV payload was emitted; BZip2 block granularity caused output to continue beyond that CSV. The actual 5 MiB request expanded far enough to include the following noise CSV and the start of the HDF5 tar member. It yielded 8,367,760 bytes of the declared HDF5 member before truncation. This partial HDF5 payload is not a complete, readable trace and its contents were not interpreted. No entire archive or complete waveform array was retrieved.

`bzip2 -dc` on the truncated range exited 2 with “Compressed file ends unexpectedly” but emitted recoverable prefix bytes. `tar -tvf` listed:

- `./metadata/metadata_Instance_events_10k.csv` — 12,678,854 bytes;
- `./metadata/metadata_Instance_noise_1k.csv` — 309,808 bytes;
- `./data/Instance_events_counts_10k.hdf5` — declared 1,444,058,504 bytes, but only an incomplete prefix was available.

The sample CSV was extracted from the partial tar stream to `/tmp/instance_sample_metadata_events_10k.csv`. It has 10,000 data rows plus a header and SHA-256 `7ab05e91e1a97278f24ac77818c6c6e6914dfcb8f59920618d5e4dec2b031c8f`. It contains trace-level source, station, timing, reviewed-pick, count-statistic and `trace_name` fields. This proves the listed metadata row belongs to the sample index. By itself it does not prove that a corresponding dataset object is physically present in the HDF5 file.

### Sample-indexed candidate

The previous candidate `10000541.MN.AQU..HH` has no match in this sample CSV. The sample-specific row for the new candidate is:

| Field | Sample CSV value |
|---|---|
| source_id / event identifier | 11032751 |
| event origin time | 2016-12-04T16:23:24.91Z |
| network / station / location | MN / AQU / empty |
| channel family | HH (three components) |
| trace_name / candidate HDF5 dataset key | 11032751.MN.AQU..HH |
| trace start | 2016-12-04T16:23:14.51Z |
| dt / rate / npts | 0.01 s / 100 Hz / 12,000 |
| P evaluation / uncertainty | manual / 1.0 s |
| P arrival / arrival sample | 2016-12-04T16:23:33.50Z / 1,898 |
| field `trace_deconvolved_units` | `mps`; the selected digital-count waveform representation is counts, while this field describes the associated deconvolved units |
| per-trace gap flag | no such field in this row; source gap-free status not established by the row |

The row is also present in the full v3 metadata with identical values for the fields above. The full metadata CSV is not the sample-membership evidence; the sample-specific CSV is.

The paper's Appendix A states that each 3-component waveform is an HDF5 dataset addressed by its `trace_name` from the metadata. The official README states that the sample archive includes associated metadata and waveforms. Together these establish the documented key convention and an indexed sample candidate. They do not substitute for opening `Instance_events_counts_10k.hdf5` and checking that its dataset key exists and its data align with the retrieved source waveform.

### Source network and raw-record check for the new candidate

The raw candidate stream is MN.AQU with empty location and HHZ component; the corresponding three-component family is HHE/HHN/HHZ. The official INGV MN network page reports data restriction `open` and describes an open-definition-compliant license. FDSN independently lists MN as open. The specific license identifier for this record was not obtained; no permission to redistribute the raw waveform is asserted. The original file remains in `/tmp` and is not in the repository.

INGV station metadata for MN.AQU says HHZ was active from 2011-04-13 through 2017-12-31 at 100 Hz, with a STRECKEISEN STS-2-120S sensor. The availability response for 2016-12-04T16:23:14.51Z through 16:25:14.50Z returned one D-quality span at 100 Hz with restriction OPEN. A HEAD request to dataselect returned HTTP 200 and MiniSEED content type but no Content-Length. Before retrieval, an uncompressed 32-bit size estimate was 12,000 × 4 = 48,000 bytes plus record overhead. The actual one-component response was 22,528 bytes.

Raw response `/tmp/instance_sample_candidate_11032751_MN_AQU_HHZ.mseed` SHA-256: `72902f235875b9dbe2c0d7ed26e5a078c43f8ddc1ee4cc2bc2effb3f6bb29cc8`. MiniSEED headers identify MN.AQU, empty location, HHZ, 100 Hz. The service returned whole overlapping records: first starts 2016-12-04T16:23:13.386500Z and the record headers contain 12,138 samples through an end-exclusive time of 16:25:14.766500Z. After selecting the 120-second interval by nearest sample, the first raw sample is 16:23:14.506500Z, 3.5 ms before the metadata time rounded as 16:23:14.51Z. At 100 Hz this is consistent with a rounded timestamp, but the HDF5 samples and preprocessing/resampling path were not inspected, so exact release alignment is unresolved.

The sample CSV's P arrival sample and time are internally consistent with the reported rounded trace start at 100 Hz: 1,898 samples correspond to 18.98 s, while the displayed P time minus displayed trace start is 18.99 s. The P uncertainty is 1.0 s. This is metadata-level consistency, not a waveform sample comparison.

### What is now established and what is not

Established:

- HTTP byte ranges are supported by the official archive server, and a small prefix can recover the sample-specific event metadata CSV without downloading the full archive.
- The old full-v3 candidate 10000541 is absent from sample metadata.
- Sample metadata contains the new trace key 11032751.MN.AQU..HH and reviewed P fields; the key convention is documented in the primary paper.
- The corresponding original source stream is available as a small, open-access MN.AQU HHZ response; network attribution is available and redistribution is not assumed.

Not established:

- The target key is physically present in the HDF5 member (the HDF5 was not opened).
- The HDF5 dataset array is byte/sample-identical to the source after documented trimming, detrending and resampling.
- Exact source-to-release sample origin, transform parameters, gap-free status or component mapping.
- A scientifically defensible offline-versus-causal result. No detector or preprocessing comparison was run.

### Current next action

Ask the data publisher for one of: (a) a sample-HDF5 single-trace export for `11032751.MN.AQU..HH` with provenance and checksum; (b) a documented uncompressed sample HDF5 endpoint or seekable index that permits reading this dataset without downloading the full archive; or (c) confirmation that the sample CSV alone is the authoritative trace manifest and a documented transform/source-time mapping adequate to validate alignment. If no such small, authoritative route is available, keep the data experiment blocked. Do not infer that the partial HDF5 prefix contains this trace.

## Final single-trace retrieval gate (2026-10-26)

### Official release mechanisms checked

The publisher's [INSTANCE release page](https://www.pi.ingv.it/banche-dati/instance/) lists the v3 sample as one 1.7 GB `.tar.bz2` archive (2.74 GB expanded), containing 10,000 event waveforms, 1,000 noise waveforms, and associated metadata. Its listed waveform alternatives are whole HDF5 products (and multipart full-dataset files); it does not list a sample-trace API or one-trace export. The [official INGV/instance repository](https://github.com/INGV/instance) README gives the same archive and demonstrates retrieval by piping the archive into `tar xj`. The repository tree was checked via GitHub API on 2026-10-26: it contains README, notebooks, auxiliary files, and figures, but no sample trace-serving code, manifest API, or archive seek index.

The [INSTANCE paper (Michelini et al., 2021)](https://doi.org/10.5194/essd-13-5509-2021), Appendix A, documents a `data` HDF5 group with one dataset per three-component waveform, addressed by `trace_name` from the metadata. This explains how to look up a trace **inside a locally available HDF5 file**. It does not document an HTTP endpoint, remote HDF5 reader, byte-offset map, or single-trace download for the sample archive.

### Compression and range conclusion

The sample URL's confirmed `Accept-Ranges: bytes` and HTTP 206 responses apply to offsets in the 1,777,063,900-byte **outer bzip2 stream**. The first 5 MiB range can be decompressed from the beginning and parsed as a tar prefix; it includes the target sample CSV and then only the start of the single HDF5 tar member. This is sequential prefix access. A tar member boundary does not create a bzip2 restart point, and an HDF5 dataset key cannot be used as a selector in an HTTP byte-range request. The publisher provides no bzip2 seek table or documented mapping from the requested HDF5 key to a compressed range. Therefore HTTP range support does not make the desired inner HDF5 dataset independently retrievable.

The paper's HDF5 layout could support key-level reads after obtaining/decompressing the HDF5 member, but the sample HDF5 member is listed at 1,444,058,504 bytes uncompressed, nested after metadata in the tar.bz2 archive. The 5 MiB prefix yielded only 8,367,760 bytes of that member. No additional waveform range or full archive was retrieved for this gate. No technically defensible, proportionate single-trace transfer path was found in the publisher's release page, official repository, or paper.

### Candidate key, time-grid discrepancy, and terms

The sample-specific CSV row identifies `trace_name=11032751.MN.AQU..HH`, event `11032751`, network/station/location `MN.AQU.` (empty location), channel family `HH`, `trace_start_time=2016-12-04T16:23:14.51Z`, `trace_dt_s=0.01`, `trace_npts=12000`, manual P pick at CSV time `16:23:33.50Z`, sample index 1898, and 1.0 s pick uncertainty. The primary paper documents the general trace-name key convention, but that convention plus the CSV row is not direct observation of this HDF5 object or its shape.

The retrieved original MiniSEED header stream is MN.AQU.--.HHZ at 100 Hz. After selecting the nominal 120-second interval by nearest sample, its first sample is `2016-12-04T16:23:14.506500Z`, 3.5 ms before the CSV value. The CSV displays start time to 0.01 s, so the offset is compatible with decimal rounding, but the consulted publisher materials do not define this field's rounding rule or the exact HDF5 sample-time origin. The HDF5 values and attributes remain unavailable; consequently no integer-sample alignment, waveform identity, or exact source-to-release transformation can be established. No time shift or rounding correction has been applied.

The INSTANCE release page and repository state CC BY 4.0 for the released dataset. The original MedNet/EIDA waveform is a separate source record. The [FDSN MN network record](https://www.fdsn.org/networks/detail/MN/) and INGV network information label the network open/open-definition compliant, but the exact license instrument applicable to this response and redistribution permission remain unresolved. The source MiniSEED remains outside the repository; neither waveform is being redistributed here.

### Gate result

- **Sample-level index membership:** established for the CSV row, not verified against the physical HDF5 key.
- **Official one-trace/sample HDF5 retrieval:** not found.
- **Archive seekability for this key:** not supported by the documented access methods; available ranges address the outer sequential compressed archive.
- **3.5 ms alignment:** plausibly attributable to displayed timestamp precision, but not resolved by a documented rounding convention or observed HDF5 time grid.
- **Legal source-to-release pairing:** not established; source waveform redistribution terms are still unclear and waveform identity is unverified.
- **Detector or preprocessing comparison:** not run.

The smallest next action is a request to the INSTANCE data publisher for a one-trace export or a key-addressable/seekable sample HDF5 route, including the exported dataset checksum, component order, exact time origin, and confirmation of source-data reuse terms. Until supplied and independently checked, the raw MiniSEED and indexed sample row must remain an unmatched candidate.

**BLOCKED** — no publisher-supported or technically defensible single-trace retrieval route was found, so the HDF5 values and exact alignment remain unverified; source-waveform redistribution terms are also unresolved.
