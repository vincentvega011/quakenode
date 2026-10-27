# INSTANCE sample index blocker review

**Review date:** 2026-10-26  
**Scope:** determine whether the sample-specific index and HTTP partial access permit one defensible source-to-HDF5 waveform match without downloading the full sample archive. No detector comparisons were run.

## Finding

The original index blocker is partly resolved. The official v3 sample archive supports HTTP byte ranges, and its first compressed-tar members include a sample-specific 10,000-row event metadata CSV. A small prefix range recovered that CSV, so sample membership can be checked without retrieving the 1.78 GB archive. The prior full-metadata candidate `10000541.MN.AQU..HH` is **not** in this sample CSV. A different candidate, `11032751.MN.AQU..HH`, is in it and has a manually reviewed P pick.

The data-pair blocker remains. The sample metadata CSV and INSTANCE paper document the `trace_name`-to-HDF5-dataset relation, but the target HDF5 dataset was not opened or read. The only exposed HDF5 artifact is a single 1,444,058,504-byte HDF5 member nested in the sequentially compressed archive. The tested HTTP ranges address the compressed archive stream, not a particular HDF5 dataset. The prefix sufficient to recover metadata also decompresses into the beginning of this HDF5 member. I found no official sample HDF5 per-trace endpoint or documented random-access index. Therefore there is a sample-indexed source candidate, but not a verified raw-to-HDF5 waveform pair.

## Artifacts and endpoints investigated

| Artifact or endpoint | What it proves | What it does not prove |
|---|---|---|
| Official sample archive: `https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2` | HTTP HEAD returned `Accept-Ranges: bytes`, total length 1,777,063,900 bytes, content type `application/x-bzip2`, and an ETag. HTTP range requests returned 206 with correct `Content-Range`. The first archive members can be recovered from a prefix. | `Accept-Ranges` is not a per-file seek API. It does not support a request for an HDF5 key or an inner archive member by name. |
| Sample prefix `Range: bytes=0-5242879` | The decompressed prefix lists `metadata_Instance_events_10k.csv`, `metadata_Instance_noise_1k.csv`, and then the HDF5 member header. Extracted event CSV has exactly 10,000 data rows plus header. | It does not provide the complete HDF5 member or tell us which physical HDF5 datasets exist beyond the documented metadata convention. |
| Extracted `metadata_Instance_events_10k.csv` | Direct sample-specific metadata evidence. It has `trace_name`, event/station identity, trace start, dt/npts, P evaluation/time/sample, and other fields. Candidate 11032751 appears here; candidate 10000541 does not. | CSV presence is not direct observation of a matching HDF5 dataset or sample values. |
| Full metadata v3 file `https://repo.pi.ingv.it/instance/metadata_Instance_events_v3.csv.bz2` | The chosen sample candidate also appears in the full release metadata with consistent key fields. | The full metadata file alone cannot establish sample membership; it also includes records absent from the sample. |
| INSTANCE paper Appendix A, https://doi.org/10.5194/essd-13-5509-2021 | States each three-component waveform is a separate HDF5 dataset accessed by its metadata `trace_name`. | It does not document a remote per-key extraction endpoint for the sample archive, nor does it prove that this particular key's dataset was read. |
| Official INGV INSTANCE README, https://github.com/INGV/instance | States the sample includes 10,000 events and 1,000 noise waveforms with associated metadata; documents the full sample archive size and sample workflow. | It does not provide a separate sample CSV download or an HDF5 trace-level API. |
| INGV MN network page and FDSN MN record | MN/MedNet is marked open; official descriptions state distribution under an open-definition-compliant license. FDSN query service and interval availability are operational. | The retrieved text does not name a specific license identifier. “Open” is not treated as permission to redistribute the source waveform. |

## HTTP range and archive test

The sample endpoint's HEAD response was:

- HTTP 200;
- `Accept-Ranges: bytes`;
- `Content-Length: 1777063900`;
- `Content-Type: application/x-bzip2`;
- ETag `"69ebd7dc-6181c86672af4"`.

