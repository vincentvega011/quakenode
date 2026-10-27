# Metric validity matrix after remediation review

**Checked:** 2026-10-26. Source-based assessment only; no dataset sample/metadata has been downloaded or counted.

## Population boundary

INSTANCE event stations were selected where manually reviewed P picks contributed to preferred locations, under residual/weight criteria. The paper aims for one P (and possibly S) per window but acknowledges additional unidentified earthquakes can occur. Noise examples are selected clips, not continuous exhaustive negatives; hidden events may occur. Exact HNZ coverage and v3 field mapping remain unverified.

The strongest immediate estimand is **per-trace detector behavior conditional on an accepted bulletin P pick and inclusion in the curated INSTANCE cohort**. The proposed protocol has one HNZ trace detector, no event fusion, no alert issuance/delivery, and no target threshold time.

| Metric / claim | Validity now | Defensible denominator/reference and interpretation | What it cannot establish |
|---|---|---|---|
| P-relative trigger emission latency | Conditional on causal input and verified time map | Eligible picked trace; emission time on simulation clock mapped to UTC minus reviewed P, seconds | Not origin-to-alert or delivered warning time. Current HDF5 path is noncausal. |
| Trigger-by-P+H / miss fraction | Picked-trace metric only | No qualifying trigger in [P,P+H] divided by all eligible P-picked traces; state H/exclusions | Not station recall, event miss rate or network coverage; selection conditions on accepted picks. |
| Restricted detection time | Conditional descriptive composite | First trigger in [P,P+H]: min(emission−P,H), else H; report pre-P separately | Not warning utility; depends on horizon, P uncertainty, detector and cohort. |
| Conditional latency among detections | Conditional; report with misses | Emission−P for qualifying detected traces | Alone can hide misses and make a degraded detector appear faster. |
| Pre-P triggers / duplicates | Conditional | Counts/proportion per eligible picked trace under frozen matching interval | Not definitely false; other seismic signals may occur. Not false event alerts. |
| Triggers in labeled noise clips | Conditional, narrow | Raw unmatched count / valid analyzed trace seconds, reported as sampled trace-hour plus exposure | Not operational false alerts per calendar hour/day. Clips are not exhaustive negatives; HNZ noise coverage unverified. |
| Event match / event recall | Unsupported by current protocol | Requires event-level fusion, association, complete event cohort and spatial/time match | Single-channel trigger is not an event association. |
| System-wide missed-earthquake rate | Requires scope/data change | Continuous declared network/time population, station availability, independent sufficiently complete catalog and event matching | Curated traces condition on reviewed P pick in preferred event solution. |
| Operational false-alert rate | Requires scope/data change | Continuous valid network exposure, alert outputs and adjudication | Selected snippets cannot establish calendar-time false-alert rate. |
| Simulated delivery-fault effect | Conditional sensitivity only | Same fixed records/detector under paired no-fault and pre-generated fault schedule | Not empirical network reliability. Current 1 s, p=5%, 250 ms and onset blackout are exploratory with no telemetry calibration. |
| Station outage resilience | Unsupported | Needs multiple station streams and fusion; outage removes station streams | One HNZ channel gap is not a station/network outage. |
| Target-site warning time | Unsupported/out of scope | Target threshold time minus alert delivery time, common clock; allow nonpositive times | No target site/threshold and no alert issue/delivery model. |
| PGA/PGV threshold time | Potentially derivable after separate validation | Response-removed physical-unit target trace, verified response and explicit threshold | Does not alone yield warning time. Protocol selects counts; paper notes possible physical-product errors. |
| Accuracy | Do not report | No classification unit or denominator | Undefined in this design. |
| Causal correctness | Software invariant, not performance metric | Whole-chain future counterfactual and arrival-cutoff tests | Cannot be inferred from design/API or tests on already detrended arrays. |

## Additional data/methods required

- **Event recall:** continuous/systematic streams for all available stations in a defined region/time; independent catalog/completeness; station availability; fusion and frozen matching.
- **Operational false-alert rate:** long continuous background/event exposure, complete trigger/alert association and adjudication of potentially uncatalogued events.
- **Station outage impact:** multistation streams, station identity/availability and fusion.
- **Warning utility:** target-site physical waveform/response, explicit shaking threshold, geometry, alert issue/delivery semantics and reconciled clocks.
- **Empirically realistic faults:** observed telemetry arrival/loss/outage measurements and explicit packet/timestamp model. Otherwise faults remain hypothetical.

## Evidence checked

- Michelini et al. (2021), [INSTANCE DOI](https://doi.org/10.5194/essd-13-5509-2021), §§2.1–2.3; official [release page](https://www.pi.ingv.it/banche-dati/instance/).
- Current draft: evaluation_protocol.md §§4–16 and experiments/configs/phase1_protocol.yaml.
- Williamson et al. (2026), [EPIC Alaska replay, DOI 10.1785/0120260139](https://doi.org/10.1785/0120260139).

