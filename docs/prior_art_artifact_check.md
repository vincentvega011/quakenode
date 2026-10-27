# Prior-art and positioning audit (artifact level)

Research prototype, not an operational warning system. Audit date and access date for every URL: **2026-10-26**. This document records what I actually read, what I could only see as an abstract or metadata, and what I could not access. It contains no novelty claim; the words "first" and "novel" appear only to describe checks that remain to be done.

## 1. What I read versus what I could not access

| item | what I read | not accessed / limits |
|---|---|---|
| Portnoi et al. 2014 (QCN) | Abstract (via OpenAlex), reference list (Crossref). Elsevier's open API returned only metadata | Full text: ScienceDirect served a captcha page; I did not try to bypass it. Methods, figures, code availability: **unverified** |
| Williamson et al. 2026 (EPIC Alaska) | Abstract and reference count (Crossref), license (CC BY, Crossref/Unpaywall), the Zenodo dataset record 10.5281/zenodo.19897535 | Full text and supplement: GeoScienceWorld bot wall. Methods, supplement, EPIC code availability: **unverified** |
| Zuccolo et al. 2021 | **Full text PDF** (Frontiers, CC BY) | none |
| Meier 2017 | Abstract and reference list (Crossref) | Full text: Wiley bot wall. Methods, data/code statement: **unverified** |
| Boese et al. 2022 (ShakeAlert synthesized sequences) | Abstract (Crossref); USGS record page has no further detail | Full text: closed access (Unpaywall: closed). **Unverified** beyond the abstract |
| CREW (EPOS testing center) | EPOS service page, https://www.epos-eu.org/tcs/near-fault-observatories/services/crew | Metrics pages, software, licences of CREW: not checked |
| SeisBench | Shallow clone at commit `e5616ad33c00aba75d5130b44222df46b41e4094` (2026-10-05); read `seisbench/data/instance.py`, `seisbench/models/phasenet.py`, `eqtransformer.py`, `base.py`, `util/arraytools.py`, examples list, LICENSE | Did not run it. Did not read the documentation website or all model files |
| OpenEEW | Shallow clone of `openeew/openeew` (commit `a23ba77`, 2024-05-10), `openeew-python` README and license via the GitHub API | The detection algorithm repositories outside the two above; whether a replay or evaluation mode exists elsewhere in the org: not verified |
| SeisComP | `scautopick` and waveform-playback documentation pages on seiscomp.de; GitHub metadata | Source code not read |
| ObsPy `obspy.realtime` | Docstrings of the locally installed obspy 1.5.1 | Not an evaluation of its behaviour |
| FisH (arXiv 2408.06629) and Muenchmeyer et al. (arXiv 2110.13671) | Full text PDFs (keyword-searched and read around the hits) | Muenchmeyer: I searched the text for detrend, demean, normaliz, causal, real-time, online; I did not read the whole paper |
| Other literature | Abstracts only, from OpenAlex/Crossref/search snippets | listed in the search log |

Tools were also limited: a browser extension tool was not connected, and the web search tool returns snippets from a US-only index. Scholarly databases that need institutional access (Scopus, Web of Science, Google Scholar) were not used.

## 2. Artifact checks

Capabilities: (i) causal streaming replay, (ii) network faults (delay, loss, outage), (iii) offline-versus-causal preprocessing differences, (iv) event-level or picked-trace evaluation, (v) reproducible configs and seeds, (vi) target-site warning time. Values: yes / partial / no / unverified.

### 2.1 Portnoi, Schlachter, Taufer (2014), https://doi.org/10.1016/j.procs.2014.05.041
- Does (from the abstract): proposes multiple servers instead of a master-worker topology for the Quake-Catcher Network, and "emulate[s] these critical scenarios in a simulation environment". Metrics: "time to detect an earthquake from 1.8 s to 173 ms in case of network congestion and the number of lost trickle messages from 2,013 to 391 messages in case of network failure". The reference list cites SimBOINC/SimGrid/SimBA-style simulators.
- Data/metrics beyond the abstract, code, licence: **unverified** (full text not accessed). The article is open access (Unpaywall/OpenAlex: `cc-by-nc-nd`).

