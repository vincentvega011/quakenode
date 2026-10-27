# QuakeNode dataset feasibility

**Checked:** 2026-10-26  
**Basis:** context.md and the earlier Phase 1 documents, plus primary dataset/archive documentation linked below. This is a source-document review only. No waveform, metadata, or sample dataset was downloaded or queried in this task.

## Decision

**A first scientifically interpretable real-waveform experiment is feasible, but only as a bounded benchmark on curated event/noise windows.** The most practical starting point is the officially distributed **INSTANCE version 3 sample dataset**: the producer provides a 1.7 GB compressed sample (2.74 GB expanded) with 10,000 events and 1,000 noise waveforms and identifies the dataset as CC BY 4.0. The full INSTANCE release is far larger. This is enough in principle to run paired, causal replay conditions on fixed records, provided a metadata-only inspection confirms the sample includes enough matched station/event traces for the selected protocol.

This can support detector-level measurements (event detection and latency on the supplied earthquake clips; false triggers per analyzed noise-window time under a stated definition) and controlled simulated delivery loss/delay on those same clips. It does **not** provide naturally continuous network traffic or observed communication failures. A faulted run therefore estimates sensitivity to the specified simulated fault process, not real-world network reliability.

The chosen direction—fault effects on existing EEW pipelines—**cannot yet be claimed as a full multi-station network benchmark**: the sample’s event grouping, cross-station temporal overlap, metadata completeness, and exact selected-file transfer have not been verified from an actual metadata read. It also cannot yet support target-site warning utility. Although the full dataset has event ground-motion intensity measures, they are not by themselves time-of-threshold observations at a target site. The source waveforms could potentially support such a study after a station/event subset, physical units, response processing, and common time axis are validated; no such validation has happened.

If the first experiment requires long continuous noise, real packet arrival logs, realistic communication failure distributions, or defended warning-time-at-target results, the honest outcome today is **not ready**. Use INSTANCE for the narrow detector/fault sensitivity pilot, and treat EarthScope/USArray or a target-specific strong-motion archive as a separate feasibility gate.

## Recommended primary dataset and why

### INSTANCE, official sample dataset v3

