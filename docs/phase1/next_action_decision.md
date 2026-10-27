# QuakeNode next-action decision

**Decision date:** 2026-10-26  
**Verdict: NO-GO for the main pipeline and proposed packet-loss experiment.** A bounded evidence-gathering phase is reasonable; this is not approval to implement the main study.

## Current reality

The workspace contains Phase 1 plans and a draft YAML, no Git metadata, source code, data, dependencies, CI or tests. unittest discovery finds zero tests. The proposed INSTANCE sample has not been accessed. The data paper documents full-window detrending/resampling before the selected HDF5 product, which cannot serve as causal primary input without a scope change. Reviewed-P selection limits valid outcomes to picked-trace behavior. QCN, CREW, Zuccolo et al. and EPIC Alaska establish substantial prior art for network-fault simulation, real-time testing, streaming comparison and multistation replay. The candidate preprocessing comparison remains unverified as novel.

## Preserve

- Preserve all Phase 1 reports, ADR, protocol draft and YAML as a record of assumptions and decisions.
- Preserve picked-trace denominators in metric_validity_matrix.md.
- Preserve separate sample/arrival/emission clocks, deterministic scenarios and future-counterfactual requirements as proposed invariants.
- Keep synthetic causality checks separate from real-waveform detector evidence.

## Fix

- Retire “causal HNZ replay from INSTANCE v3 HDF5” as a valid causal-input path.
- Enumerate the cohort only after metadata and time fields are inspected; event_ids is currently null.
- Establish raw miniSEED access and per-network license/terms before final dataset selection.
- Recover transform provenance or treat HDF5 strictly as an offline comparator.
- Freeze a causal input method independently and verify it with whole-path counterfactual tests.
- Restrict outcome claims to P-picked trace behavior; no system recall, continuous false-alert rate or target warning time.

## Defer

- Main replay/fault pipeline, detector plugins, fusion, alerts, dashboard, sensors and broad fault engine.
- Dependency additions; no implementation need or stack has been validated.
- Novelty and system-level EEW claims.
- Waveform redistribution until actual network terms are known.

## Next three actions

1. **Metadata/access feasibility, no large download:** establish whether the official sample has a small metadata sidecar/index and determine its size before retrieval. Enumerate HNZ event/noise rows, P/start/rate/units/quality fields and candidate IDs. For a small frozen subset, check original EIDA availability and each network's terms. Stop if exact records cannot be matched. Do not transfer waveforms until scope and terms are documented.
2. **Artifact-level prior-art check:** inspect QCN full methods and any reproducible code/config; retrieve EPIC's cited test-suite record and inspect contents/license/rerun steps; search the exact causal-vs-offline preprocessing question and record search limits.
3. **Only if 1–2 succeed:** choose causal raw-count processing and fixed STA/LTA settings from documented method defaults or separate development data; amend protocol for same-record preprocessing comparison and picked-trace metrics; implement/run the minimum synthetic and raw/release-pair counterfactual tests. Obtain independent review before main pipeline work.

## Minimum experiment proposal

- **Input/provenance:** matched original miniSEED, StationXML and reviewed bulletin P picks. Record actual network DOI/license, request parameters and checksums. Exact records/access remain unresolved.
- **Streaming path:** preserve native sample rate/time and decode incrementally; do not batch detrend, normalize or resample. Start with raw counts. If a baseline correction is required, a concrete causal candidate is a one-pole high-pass expressed as a recursive baseline estimate: m[n] = αm[n−1] + (1−α)x[n], y[n] = x[n]−m[n], with α = exp(−2πfc/fs). It consumes only current/past samples and carries m as state. Select fc from a documented detector recipe or a separate development set; no fc is currently justified. Initialize from the first observed sample, suppress scoring during a fixed contiguous warm-up, carry state across chunks, and reset/re-warm after gaps without filling them. Validate transient and frequency response before use. This candidate is not implemented or validated.
- **Replay:** deterministic virtual clock, fixed packet boundaries, contents hidden until arrival; keep sample time, packet-ready, arrival and emission separate.
- **Detector:** fixed classic STA/LTA as a proposed interface/configuration, one HNZ channel, no fusion.
- **Conditions:** clean stream primary control; optional deterministic single-packet gap as a secondary recovery stress test, not a representative network model. Add calibrated delay/loss only if target telemetry evidence exists.
- **Metrics:** P-relative first trigger time and miss-by-horizon for eligible reviewed-P traces; pre-P/duplicate triggers separately. Noise clips support a sampled trace-hour trigger rate only if HNZ coverage/labels are confirmed. No system recall, operational false-alert rate or warning time.
- **Saved outputs:** versioned config; trace manifest/exclusions; dataset DOI, license/terms, request parameters and checksums; code revision once Git exists; runtime/dependency lock; fault schedule/seed; raw per-trace emissions/gaps; event-level metrics and denominators; logs and rerun command.

This proposal is not ready to implement because records, transform settings, sample schema and research gap are unverified.

## Tests before a full system

No implementation or data fixtures exist, so test implementation is blocked. Specifications are in causal_preprocessing_audit.md. Minimum suite:

1. Hold waveform prefix through k fixed and alter only future samples; all pre-k preprocessing/statistic/trigger/emission outputs must match within justified tolerance.
2. Delay/alter packets after T; outputs through T remain unchanged.
3. Compare one-sample, irregular and packet chunking with state carried.
4. Test initialization/warm-up; no emissions until warm-up completes.
5. Insert a known gap; verify no fill, reset and declared recovery.
6. Test sequence ordering/duplicates; reject or explicitly buffer out-of-order packets.
7. Hand-check STA/LTA arithmetic and metric denominators on tiny synthetic fixtures.

No synthetic result can establish detector performance on real earthquakes. The only test run was discovery: python3 -m unittest discover -v, exit 0, **0 tests**; it is not a passing behavior test.

## Remaining blockers and GO threshold

1. **No Git metadata:** commit history and prior uncommitted state unavailable. Minimum evidence: intended Git checkout or explicit source-snapshot provenance.
2. **No data/metadata:** cohort, rate, timing, HNZ/noise coverage and rights unknown. Minimum evidence: trace inventory and legally cleared matched raw/release specimen.
3. **No causal implementation/tests:** no function path exists. Minimum evidence: frozen transform contract and passing whole-chain future, chunk and gap tests.
4. **Research gap unresolved:** broad overlap with QCN, EPIC, CREW and streaming utility. Minimum evidence: QCN/EPIC artifact review, focused literature search, and a consequential nonduplicate outcome.
5. **No declared runtime/dependencies:** host Python 3.9.6 does not establish compatibility. Minimum evidence: choose a supported version/stack only when a small vertical slice is justified.

The verdict can move to **CONDITIONAL GO for a feasibility/conformance slice** after data/access and Git/source provenance are established and the narrower question is independently reviewed. GO for the main experiment requires a matched legal cohort, passing causal tests, defensible denominators and a nonduplicative contribution. If the preprocessing question is already covered or records cannot be matched, pause or limit work to a clearly labeled software conformance artifact.