### 2.2 Williamson, Lux, Henson, Allen (2026), https://doi.org/10.1785/0120260139
- Does (abstract): tests EPIC on 530 Alaska events (M 4.5 to 8.2), "real seismic waveforms and metadata ... in simulated real-time replays"; measured detection success, epicenter accuracy, magnitude estimation; "The openly available Alaska test suite also provides a robust benchmark for future algorithm development." Result quoted in the abstract: 345 of 530 events detected and matched.
- Test suite: Zenodo record https://doi.org/10.5281/zenodo.19897535, CC BY 4.0, one file `testsuite_data_williamson.zip` of 8,372,439,484 bytes, published 2026-06-26 (record read through the Zenodo API). Article licence per Crossref: CC BY. **Whether the suite can be rerun without EPIC, and whether EPIC source is public: unverified.** I found no public EPIC repository with GitHub search (queries below).

### 2.3 Zuccolo, Cremen, Galasso (2021), https://doi.org/10.3389/feart.2021.686272
- Does (full text read): compares PRESTo and VS(SC)+scanloc on 27 historical or synthetic events "in real-time simulation mode, accounting for the continuous streaming of data and effective processing times" using "playbacks of recorded seismic waveforms or those simulated through a physics-based method". Lead time at target sites is defined as "the time difference between the S-wave arrival and the first EEW estimate; a 1 s transmission delay is also accounted for". Metrics: timeliness and accuracy of location and magnitude, stable-estimate times, ground-shaking prediction at lead times of 15, 10 and 5 s.
- Code/data: "The raw data supporting the conclusions of this article will be made available by the authors, upon reasonable request." SeisComP is open; "scanloc is a commercial software by gempa". Article CC BY. I found no discussion of detrending or filter causality (keyword search of the text); PRESTo's FilterPicker is described but not compared causally.

### 2.4 Meier (2017), https://doi.org/10.1002/2017JB014025
- Does (abstract): proposes metrics that "directly quantify an algorithm's ability to identify target sites that will experience ground motion above a critical (user-defined) ground motion threshold"; processes "15,553 recordings from 238 earthquakes with M > 5 (mostly from Japan and southern California) in a pseudo-real-time environment" for two end-member methods. Methods detail, code, data availability: **unverified**.

### 2.5 Boese et al. (2022) and CREW
- Boese et al., https://doi.org/10.1785/0220220088 (abstract only): tests EPIC, FinDer and PLUM on "synthesized earthquake sequences" built by "combining the signals from pairs of well-recorded earthquakes (4.4<=M<=7.1) using time shifts ranging from -60 to +180 s"; metrics include "alerting timeliness"; suggests "25 of our 73 scenarios become part of the baseline data set". The abstract says nothing about network faults or preprocessing. Closed access; code/data: **unverified**.
- CREW (EPOS), https://www.epos-eu.org/tcs/near-fault-observatories/services/crew: "a European-level testing facility for earthquake Early Warning systems". It "operates on ISNet"; "Minimum latency waveform data from the network is available on a single SeedLink server to the EEW algorithms that operate on separate Virtual Machines"; alerts in QuakeML; "Performance criteria will include location, magnitude, lead-time and ground motion estimation". This is a **live** test bed, not a replay tool. Note the name clash: SeisBench's `CREW` class is a different thing, the "Curated Regional Earthquake Waveforms" dataset (Aguilar Suarez & Beroza 2024, Seismica, https://doi.org/10.26443/seismica.v3i1.1049).

