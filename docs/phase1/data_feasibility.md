# QuakeNode feasibility sprint: data access

**Checked:** 2026-10-26  
**Purpose:** decide whether a small paired offline-versus-causal preprocessing experiment is currently supportable. No waveform files were downloaded.

## Decision summary

There are two credible public access routes, but neither is a verified, ready-to-run matched cohort in this workspace. INSTANCE is the closer fit to the proposed question: its official page advertises a small sample and CC BY 4.0; its paper documents 120-second, reviewed-P event windows that are linearly detrended and resampled before release. That makes the released product a useful offline comparator, but a causal arm needs the corresponding original records and exact sample-time/pick mapping. No HNZ row counts or raw/release matches have been enumerated.

The 2026 EPIC Alaska paper describes a substantial public miniSEED replay suite with station metadata and event catalog context. DataCite metadata for its Zenodo DOI reports CC BY 4.0. However, the paper's cited Zenodo API returned HTTP 500 when checked, and DataCite provides no files, formats, sizes, or detailed description. The paper-level description supports the existence and intended content of the suite; direct retrieval and the exact archive contents remain unverified. EPIC is better suited to replay-level evaluation than to isolating INSTANCE's preprocessing.

**Dataset recommendation:** first attempt a bounded INSTANCE metadata and matching feasibility check, retrieving no waveform until the candidate record, network terms, and transfer size are known. Keep the EPIC suite as a backup if its record becomes inspectable and its stored inputs include the needed raw waveform and precise time mapping. A synthetic fixture is appropriate for software causality tests only.

## Current project baseline and provenance

The current directory is a documentation snapshot, not a working application. It contains context.md; Phase 1 reports, an ADR, a prior-art CSV; and experiments/configs/phase1_protocol.yaml. It has no source code, waveform data, README, license file, dependency manifest, tests, CI, scripts, generated results, or Git metadata. `git status` and `git log` fail because this directory is not a repository. A sibling quake directory has an empty Git repository with no commits or files and therefore does not establish provenance for this workspace. The system Python 3.9.6 is an environment fact, not a supported QuakeNode runtime. No Git repository was initialized and no existing project document was changed in this sprint.

The exact tree at inspection is recorded in the existing [repository reality audit](repository_reality_audit.md). The prior draft config leaves event IDs, data paths, and checksums unset.

## Candidate comparison