First range probe, `Range: bytes=0-1048575`, returned HTTP 206, 1,048,576 bytes, and `Content-Range: bytes 0-1048575/1777063900`. Its bytes begin with the bzip2 `BZh9` signature. Truncated decompression emitted a partial tar listing, but not the complete metadata member.

Second probe, `Range: bytes=0-5242879`, returned HTTP 206, 5,242,880 bytes, and `Content-Range: bytes 0-5242879/1777063900`. `bzip2 -dc` exited 2 because the stream prefix is incomplete but emitted a partial tar. `tar -tvf` exposed:

- `./metadata/metadata_Instance_events_10k.csv`, declared size 12,678,854 bytes;
- `./metadata/metadata_Instance_noise_1k.csv`, declared size 309,808 bytes;
- `./data/Instance_events_counts_10k.hdf5`, declared size 1,444,058,504 bytes.

The event CSV was extracted from the partial tar to `/tmp/instance_sample_metadata_events_10k.csv`; it contains 10,001 lines including header and SHA-256 `7ab05e91e1a97278f24ac77818c6c6e6914dfcb8f59920618d5e4dec2b031c8f`. The archive's metadata precedes waveform data, but the five-megabyte prefix crossed into the HDF5 member. Tar reported that only 8,367,760 bytes of the HDF5 member were available before the compressed prefix ended. This is an incomplete HDF5 payload; it was not treated as a trace and was not inspected as waveform data. No full sample or HDF5 file was downloaded.

The bzip2-compressed tar is sequential. The server's range support can retrieve arbitrary compressed byte offsets, but a range starting at an arbitrary offset is not a documented way to decompress or seek to an inner tar/HDF5 dataset. No archive index for such seeking was found in the official documentation. In particular, no documented way was found to fetch one HDF5 dataset by `trace_name` from this archive.

## Candidate membership and source record

### Excluded initial candidate

The former full-metadata key `10000541.MN.AQU..HH` was searched in all 10,000 event rows of the extracted sample CSV. Result: **zero matches**. It cannot serve as the sample trace for this experiment.

### New sample-indexed candidate

The sample-specific CSV has one row for `11032751.MN.AQU..HH`. Its fields are:

| Field | Value |
|---|---|
| Event ID / origin time | 11032751 / 2016-12-04T16:23:24.91Z |
| Network, station, location | MN, AQU, empty |
| Channel family | HH, three-component |
| `trace_name` | `11032751.MN.AQU..HH` |
| Trace start, dt, npts | 2016-12-04T16:23:14.51Z, 0.01 s, 12,000 |
| Rate | 100 Hz |
| P-pick provenance | `manual` |
| P uncertainty | 1.0 s |
| P arrival / sample | 2016-12-04T16:23:33.50Z / 1,898 |
| Gap indicator | None in this row; gap-free source status is unknown |
| Unit field | `trace_deconvolved_units=mps`; it is not a substitute for identifying the selected count-HDF5 array |

The same key and values are present in full event metadata v3. The sample CSV is the evidence that this record was selected into the sample metadata. The INSTANCE paper says `trace_name` is the key for a separate HDF5 dataset for each three-component waveform. That is strong documented membership evidence, but the actual HDF5 dataset was not opened to verify physical presence or dimensions.

### Network terms and original miniSEED

Official INGV MedNet metadata identifies MN as open and says the network distributes data under an open-definition-compliant license; the FDSN MN record agrees. The exact license identifier was not obtained. This supports the small research access request, with attribution; it does **not** establish redistribution rights for the raw waveform. The original response remains in `/tmp` and is not committed or redistributed. Cite the MedNet dataset DOI `10.13127/sd/fbbbtdtd6q` and INSTANCE DOI `10.13127/instance` in any later study; re-check exact applicable terms before sharing source data.

Metadata-only station query found MN.AQU HHZ at 100 Hz during the event epoch. INGV availability reports one D-quality HHZ span at 100 Hz and `Restriction OPEN` for the requested 120 s interval. A dataselect HEAD returned HTTP 200 and MiniSEED content type, but no `Content-Length`. Before GET, a single 100 Hz, 120 s, 32-bit component was estimated at about 48,000 bytes plus MiniSEED headers. The actual one-component response was 22,528 bytes.