### 2.6 SeisBench, https://github.com/seisbench/seisbench
- GPL-3.0; 428 stars; last push 2026-10-05; latest release v0.12.0 (2026-06-24); 23 contributors listed; created 2020-11-12; 18 open issues.
- INSTANCE: `seisbench/data/instance.py` defines `InstanceNoise`, `InstanceCounts`, `InstanceGM`, `InstanceCountsCombined`; they download the **full** bz2 archives from `repo.pi.ingv.it/instance/` (events metadata, counts HDF5, GM HDF5, noise HDF5) and convert them into SeisBench's own format. It does not use the 10k sample.
- Preprocessing inside models: for PhaseNet, `annotate_batch_pre` does `batch - batch.mean(axis=-1)` over the input window, optionally `sbu.torch_detrend` (a linear fit over the window), then divides by the window std or peak. EQTransformer has `norm_detrend` and `norm` options likewise. These statistics use every sample in the model's input window, so inside a window they are not causal; whether this changes trigger timing in a stream is not examined in the code.
- Streams: `annotate` works on ObsPy streams by grouping, slicing and merging windows. `annotate_async` is an asynchronous call, not an online mode. A grep for real-time, online, seedlink, latency, causal and streaming found no streaming evaluation mode. Causality appears only in resampling: a documented option `zerophase_resample` ("If true, the filter applied before resampling for anti-aliasing is zero-phase. Otherwise, uses causal filter").
- Benchmark tooling: datasets, generators/augmentations, models, training examples; the associated picker benchmark is Muenchmeyer et al. 2022 (https://doi.org/10.1029/2021JB023499, arXiv 2110.13671), which evaluates on INSTANCE among other datasets with offline windows. In that arXiv text I found no mention of detrending, demeaning or causal evaluation (keyword search).

### 2.7 OpenEEW, https://github.com/openeew/openeew
- Apache-2.0; 208 stars; last push 2024-05-10. The main repository holds docs and a data README: an AWS Public Dataset of raw accelerometer data; "Accelerometer data is stored with the same structure as received from the devices in order that any processing applied to the archived data could straightforwardly be applied to the data in real time." `openeew-python` (Apache-2.0, 19 stars, last push 2021-09-02) lists "Downloading and analyzing accelerometer data; Real-time data processing; Detection algorithms". A keyword search of the main repository for replay, simulat, playback, evaluat, benchmark, latency, packet found no evaluation or replay tooling. Whether another OpenEEW repository has one: **not verified**.

### 2.8 Other repositories found

GitHub searches (queries in the log) and manual checks. Stars and dates from the GitHub API on 2026-10-26.

| repository | licence | stars | last push | what it is (facts only) |
|---|---|---|---|---|
| SeisComP/seiscomp | README: "primarily released under the AGPL 3.0" (API field NOASSERTION) | 90 | 2026-10-19 | Acquisition/processing/distribution system. Docs: `scautopick` default filter `RMHP(10)>>ITAPER(30)>>BW(4,0.7,2)>>STALTA(2,80)`; "a pick is set to the time when this threshold is exceeded ... and the picker is set inactive" until the ratio falls to 1.5; `--playback` for non-real-time runs; real-time playbacks inject miniSEED into seedlink with `msrtsimul` |
| obspy/obspy | module docstring of `obspy.realtime`: LGPL-3.0 (API field NOASSERTION) | 1341 | 2026-10-14 | `obspy.realtime.RtTrace`: "real time processing of periodically append data packets"; causal time-domain processes (offset, scale, integrate, differentiate, boxcar, kurtosis, tauc, mwp) |
| seisbench/seisbench | GPL-3.0 | 428 | 2026-10-05 | see 2.6 |
| openeew/openeew | Apache-2.0 | 208 | 2024-05-10 | see 2.7 |
| xspanger3770/GlobalQuake | none shown | 409 | 2025-01-23 | README starts with "Repository Discontinued"; near-real-time monitoring application. No replay/benchmark terms in the README |
| AI4EPS/QuakeFlow | MIT | 122 | 2026-08-10 | Deep-learning earthquake monitoring workflow with cloud computing |
| SeisComP/scdlpicker | AGPL-3.0 | 27 | 2026-10-12 | DL repicker (SeisBench) for already-located events in SeisComP, not a streaming evaluator |
| ut-beg-texnet/scmlpick | BSD-3-Clause | 6 | 2026-08-07 | SeisComP module running EQCCT for real-time picking; README claims "latencies typically below 60 seconds" |
| ut-beg-texnet/eqcct | none shown | 21 | 2026-05-04 | EQCCT picker |
| PabloELara/E3WS | CC-BY-4.0 | 17 | 2026-04-28 | Single-station ML EEW from 3 s of records |
| jiunting/MLARGE | none shown | 9 | 2023-03-28 | Training/analysis scripts for a magnitude model |
| sigiteko/eew_simulation | GPL-3.0 | 0 | 2025-09-10 | Lead-time and exposure simulation fed by TEAM detections (West Sumatra case study), not a waveform replay |
| rezakarbasi/EEW_simulator | none shown | 1 | 2022-01-06 | One-line README: "simulation app to evaluate different algorithms on earthquake datas" |
| FMassin/scpbd | none shown | 2 | 2025-08-06 | Docker for SeisComP miniSEED playback |
| Dongwu259/open_quake_sim | MIT | 7 | 2026-10-16 | Web earthquake simulator/monitor for Japan (JMA data); not a seismological evaluation tool as far as the description shows |

I found no public EPIC/ElarmS/PRESTo source repository with GitHub search (queries "Point-source Integrated Code", "ElarmS", "PRESTo"), which does not prove none exists.

### 2.9 Comparison matrix

| item | (i) causal streaming replay | (ii) network faults | (iii) offline vs causal preprocessing | (iv) event / picked-trace evaluation | (v) reproducible configs and seeds | (vi) target-site warning time |
|---|---|---|---|---|---|---|
| Portnoi 2014 (QCN) | partial (simulation environment; unverified detail) | **yes** (congestion, failure; abstract) | unverified | unverified | unverified | no (detection time, lost messages) |
| Williamson 2026 (EPIC Alaska) | **yes** ("simulated real-time replays", abstract) | unverified | unverified | yes, event level (530 events) | partial (open test suite, CC BY 4.0; EPIC code unverified) | unverified |
| Zuccolo 2021 | **yes** (playbacks, "continuous streaming", processing times) | partial (fixed 1 s transmission delay) | no (not found in text) | yes, event level | partial (data on request; one tool commercial) | **yes** (lead time at target sites) |
| Meier 2017 | partial ("pseudo-real-time", abstract) | unverified | unverified | yes, event / site level | unverified | **yes** (target-site threshold metrics) |
| Boese 2022 | partial (synthesized sequences through ShakeAlert algorithms; abstract) | no (not in abstract) | no (not in abstract) | yes, event level | unverified | partial ("alerting timeliness") |
| CREW (EPOS) | partial (live SeedLink, not replay) | no (not described) | no | yes, event level | unverified | **yes** (lead time) |
| SeisBench | no (sliding windows over streams; no online mode found) | no | partial (window mean/detrend/normalisation in `annotate_batch_pre`; `zerophase_resample` option; not evaluated for causality) | partial (pick-level benchmarks via Muenchmeyer 2022) | **yes** (public code, GPL-3.0, benchmark tooling) | no |
| OpenEEW | partial (data layout meant for real-time reuse; no replay tool found) | no | no | no | partial (data + Apache-2.0 code) | no |
| SeisComP (scautopick, msrtsimul) | **yes** (real-time playback, `--playback`) | no (no fault injection in the docs read) | partial (documented causal default chain; no offline comparison) | picks/origins only | partial (configs and AGPL code) | no |
| ObsPy `obspy.realtime` | partial (RtTrace causal chunk processing) | no | partial (causal processes only) | no | yes (LGPL) | no |
| FisH (arXiv 2408.06629) | partial (a model run on a streaming history; online vs offline picking evaluated) | no | partial (only online-computable normalisation allowed) | picked-trace level (STEAD, INSTANCE) | unverified | no |

## 3. Literature search log and findings

Index limits: `WebSearch` (standard mode, US-only snippet index); OpenAlex API (`api.openalex.org/works?search=`, titles/abstracts, top hits only); Crossref API and Zenodo API for metadata; GitHub search through `gh search repos`. No Google Scholar, Scopus or Web of Science. Queries are verbatim.

WebSearch:
1. `Portnoi Schlachter Taufer 2014 Quake-Catcher Network earthquake early warning simulation network impact`
2. `Williamson 2026 EPIC Alaska earthquake early warning replay Bulletin of the Seismological Society of America`
3. `"Study of the Network Impact on Earthquake Early Warning in the Quake-catcher Network Project"`
4. `"Exploring the Use of the EPIC Earthquake Early Warning Algorithm in Alaska" Williamson Lux Henson Allen`
5. `causal versus non-causal preprocessing earthquake early warning detrending filtering future samples real-time seismic detection`
6. `data leakage future information seismic deep learning phase picker evaluation normalization window offline versus online PhaseNet EQTransformer`
7. `real-time versus offline performance gap machine learning phase picker streaming evaluation earthquake early warning latency`
8. `INSTANCE dataset Italian seismic earthquake early warning online detection deep learning real-time`
9. `zero-phase versus causal filter picking delay detection time earthquake early warning STA/LTA`

OpenAlex searches: `causal filter real-time earthquake early warning P-wave detection preprocessing`; `future information leakage seismic deep learning benchmark phase picking`; `streaming evaluation of deep learning phase pickers real-time`; `online versus offline evaluation seismic phase picking neural network real-time earthquake early warning`; `INSTANCE dataset earthquake early warning`; `zero-phase causal filter onset time bias seismic`; `pseudo-real-time playback EEW algorithm offline processed waveforms`; plus title lookups (Waveform Identity..., FisH, LFTNet, Boore and Bommer, recursive high-pass filter..., EQTransformer PhaseNet continuous data...). Zenodo: `"Alaska" EPIC earthquake early warning test suite`, `Meier "real-time ground motion predictions"` (no relevant result). GitHub queries: earthquake early warning simulation / replay / benchmark / evaluation; eew earthquake; ShakeAlert; EEW; quakeflow; EQCCT; SeisComP; seiscomp playback; eew simulation; eew-simulator; Point-source Integrated Code; ElarmS; topic `earthquake-early-warning`; several multi-word queries returned nothing.

What the searches returned, by question (nothing here is a claim that other work does not exist):

- **Causal vs non-causal preprocessing in seismic detection / EEW.** I found general statements, not a study of the question. From search snippets of papers I did not open: zero-phase FIR filters produce precursors before impulsive arrivals (Virginia Tech note on acausal filters, https://www.geophys.geos.vt.edu/snoke/pdf/ES_SSA12_acausal.pdf); Scherbaum & Bouin (1997) show zero-phase filtered data can be converted to "equivalent minimum phase" data; D. Boore's processing notes say a causal filter produces no precursory motion but distorts phase. The SeisComP documentation (read) shows the operational default is a causal chain. No result compared a released full-window detrended product with causal processing of the same raw waveform.
- **Leakage or future information in seismic deep-learning benchmarks.** The closest hit is Wibowo et al. 2026 (Research Square preprint, https://doi.org/10.21203/rs.3.rs-11159236/v1; abstract only): "Waveform Identity and Reproducible Source-Grouped Evaluation of Seismic Phase Pickers", about train/test identity and source-disjoint splits on STEAD. That is split leakage, not window-normalisation leakage. PickBlue (arXiv 2304.06635) and others describe mean/trend removal and normalisation over the input window (snippet-level). I found no paper that frames window statistics as future-sample use.
- **Real-time vs offline gap for pickers / streaming evaluation.** FisH (arXiv 2408.06629, read): "most deep learning models in seismology rely on full three-component waveforms and are not suitable for real-time streaming data"; evaluates online picking with a 30 s history on STEAD (99% precision and recall for P, 96% and 90% for S) and offline picking separately, and reports an INSTANCE benchmark offline. Its online setting "only allow[s] the normalization method that has online version". From search snippets only (pages not opened): an EGUsphere review reply (egusphere-2023-1391, a different paper from FisH) where the authors concede their model does not run in real time; ETH Zurich EGU abstracts (EGU2013-8824, EGU2009-2841) comparing offline tests with real-time Virtual Seismologist performance; a USGS PLUM item pointing to data latency during the Ridgecrest sequence. None isolates the dataset preprocessing.
- **INSTANCE for EEW / online detection.** Snippets: an LSTM near/far classifier on INSTANCE (Springer 2023), a 2 s single-station intensity model (MDPI Remote Sensing 16(12):2159, https://doi.org/10.3390/rs16122159), FisH, and the Muenchmeyer benchmark. I found none that replays INSTANCE traces through a causal pipeline from raw miniSEED.
- **Zero-phase vs causal filter effect on picking delay.** Mechanism statements as above (Scherbaum & Bouin 1997 via snippet); no measured latency or trigger-time comparison for STA/LTA in EEW found.

## 4. What is already covered

- Real-waveform replay of EEW algorithms with event-level metrics (Williamson 2026, Zuccolo 2021, Meier 2017, Boese 2022), including target-site lead time (Zuccolo, Meier) and an open 8.4 GB test suite (Williamson, CC BY 4.0).
- Network congestion and failure effects on EEW detection time in a simulator (Portnoi 2014, abstract level).
- Live multi-algorithm testing on a common data feed (CREW, EPOS).
- Real-time playback and a causal default STA/LTA picker chain in production tooling (SeisComP `msrtsimul`, `scautopick`), and causal chunk processing in ObsPy (`obspy.realtime`).
- INSTANCE loading, window-based ML picker inference, and the offline picker benchmark (SeisBench, Muenchmeyer 2022).
- An explicit online-versus-offline evaluation for one new streaming picker (FisH).

## 5. What appears not covered, and how strong the evidence is

| candidate gap | evidence | strength |
|---|---|---|
| A matched comparison of the **released** INSTANCE counts (full-window detrended, integer) versus **causal processing of the same raw INGV waveform**, with trigger timing relative to the reviewed P pick and misses | no such study in the OpenAlex / WebSearch / GitHub results above; the INSTANCE paper and repo describe the processing but no paper found uses it this way | weak to moderate: limited indices, no citation chasing of INSTANCE (no cited-by list consulted), paywalled papers unread |
| Quantifying window-statistic dependence (mean/detrend/std normalisation) of pretrained SeisBench pickers in a causal replay versus the standard windowed evaluation | SeisBench source shows window-wide statistics in `annotate_batch_pre`; no streaming evaluation mode found in its code or docs; FisH addresses its own model only | weak to moderate |
| Seeded fault injection (delay, loss, outage) on a replay of **picked-trace** detector behaviour with a fixed manifest | QCN simulates network effects; SeisComP playback has no fault injection in the docs I read; Zuccolo uses a fixed 1 s delay | weak (QCN full text and Williamson/Meier/Boese methods unread) |
| An open, packaged, `pip install`-able replay and fault harness for detector plugins | found no such package on GitHub with my queries | weak (GitHub search is keyword-based; SeisComP tooling exists and is not pip-installable) |
| Public documentation that the INSTANCE counts are a window linear detrend plus an undocumented integer cast, reproducible to about 1 count on HH Z | our own pre-registered check (`docs/detrend_check_results.md`); the paper lists the steps but not the cast | moderate for the HH claim, nothing for HN |

## 6. Risks to novelty

1. The qualitative effect (non-causal filters move onsets earlier; whole-window detrending uses future samples) is textbook-level; a reviewer may call the P1 result expected. The contribution then has to be the size, the cohort, and the protocol.
2. Unread full texts (Portnoi, Williamson, Meier, Boese) may already contain faults or preprocessing comparisons.
3. Window normalisation inside ML pickers may be known to practitioners (it is in the code) and discussed in forums or theses I did not search.
4. SeisComP, ObsPy and CREW cover replay and live testing in mature form; a general framework (P3) invites direct comparison with them.
5. Our own limits: HH only, IV only, 88 comparable traces for the equivalence, and an offline arm that is the release (not an exact reproduction).
6. Licence: SeisBench is GPL-3.0; QuakeNode is MIT. Importing SeisBench from MIT code as an optional extra is a design that needs a legal check before distribution; do not vendor GPL code.
7. Name clash: "CREW" means the EPOS testing center in our Phase 1 notes and a dataset in SeisBench.

## 7. Candidate positionings

**P1. Narrow empirical study** (release product versus causal preprocessing on INSTANCE IV/HH Z, STA/LTA only).
- (a) Paper value: moderate to low as a stand-alone paper. It is well defined, cheap, and reproducible, but STA/LTA is a toy detector, the headline effect is expected qualitatively, and a result on one detector is easy to dismiss. It could be a data-practice note (a caution for users of the released product).
- (b) Open-source adoption: low. It is a script and a table.

**P2. P1 plus ML pickers** (SeisBench PhaseNet/EQTransformer in a causal streaming replay versus their standard offline-window evaluation on the same cohort).
- (a) Paper value: highest of the three if it works. The audience is large (users of INSTANCE and SeisBench), and the question (does offline evaluation overstate early-detection behaviour) is practical. Risks: confounds (the models were trained on windowed, normalised data; a causal arm must be designed so only the information available changes), compute cost, and the need for a pre-registered protocol and tolerance.
- (b) Adoption: moderate. A SeisBench streaming-evaluation recipe would be useful to that community, but the GPL licence constrains how it can be packaged.

**P3. General reproducible causal-replay and fault benchmark framework with P2 as the flagship.**
- (a) Paper value: diluted. A framework paper must be compared against SeisComP playback, ObsPy realtime, CREW and QCN-style simulators, and the novelty wording is hardest to defend.
- (b) Adoption: the highest ceiling and the highest maintenance cost; a pip-installable harness with plugins could be adopted, but only if the flagship result attracts attention first.

**Recommendation: P2, executed in two stages** (stage 1 = P1 as the guaranteed deliverable and the replay core already built; stage 2 = the SeisBench arm, gated by a small pre-registered pilot). Reasons: P1 alone is thin for a paper; P3 is premature and invites the most overlap; P2 answers a question practitioners actually have and uses the replay core as a vehicle rather than as the claim. If the pilot shows the confounds cannot be controlled, fall back to P1 as a short data note and keep the tool as supporting material.

**Minimum evidence before any novelty wording appears in the README or paper:**
1. Read the full text of Portnoi 2014, Williamson 2026, Meier 2017 and Boese 2022 (institutional or author access) and record whether they contain a preprocessing or fault comparison.
2. Citation-chase INSTANCE (Michelini 2021), SeisBench, Muenchmeyer 2022 and FisH in a database with a cited-by list (Scopus, Web of Science or Google Scholar), and read every hit that mentions streaming, causal, real-time or normalisation.
3. Search preprint servers (EarthArXiv, ESSOAr, arXiv physics.geo-ph) and the SeisBench, SeisComP and ObsPy issue trackers and forums for causal-versus-window preprocessing discussions.
4. Ask at least two domain experts whether they know of prior work.
5. Re-run and date-stamp the search log immediately before submission.
6. Have our own pre-registered result in hand; wording limited to "we are not aware of ..." with the search protocol and date stated.