| Question | INSTANCE | EPIC Alaska test suite |
|---|---|---|
| Primary source | [Official INSTANCE release page](https://www.pi.ingv.it/banche-dati/instance/) and Michelini et al. 2021, [DOI 10.5194/essd-13-5509-2021](https://doi.org/10.5194/essd-13-5509-2021). | Williamson et al. 2026, [DOI 10.1785/0120260139](https://doi.org/10.1785/0120260139); cited data DOI [10.5281/zenodo.19897535](https://doi.org/10.5281/zenodo.19897535); [DataCite record](https://api.datacite.org/dois/10.5281/zenodo.19897535). |
| Access route | Official release page links downloads for sample/full metadata, HDF5 traces, and StationXML. EIDA is the stated source archive for the contributing waveforms. Page-level access confirmed; actual file transfer not tested. | Paper says the per-event miniSEED and metadata are openly available from the cited Zenodo repository. DOI resolves to DataCite metadata; direct Zenodo record API returned HTTP 500. Actual files and access route not verified in this check. |
| Published files / volume | Official release page: 10,000-event sample plus 1,000 noise waveforms; compressed sample 1.7 GB and expanded 2.74 GB. Full event-count data 39 GB compressed / 156 GB expanded; physical units 151 GB compressed / 156 GB expanded. These are page-listed sizes, not downloaded measurements. | Article says event waveforms are miniSEED converted to Earthworm tank files for EPIC, plus per-event station/network metadata with coordinates, gain, and units. DataCite has empty sizes/formats and no content URL. No volume can be responsibly estimated. |
| License / redistribution | Official page states CC BY 4.0 for the release. Attribute the dataset and cite DOI 10.13127/instance. For the original EIDA records, check each contributing network's terms; EIDA policy is network-dependent and does not replace the release terms. | DataCite reports CC BY 4.0 for DOI 10.5281/zenodo.19897535. Confirm the license on the dataset record/files before retrieval or redistribution. Article-level “openly available” is not a substitute for record inspection. |
| Waveform rawness | Released count HDF5 is processed, not raw. The paper documents removal of mean and linear trends and resampling to 100 Hz on 120 s windows; gapped traces are excluded. The distinct physical-motion branch includes response removal and tapers. The exact detrend/resampling implementation and options were not recovered. Matching original EIDA miniSEED is required for a causal arm. | Article describes collected event waveforms in miniSEED and station metadata with gain/units; this appears suitable as waveform replay input. Whether files are untouched archive samples versus cut/converted records, exact preprocessing, sample rates, and sample-start semantics must be verified from the archive and methods supplement. |
| Labels and denominator | Paper describes a curated cohort of reviewed P picks used in preferred event locations, not a complete unconditional event/station population. Sample advertises 10,000 event traces and 1,000 noise traces overall, but exact HNZ counts, pick fields, metadata join rates, usable matched records, and event counts in any requested subset are unknown. | Article reports 530 Alaska earthquakes from Jan 2010–Feb 2025, M4.5–8.2, and 345 EPIC matches. This is event-cataloged replay data, not evidence of continuous negative time. Usable matched waveform files count and number of station traces per event require archive inspection. |
| Continuous noise / no-event periods | Release advertises 1,000 noise waveforms in its sample, but these are selected snippets, not verified continuous background coverage. Noise labels and duration distribution need metadata inspection. | Alaska test suite is assembled around earthquake events. Continuous no-event intervals are not established by the paper's test-suite description. |
| Small pilot suitability | The sample is small relative to full release but still 1.7 GB compressed. It may be excessive for a tiny initial pilot. A single trace from the official sample may suffice for data-path feasibility, but do not fetch until file-specific size and terms are checked. An event subset can test detector behavior only after raw/release matching. | A single event might be a useful replay pilot if the record exposes per-event files and modest size, but neither file size nor direct access has been confirmed. The paper's full suite is 530 events; full download is not justified for a feasibility check. |
| Suitability for proposed comparison | Best conceptual match because the published full-window transform is explicit and P-picked traces exist. Main unresolved blocker is matching original miniSEED with release HDF5 and timing/pick metadata. | Supports replay and multi-station EPIC behavior. Does not by itself create an offline-versus-causal preprocessing pair or isolate preprocessing effects. |

## INSTANCE evidence and caveats

The official release page gives the collection totals, small sample contents, release sizes, StationXML availability, and CC BY 4.0. It cites DOI 10.13127/instance. The paper's preprocessing methods describe reviewed phase picks and the count-trace workflow: gap exclusion, trimming/windowing to 120 s, mean and linear detrending, 100 Hz resampling, and post hoc quality/SNR information before HDF5 assembly. That description establishes full-window processing but not the exact operation implementation. It also does not show that every sample trace can be joined back to a public original record with an identical start time.

The HNZ channel requirement in the old draft is not yet proven to yield a sufficiently large or representative subset. Do not state a trace count until sample metadata are inspected. Picked traces condition the sample on reviewed detections and location use. They cannot support a system-wide earthquake miss rate, continuous false-trigger rate, or representative warning utility.

EIDA access and use must be checked against the actual contributing network. Official sources: [EIDA data policy](https://eida.ingv.it/en/datapolicy), [EIDA data access](https://www.eida.ingv.it/en/getdata). Policy content was not directly revalidated in this sprint; treat its network-specific implications as a required per-record check. No credentials or private tokens were used.

## EPIC evidence and caveats

The 2026 article says the Alaska test suite contains 530 events with magnitudes 4.5–8.2; events span multiple tectonic settings and station density varies over time. Per-event input uses miniSEED plus station metadata; replay ingests data in simulated real time, and paper results report 345 matched events under catalog location/origin-time/quality criteria. The paper says the suite is openly available at DOI 10.5281/zenodo.19897535.

DataCite API metadata checked on 2026-10-26 reports creator Amy Williamson, dataset title, 2026 issue date, relation to DOI 10.5281/zenodo.19897534, and CC BY 4.0. DataCite lists no file sizes, formats, content URL, or descriptions. A direct request to the Zenodo record API returned HTTP 500 (228-byte error response). No waveform data were retrieved. Therefore the existence and paper-described composition are supported, but archive file listing, download size, data-to-event mapping, and practical retrieval are unresolved.

EPIC's published replay is strong prior art for progressive multistation ingestion and event-level scoring. Its event suite is not automatically a benchmark for preprocessing causality, and an EPIC input format conversion may itself require checking before claiming access to raw records.

## License and redistribution summary

| Material | Evidence | Current status |
|---|---|---|
| INSTANCE sample/HDF5 and metadata | Official release page says CC BY 4.0; DOI 10.13127/instance. | Reuse with attribution appears permitted under the stated release license. Confirm any file-specific notices and attribution text. |
| Original EIDA miniSEED/StationXML | Network-specific EIDA access and policy pages. | Unresolved until exact network codes and data policy are checked. Do not redistribute original records before that check. |
| EPIC Alaska suite | DataCite DOI metadata reports CC BY 4.0; paper says open. | Metadata license is positive evidence, but inspect the archive record and file-level terms before download or redistribution. |
| Synthetic fixture authored for QuakeNode | No seismic source dataset required. | Can be released under a project-selected license once one exists; this workspace currently has no project license file. |

## What metrics data can support

After a matched reviewed-P subset is verified, the experiment can support paired comparisons of sample-prefix processing outputs, fixed-detector statistic/decision changes, and P-relative first trigger timing or miss-by-predeclared horizon **conditional on those selected traces**. It can separately describe behavior on the release's selected noise snippets if their labels and durations are inspected.

Current data evidence does **not** support a system-wide event recall, operational false-alert rate, time-dependent station availability, communication delay/loss effect, target-site shaking threshold, or warning time. Those require continuous station streams including quiet periods, complete event catalogs for the region/time interval, verified station/channel uptime and timing, and target-site observations with a defensible ground-motion threshold and arrival/alert clocks.

## Access plan: metadata first, then one trace

1. For INSTANCE, inspect only the official sample metadata/index and file listing. Record actual transfer size before downloading. Identify one HNZ trace by event/network/station/location/channel, its HDF5 key, start time, sample rate, units, P-pick reference, gap/quality flags, and source network.
2. Check the original EIDA miniSEED metadata request for that record and the network's use terms. First inspect request parameters and expected response size. Do not send credentials in a report or code. If request is authenticated or restricted, stop and record that requirement.
3. Only when the source waveform is a small, authorized transfer, retrieve one event-station record and compare identity, timing, rate, units, channel and pick against the released trace. Save checksums and exact request metadata locally; do not commit data.
4. If exact matching succeeds, enumerate a small fixed cohort and report counts and exclusions before detector evaluation. If it fails, test EPIC metadata/file retrieval at the DOI without fetching the full suite; decide from its actual file list whether one event gives a comparable raw waveform and timing metadata.
5. Keep a synthetic deterministic trace for software tests. Never present it as seismic detector evidence.

## Selection proposal (not yet applied)

For an initial real-data pilot, freeze trace selection using metadata only, before running detectors: one component/channel family with verified original sampling rate and units; reviewed P pick and unambiguous absolute sample-time mapping; no unresolved gaps across the scored interval; a predeclared pre-P warm-up and post-P scoring window; exact raw-to-release match; and documented network permission. Prefer the smallest subset with one trace per event to reduce within-event pseudo-replication. Publish all eligible and excluded counts and reasons. Do not select on detector success or observed preprocessing effect.

Do not adopt HNZ or a specific number of events until metadata inspection confirms actual availability. A pilot may be one matched trace for software/data-path validation; that sample cannot estimate population effects.

## Checklist before download, commit, or redistribution

- [ ] Verify the authoritative record, exact version, files and checksums.
- [ ] Record expected bytes for each requested file; request only the smallest needed item.
- [ ] Verify file-level license and attribution; for EIDA, verify the actual network policy and any registration/authentication rules.
- [ ] Confirm rawness, sample rate, units, timing convention, channel and station metadata.
- [ ] Confirm event ID, reviewed pick provenance, pick time reference, trace start, gaps and raw/release correspondence.
- [ ] Save request parameters and source DOI/URL without secrets.
- [ ] Keep downloaded data out of Git unless redistribution permission is explicit and repository policy is established.
- [ ] For EPIC, inspect Zenodo files and size; the current Zenodo API 500 prevents this check.
- [ ] Define a data citation and attribution entry before sharing derived data or figures.

## Sources checked

- INSTANCE release page, including sample/full collection counts, archive sizes and license: https://www.pi.ingv.it/banche-dati/instance/ — checked 2026-10-26.
- Michelini et al. (2021), “INSTANCE – the Italian seismic dataset for machine learning,” Earth System Science Data 13, 5509–5534: https://doi.org/10.5194/essd-13-5509-2021 — checked 2026-10-26.
- Williamson et al. (2026), “Exploring the Use of the EPIC Earthquake Early Warning Algorithm in Alaska”: https://doi.org/10.1785/0120260139 — checked 2026-10-26.
- DataCite metadata for EPIC Alaska dataset DOI 10.5281/zenodo.19897535: https://api.datacite.org/dois/10.5281/zenodo.19897535 — checked 2026-10-26. Direct Zenodo record API returned HTTP 500 on same date.
- EIDA policy and access pages: https://eida.ingv.it/en/datapolicy and https://www.eida.ingv.it/en/getdata — references to check per network; policy text not independently revalidated in this sprint.