Raw file: `/tmp/instance_sample_candidate_11032751_MN_AQU_HHZ.mseed`  
SHA-256: `72902f235875b9dbe2c0d7ed26e5a078c43f8ddc1ee4cc2bc2effb3f6bb29cc8`

MiniSEED fixed headers identify MN.AQU, empty location, HHZ, 100 Hz. The service returned whole overlapping records: 44 records of 512 bytes, with 12,138 samples total. First record time is 2016-12-04T16:23:13.386500Z; computed end-exclusive time is 16:25:14.766500Z. Restricting to the nominal 120 s window by nearest sample gives first sample at 16:23:14.506500Z, 3.5 ms before the CSV time 16:23:14.51Z. This is consistent with the CSV timestamp being rounded to 10 ms, but it does not prove how the release HDF5 was trimmed/resampled or where its exact sample grid begins.

The displayed P time minus displayed start is 18.99 s; the arrival sample at 100 Hz represents 18.98 s. The 10 ms discrepancy is within the CSV's rounded timestamps and much smaller than the listed 1.0 s pick uncertainty. This metadata-level arithmetic does not substitute for comparing the HDF5 data array.

## What is proven and what remains open

**Proven:**

- The official server accepts byte-range requests.
- A limited prefix retrieves a sample-specific index without transferring the full archive.
- The old candidate is absent from the sample index; the new candidate appears in it.
- The new candidate has a reviewed P pick and a plausible, small original source waveform under the open MN access status.
- Its source metadata and sample metadata agree on event, network, station, channel family, rate, duration, pick and rounded trace start.

**Not proven:**

- The actual sample HDF5 dataset exists at `trace_name=11032751.MN.AQU..HH` or can be read independently of the archive.
- The source HHZ values align to the HDF5 Z component after trimming, detrending and resampling.
- Exact source-to-release sample origin, gap handling, transformation implementation or data integrity.
- A valid offline-versus-causal waveform pair or any detector result.
- A specific redistributable license for original MedNet waveform data.

## Exact commands and requests

Commands used for the archive and index investigation:

    curl -sSI -L --max-time 20 'https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2'
    curl -sS -D /tmp/instance_sample_range.headers -H 'Range: bytes=0-1048575' --max-time 30 'https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2' -o /tmp/instance_sample_range_1MiB.bin
    curl -sS -D /tmp/instance_sample_metadata_range.headers -H 'Range: bytes=0-5242879' --max-time 30 'https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2' -o /tmp/instance_sample_metadata_range_5MiB.bz2
    bzip2 -dc /tmp/instance_sample_metadata_range_5MiB.bz2 > /tmp/instance_sample_metadata_range_5MiB.tar
    tar -tvf /tmp/instance_sample_metadata_range_5MiB.tar
    tar -xOf /tmp/instance_sample_metadata_range_5MiB.tar ./metadata/metadata_Instance_events_10k.csv > /tmp/instance_sample_metadata_events_10k.csv

Sample CSV row checks were performed with Python's standard `csv` module. The candidate row was then queried from the official INGV station, availability and dataselect services; only station/availability metadata were requested before the one-component waveform GET. The raw MiniSEED header was inspected with a small, ephemeral Python standard-library parser. No repository code or synthetic test was changed. No tests were run during this follow-up.

## Sources

- Official INSTANCE release page and sample listing: https://www.pi.ingv.it/banche-dati/instance/ — states sample size, count and CC BY 4.0; checked 2026-10-26.
- Official INGV INSTANCE repository README: https://github.com/INGV/instance — sample contains 10,000 events, 1,000 noise waveforms and associated metadata; gives archive size and sample extraction instructions; checked 2026-10-26.
- Michelini et al. (2021), INSTANCE paper, especially Appendix A and Code/Data availability: https://doi.org/10.5194/essd-13-5509-2021 — HDF5 trace-key convention and data provenance; checked 2026-10-26.
- INSTANCE Open Data Portal event dataset: https://data.ingv.it/en/dataset/476 — event dataset description and source context; checked 2026-10-26.
- Official INGV MedNet network page: https://eida.ingv.it/it/network/MN — restriction open, network description and open-definition-compliant license. Direct page retrieval was intermittent; official page search result was checked 2026-10-26.
- FDSN MN network record: https://www.fdsn.org/networks/detail/MN/ — network identity, access and license description; checked 2026-10-26.
- INGV official web-services directory: https://data.ingv.it/metadata/web_service_ita — lists MedNet FDSN station, availability and dataselect services; checked 2026-10-26.