- Official landing/download page: [INGV INSTANCE](https://www.pi.ingv.it/banche-dati/instance/); dataset DOI [10.13127/instance](https://doi.org/10.13127/instance); description paper [Michelini et al. (2021), ESSD 13, 5509–5544](https://doi.org/10.5194/essd-13-5509-2021).
- The official page lists a **sample dataset, 1.7 GB compressed / 2.74 GB expanded**, containing 10,000 events and 1,000 noise waveforms and associated metadata. It links separate components for events, noise, metadata, and station inventory. The full data require 39 GB compressed / 156 GB expanded for event counts, 151 GB compressed / 156 GB expanded for event ground-motion units, 3.9 GB compressed / 18 GB expanded for noise, and 275 MB compressed / 1.8 GB expanded for event metadata v3. These values are the official page’s published sizes; they are not estimates of the subset needed for QuakeNode.
- The paper reports fixed 120 s, three-component windows sampled at 100 Hz; digital counts and instrument-response-removed physical units are provided for earthquake events. HH/EH channels are in m/s and HN channels in m/s². Noise files are in digital counts. The event metadata contains source, station, path, waveform-quality and phase-related fields; station coordinates and an inventory are published. The official page reports 54,008 earthquakes, 1,159,249 event three-component waveforms, 132,330 noise three-component waveforms, 19 networks and 620 stations.
- The data are selected **windows**, not a continuous record. Paper-described selection used reviewed catalog information and phase residual/weight criteria; there is selection bias toward cataloged, usable records. Noise windows were independently selected from event-free periods and station operation intervals; the paper explicitly says they are not the same time window across stations. It also describes automatic instrument-response processing and warns of erroneous traces/IMs due to original spikes or anomalous trends.
- **Access:** public links from the official INGV dataset page. The page does not state that an account is required. Because no download was attempted, actual transfer success, current server limits, and any hidden access control remain unverified. Prefer the v3 sample plus metadata rather than full volumes for an initial pilot; the sample itself is not tiny.
- **Fit:** best accessible, legally clear starting point for a reproducible detector-level paired replay: same waveform and detector, fault-free versus defined synthetic packet/sample loss or delay. Since there are many station-event windows and event/source metadata, a metadata-only check may reveal a small multi-station event subset; do not assume this until checked. The sample is not sufficient for estimates of empirical link-failure rates or deployment-level false alerts per calendar day.

## Backup dataset

### EarthScope USArray Transportable Array (TA) archive plus ANF bulletins

This is the better *technical* candidate if QuakeNode later needs continuous multi-station traces and real event-free intervals. EarthScope documents TA raw data in miniSEED and says archived data are delivered through its FDSN services and sponsored S3 bucket. The TA archive documentation lists BHZ/BHN/BHE at 40 samples/s as ground velocity; strong-motion HN channels, where present, are 100 samples/s ground acceleration. StationXML service provides time-dependent channel/station metadata and response. TA network metadata reports more than 400 broadband stations deployed across about 1,700 locations with roughly 70 km spacing; stations generally occupied for 18–24 months. ANF exposes monthly CSS 3.0 event/arrival/association bulletins for TA, with analyst review ending July 2020; later solutions are automatic/unreviewed.

- Access route: [EarthScope sponsored miniSEED on AWS](https://docs.earthscope.org/sponsored-open-data/), [FDSN dataselect](https://service.earthscope.org/fdsnws/dataselect/1/), [FDSN station metadata](https://service.earthscope.org/fdsnws/station/1/), [ANF event bulletins](https://anf.ucsd.edu/tools/events/).
- The AWS sponsored-data instructions say direct S3 access needs no credentials and data are organized by network/year/day/station with UTC day boundaries; the service documents miniSEED v2/v3 and that data may contain gaps. FDSN data product access is anonymous until **2026-12-15**, after which an EarthScope account is required; current anonymous quotas are 10 GiB/hour and 50 GiB/day. These rules are time-sensitive and should be rechecked before acquisition.
- **License gate:** EarthScope’s 2025 policy says data originating from EarthScope-operated facilities are CC BY 4.0, except when a contributing provider has a more restrictive license. Its sponsored-data instructions say the network owner’s registered license governs, and CC BY 4.0 is the default where no network license is declared. The TA FDSN record surfaced here does not itself show an explicit license. Treat redistribution as **unresolved until TA’s current network/data metadata and provider rights are checked**, and cite the network DOI [10.7914/SN/TA](https://doi.org/10.7914/SN/TA) plus EarthScope as instructed.
- **Fit and limits:** continuous event/no-event replay, cross-station timing, station outage simulations, and event-level detection/fusion are plausible. But a specific regional/date/channel window, common station overlap, event count, gaps, timing quality, exact license status, and usability of any strong-motion target station have not been checked. This is a future backup, not the currently selected dataset.

### Other candidates screened

| Candidate | Verified source facts | Feasibility for this first study |
|---|---|---|
| **OpenEEW public data** | [Project repository](https://github.com/openeew/openeew) states historic unprocessed accelerometer data and CC BY-SA 4.0 for AWS data; [Python client docs](https://openeew-python.readthedocs.io/en/master/openeew.data.html) describe anonymous S3 access, historical device metadata, UTC record filters, and a sample_t estimate using device_t or cloud_t and sample rate. Code is Apache-2.0; dataset has separate CC BY-SA terms. | Promising for device packet/record replay. Not primary yet: actual record schema, sample rate and units, clock semantics and drift, event/station matching, no-event duration, accelerometer calibration, target-site shaking, selection coverage, and exact S3 size have not been independently verified from actual records. Share-alike obligations apply to dataset derivatives/redistribution. |
| **STEAD** | [Official repository](https://github.com/smousavi05/STEAD) provides chunked HDF5 plus CSV, labels earthquake/noise waveforms, reports chunks around 13.7–15.7 GB and a merged archive around 85 GB, and links CC BY 4.0. It warns that some back-azimuth labels were misplaced. | Useful model/detector dataset, but large chunks and isolated snippets make it less suitable for continuous multi-station replay or outage/network studies. Metadata and sample time rules need paper/repository-level checks before use. Not selected. |
| **Montefeltro 1S continuous dataset** | [Zenodo v1, DOI 10.5281/zenodo.7064384](https://zenodo.org/records/7064384) documents four stations, station coordinates/deployment periods, continuous 100 sps miniSEED, response files, and 42.0 GB total (year archives 801 MB, 18.2 GB, 23.0 GB). | Excellent technical shape for multi-station continuous replay but too large for the initial small pilot. The Zenodo record’s license field was not exposed in the inspected source, so redistribution terms are **unresolved**. It is not recommended until license and event/noise catalog alignment are checked. |

## What data can support which claim?

| Evidence type | What it validates | What it does not validate |
|---|---|---|
| **Synthetic fixture** (author-created, deterministic) | Replay ordering; no future-sample leakage; packet gap/duplicate/reordering handling; clock-offset handling; seeded fault reproducibility; metric denominators; alert/state transitions; exact expected outcomes. | Detector performance on real earthquakes, seismic noise robustness, real network behavior, station geometry realism, or operational warning time. |
| **INSTANCE real waveforms** (selected 120 s snippets) | Detector event detection/picking/latency on selected earthquake windows; false triggers over the stated count/duration of included noise windows; paired effects of a declared *simulated* delay/loss/outage model on those same windows; potentially event-level multi-station behavior after verifying joins/time coverage. | Real-world communications reliability; continuous false-alert rates per day/month; natural station outages; whole-network availability; representative regional performance without a sampling argument. Target-site utility only after choosing a recorded target station and deriving an independently checked shaking-threshold time from a suitable physical-unit trace on the same timeline as simulated alert delivery. |
| **Continuous archive + target-site record** (not yet selected/validated) | Could support event/no-event denominators over continuous time, station-level observed threshold crossing, and a clearly scoped alert lead-time analysis if all station clocks, responses, event associations, and alert timing are reconciled. | Population-level safety benefit, warning coverage in a different target region, or damage avoided without exposure/impact data. |

## Synthetic fixture design

Build the fixture in code only when implementation begins; do not present it as a data source or seismic validation. Keep it small (three virtual stations, three components, tens of seconds at a declared sample rate) and deterministic:

1. Store each sample’s recorded UTC time and sample index explicitly; use one fixed UTC epoch and exact rational sample interval.
2. Include generated baseline noise plus mathematically defined pulses with known onset and amplitude. Label these as artificial signals, not earthquake records.
3. Include a known target-site threshold crossing and a known alert/delivery time so warning-time arithmetic can be tested as a software invariant only.
4. Specify packet interval, packet contents, delivery times, seed (or deterministic hand-authored values), and exact packet loss, reordering, station outage, clock offset, and recovery cases in a fixture manifest.
5. Include expected output events and metric numerators/denominators by hand. The fixture must catch future-sample access, silent gap filling, timestamp ambiguity, and false-alert denominator mistakes.

## Data-access steps

1. From the [official INSTANCE page](https://www.pi.ingv.it/banche-dati/instance/), retrieve only the v3 sample-dataset link, event metadata version 3, noise metadata if separate from the sample, and relevant station inventory. The official sample size is 1.7 GB compressed / 2.74 GB expanded; decide whether the project can store this before acquisition. No credentials are listed by the source, but access was not tested here.
2. Before waveform transfer, inspect the sample metadata documentation and confirm the actual fields for event identifier, station/network/location, trace start time, phase sample/time, channel, units, sample rate, missing data, and station coordinates. Check whether multiple station traces for the same event share usable absolute timestamps.
3. Select a small predeclared event/station subset from metadata. Record exclusions and reasons before examining detector outcomes. Download only relevant subsets if the official interface permits; the source page does not document selective per-event download from the HDF5 sample, so capability/effort is **unknown**. Do not assume that chunked HDF5 permits low-transfer remote reads.
4. Verify waveform values, timing, and physical units against paper methods and metadata. Keep counts separate from response-removed units. For any derived acceleration/velocity, save processing choices and response provenance.
5. For the EarthScope backup, first query station availability and StationXML metadata for a short candidate window, then identify events from ANF/USGS catalog. Restrict the waveform request to a few stations and hours; verify TA data quality class, time gaps, clock quality, channel response, and network license before any redistribution. Check the Dec 15, 2026 account change before use.
6. For OpenEEW, inspect only a small public metadata/record range after documenting the request. Confirm device history, device_t vs cloud_t, nominal sample rate, accelerometer units/calibration, record continuity, event matching and CC BY-SA obligations before using it as a benchmark dataset.

## License and redistribution

| Dataset/source | License evidence | Intended use and redistribution status |
|---|---|---|
| INSTANCE | INGV page explicitly says CC BY 4.0 and links the license. | Reuse and redistribution are permitted with attribution, license link, and changes indicated. Cite dataset DOI and paper. Keep source metadata and license with derived subsets. |
| EarthScope TA | EarthScope policy allows CC BY 4.0 for facility-originated data unless a more restrictive contributor license applies; sponsored-data docs defer to network owner registration. TA record has DOI but no explicit license was verified in this review. | Access is open; **redistribution is unresolved pending actual TA network/license metadata check**. Do not bundle data until resolved. |
| OpenEEW | Project identifies AWS data as CC BY-SA 4.0; software repositories are Apache-2.0. | Data can be reused/shared under attribution and share-alike terms; keep data and code licenses distinct. Check source-specific terms before redistribution. |
| STEAD | Official repository exposes CC BY 4.0 license link. | Dataset redistribution appears permitted under attribution; cite original dataset paper and keep license/changes. Confirm license applies to each file/version used. |
| Montefeltro 1S | Zenodo record identifies an open dataset but license field was not verified in the inspected record content. | **Unresolved**. Do not redistribute; obtain and review the record’s machine-readable license/README before use. |
| Synthetic fixture | Newly authored deterministic data, with no third-party samples or model weights. | Project can license it directly, subject to the repository’s chosen license. Clearly identify it as synthetic. |

This is not legal advice. The checklist below is the project’s release gate, not an assertion that every use is automatically covered.

## Required fields and outstanding metadata

For the selected INSTANCE sample, confirm these in the actual v3 metadata before experiment registration:

- event ID and origin time, origin uncertainty if supplied, magnitude/type and source coordinates/depth;
- station network/station/location, channel/component, latitude/longitude/elevation, operating epoch, response/inventory reference;
- trace start UTC and sample index/time convention; phase pick times/samples and pick provenance;
- sample rate after preprocessing, channel-specific units, counts versus physical ground motion, filter/response-removal history;
- event-to-station join cardinality, simultaneous coverage and start/end overlap across stations;
- record gap/mask and quality fields, clipping/spike flags, SNR and trace exclusions;
- noise-window start time, analyzed duration, source/station associations, and confirmation that labels exclude events only according to the paper’s catalog procedure;
- target station observed waveform and ground-motion threshold-crossing time, if (and only if) utility is to be evaluated.

Known published qualifications: traces were resampled to 100 Hz and detrended; event waveform windows were selected with approximately 15–20 seconds before the P arrival where data allowed; start times can vary because of MiniSEED logical-record boundaries or missing pre-P data. The paper notes not all source fields/picks are present, not all physical-unit traces are error-free, and automatic response processing can generate bad IMs from bad source waveforms. The version 3 event metadata corrected a previous spectral-acceleration unit issue; use v3 only.

## Proposed event/station selection criteria

Use a metadata-only selection before opening waveforms; write the exact selection query and counts into a manifest.

1. Use INSTANCE sample v3 and its matching event metadata v3; avoid mixing versions.
2. Prefer cataloged events with an unambiguous origin time and usable P arrival, known station coordinates, valid response/units and no flagged clipping, gaps, spikes or preprocessing faults. Retain other records in a separately reported sensitivity/exclusion analysis rather than silently dropping them.
3. For a multi-station subset, require at least a predeclared number of stations for one event and verify that all contributing trace windows can be placed on their recorded absolute time axis. If the sample does not offer a defensible number of such event groups, narrow the initial claim to per-trace detector sensitivity; do not substitute stations across unrelated events and call it fusion.
4. Stratify or report results by magnitude, distance, channel class, SNR and station, so the result is not just a few high-SNR nearby records. Avoid tuning thresholds on the evaluation traces.
5. Use the labeled noise subset for false-trigger experiments only with denominator defined in analyzed waveform time (e.g., total valid station-hours from 1,000 × 120 s windows after exclusions), not as continuous calendar time. Noise windows were selected and may not represent all site, season, anthropogenic or operational conditions.
6. Define fault application before results: packetization, packet duration, drop probability/seed, station outage start/duration, fixed or sampled delay, recovery, and whether missing data are masked or buffered. Do not describe chosen synthetic fault rates as empirically realistic until supported by network measurements.

The sample’s event count is verified from the official page, but its event/station distribution and criteria within the sample are not exposed there in detail. Exact usable event count after these filters is **unknown until metadata is inspected**.

## Metrics: supported and unsupported

### Supported by an INSTANCE detector pilot, after metadata validation

- Event detection recall/miss fraction over the **selected, labeled event traces or event groups**, with event-level matching and denominator stated.
- Detection latency relative to declared reference (P pick or origin time); report the reference explicitly and distinguish sample time from simulated arrival/delivery time.
- False triggers per valid analyzed noise-window hour, plus raw false-trigger count and number of valid windows; this is a sampled-window rate, not operational false alerts per day.
- Paired fault-minus-baseline change in detection, misses, and latency for each fixed record/event, with uncertainty summarized across independent events (not waveform components treated as independent events).
- Per-record warning interval at a chosen target station only if the actual target trace has validated physical units, common absolute time, and a predeclared threshold crossing; call this a waveform-derived lead-time quantity, not user warning utility.

### Not supported by the selected sample alone

- Actual network delay, jitter, packet loss, station uptime, or natural recovery performance.
- Continuous-time false alert rates, detection availability, or outage statistics for the Italian network.
- A representative multi-station fault-sensitivity estimate until cross-station event joins, sample selection and time overlap are established.
- Public-safety effectiveness, population coverage, injury/damage reduction, or warning utility at a real community.
- A defensible target-site warning-time result at this stage. The existence of PGA/PGV metadata is not sufficient: warning time needs a specific target-site waveform/ground-motion reference and a validated time at which the threshold is crossed, paired with alert delivery time on one clock.

## Approximate data volumes and access restrictions

Only source-published volumes are given here. INSTANCE v3 sample: 1.7 GB compressed and 2.74 GB expanded. Full INSTANCE components range from 3.9 GB compressed for noise to 151 GB compressed for event physical-unit traces; the page does not provide a small per-event extract size. EarthScope TA has no fixed volume for a selected subset; volume depends on stations, channels, and request duration, and service quotas apply. STEAD is 85 GB in the official repository’s merged-download description. Montefeltro is 42.0 GB per Zenodo. OpenEEW selected-range volume is unknown from inspected sources.

No dataset request was made in this task, and no access credentials or tokens were used.

## Risks and fallback plan

- **Main data risk:** INSTANCE is curated windows, not continuous streams. It supports controlled replay effects on existing signals, but external packet faults remain simulated and noise-denominator interpretation is narrow.
- **Multistation risk:** an average of 21 three-component traces per event is reported for the full collection, but the sample’s station/event coverage and usable simultaneous overlap must be inspected. If overlap is too sparse, restrict claims to per-trace detection sensitivity.
- **Selection bias:** reviewed, quality-screened/catalog-centered windows overrepresent detectable events and exclude much messy operational data. Include stratified reporting and explicit exclusions; do not generalize to all EEW conditions.
- **Preprocessing risk:** fixed 100 Hz, detrending, resampling, channel mix, instrument response removal and any filtered/processed form can change detector behavior. Use one data representation consistently and record it.
- **Target-site risk:** no confirmed target community/station or validated shaking-threshold timing is currently in hand. Drop warning-utility claims until those exist.
- **Access/licensing risk:** INSTANCE has clear CC BY 4.0, but download itself has not been exercised. EarthScope TA redistribution terms depend on its current network/provider rights. OpenEEW is share-alike. Montefeltro terms remain unresolved.
- **Fallback:** if INSTANCE sample download or metadata validation fails, do not silently swap to a synthetic “real data” experiment. First exercise the software with the labeled synthetic fixture; then use EarthScope TA only after a small metadata-only availability/license check. Keep synthetic software checks separate from detector results.

## Checklist before committing or redistributing any data

- [ ] Confirm exact dataset release/version and official source URL/DOI.
- [ ] Re-read the license applicable to the actual waveform and metadata files; preserve attribution and notices.
- [ ] Verify redistribution and derivative-work conditions; for OpenEEW honor CC BY-SA; for TA resolve any provider restriction.
- [ ] Record retrieval date, request parameters, file checksums, source citation and modifications.
- [ ] Check whether the dataset terms permit storing waveform excerpts in Git, release assets, CI fixtures or public mirrors; prefer scripts/manifests over waveform redistribution where uncertain.
- [ ] Keep credentials/private tokens out of manifests, logs and repository history.
- [ ] Verify UTC timestamp convention, sample clock, trace start, sample-rate rationality, gaps, duplicates and clock-quality flags.
- [ ] Verify station/channel identity, coordinates, deployment epoch, instrument response and physical units for every selected trace.
- [ ] Reconcile event IDs, origin times, phase picks and station trace joins; report unmatched or ambiguous records.
- [ ] Define event, station, noise-window, valid-duration and false-trigger denominators before detector runs.
- [ ] Freeze selection and exclusions before inspecting fault-condition outcomes.
- [ ] Keep the synthetic fixture clearly marked and separately licensed from all real seismic records.
- [ ] Do not publish a warning-time claim without a validated target-site shaking reference and alert time on a common time base.

## Sources checked

All links below were checked on **2026-10-26**. “Checked” means the source page/document was reviewed, not that any data were downloaded.

1. INGV, [INSTANCE dataset page and download sizes](https://www.pi.ingv.it/banche-dati/instance/); [dataset DOI](https://doi.org/10.13127/instance).
2. Michelini, A. et al. (2021), [“INSTANCE – the Italian seismic dataset for machine learning,” ESSD 13, 5509–5544](https://doi.org/10.5194/essd-13-5509-2021). Methods for trace lengths, sample rate, event/noise selection, metadata, processing and known limitations.
3. EarthScope, [USArray data overview, channel descriptions and quality classes](https://ds.iris.edu/ds/nodes/dmc/earthscope/usarray/).
4. EarthScope, [sponsored miniSEED repository and access](https://docs.earthscope.org/sponsored-open-data/); [user limits and Dec 15, 2026 account requirement for FDSN data products](https://docs.earthscope.org/user-limits).
5. FDSN, [TA network metadata and DOI](https://www.fdsn.org/networks/detail/TA/); EarthScope, [data license policy](https://resess.unavco.org/data/policies_forms/data-policy/data-license.html).
6. ANF, [TA monthly event bulletins and review cutoff](https://anf.ucsd.edu/tools/events/).
7. OpenEEW, [project/data license statements](https://github.com/openeew/openeew); [Python data client](https://github.com/openeew/openeew-python); [data API documentation](https://openeew-python.readthedocs.io/en/master/openeew.data.html).
8. Mousavi et al., [STEAD repository and download sizes/license](https://github.com/smousavi05/STEAD).
9. Santini et al., [Montefeltro continuous dataset, Zenodo record](https://doi.org/10.5281/zenodo.7064384).