## Next smallest action

Request from the data publisher a one-trace HDF5 export for `11032751.MN.AQU..HH` with file checksum, component layout and exact sample-time origin, or a documented uncompressed/seekable sample-HDF5 endpoint that returns the dataset by `trace_name`. This would avoid the full archive and permit direct value/alignment comparison. Until such access exists, do not call this a paired trace and do not run detector comparisons.

**BLOCKED** — the sample index and source record are now identified, but the actual sample HDF5 dataset and sample-level alignment remain unverified.

## Final single-trace retrieval review (2026-10-26)

### Artifact and endpoint investigated

The reviewed endpoint is the publisher's `https://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2`, linked from the [official release page](https://www.pi.ingv.it/banche-dati/instance/) and [official INGV/instance repository](https://github.com/INGV/instance). Its previously observed HEAD/range headers establish a 1,777,063,900-byte `application/x-bzip2` object with byte ranges supported. A prefix range was sufficient to parse the sample CSV and the beginning of the next tar member. The sample tar listing declares the HDF5 member `./data/Instance_events_counts_10k.hdf5` at 1,444,058,504 bytes.

The publisher page lists the whole sample archive, while the repository README demonstrates sequential `curl ... | tar xj` extraction. The repository tree contains notebooks and explanatory materials, not a trace export service or index mapping `trace_name` to compressed byte offsets. The 2021 INSTANCE paper, Appendix A ([DOI](https://doi.org/10.5194/essd-13-5509-2021)), says each three-component trace is a separate HDF5 dataset under the `data` group and is selected by `trace_name`. That establishes a local HDF5 lookup convention; it does not establish a remotely addressable dataset endpoint.

### What the access evidence proves

- A small prefix can recover the sample-specific CSV without transferring the full archive.
- `11032751.MN.AQU..HH` is in that CSV, with a manually reviewed P pick.
- The server honors HTTP byte ranges for the outer archive object.
- The archive prefix reaches only the start of the HDF5 tar member; previously recorded decompression yielded 8,367,760 bytes of a 1,444,058,504-byte member, not a complete HDF5 file or trace.

### What it does not prove

- An HTTP range is a compressed-byte interval, not a request for a named tar member or HDF5 dataset. Bzip2/tar prefix extraction is sequential; no publisher-provided seek table, per-trace URL, object API, or sample HDF5 sidecar was found. Arbitrary range support alone cannot map an HDF5 key to independently decodable bytes.
- The target HDF5 key exists physically or that its data can be read from the acquired prefix.
- The source HHZ stream is the released Z component. The source's nearest nominal-window sample begins at `2016-12-04T16:23:14.506500Z`; the CSV reports `2016-12-04T16:23:14.51Z`. A 3.5 ms discrepancy is compatible with rounding to hundredths, but no documented CSV rounding convention or HDF5 time origin was found. It cannot be silently resolved by shifting samples.
- The source waveform can be redistributed under a specific license. The source network is marked open/open-definition compliant, but the exact license applicable to this record remains unidentified. The released INSTANCE sample is stated as CC BY 4.0; that does not by itself license the separate source response.

No complete sample archive, HDF5 member, or additional waveform data were retrieved during this final review. No tests or detector comparisons were run.

### Finding and smallest next action

A verified source-to-release pairing is still not possible within the current constraints. The closest legitimate path is to ask the publisher for a one-trace export or documented key-addressable sample HDF5 access, with checksum, component order, exact sample-time origin, and source provenance/reuse terms. If the publisher cannot provide that, resolving this candidate would require accepting the full sample HDF5/archive transfer, which remains outside the authorized scope. Keep the original source waveform local and do not claim a paired record.

**BLOCKED** — the specific remaining blockers are lack of a documented proportionate way to retrieve the HDF5 dataset, unresolved sample-grid alignment, and unspecified redistribution terms for the original source waveform.
