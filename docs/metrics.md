# Metrics

Research testbed, not an operational warning system. For the synthetic scenario every number comes from SYNTHETIC
data, so the metrics describe software behaviour under the configured faults, not real earthquakes. For a real
recorded event (`source: instance_event`, tool demonstration) the same metrics are computed against the catalog P
sample of each station; see "Real recorded events" below.

Definitions are implemented in `src/quakenode/evaluation/metrics.py` and checked by hand-computed tests in
`tests/test_metrics.py`. Times are seconds. **Sample clock** = time of the sample at the sensor; **emission clock** =
simulated time at which the detector emitted (see `docs/architecture.md`).

## Truth and windows

- `P_s` = true P arrival of the synthetic event at station `s`, on the sample clock (origin time + hypocentral distance / velocity).
- A detection is a **hit** for station `s` if its trigger sample time lies in `[P_s - pre_margin, P_s + post_horizon]`
  (`metrics.detection_pre_margin_s`, default 1 s; `detection_post_horizon_s`, default 10 s). The station's first hit
  (earliest trigger sample time) defines its latencies.
- A **pre-event (false) trigger** is a detection with trigger sample time `< P_s - pre_margin`.

## Per station and seed

| metric | definition |
|---|---|
| `detected` | true if the station has a hit; `None` if the scenario has no event |
| `sample_latency_s` | first hit's trigger sample time minus `P_s`. Detector delay on the **sample clock**; unaffected by packetization, network or buffering. `None` if not detected |
| `emission_latency_s` | first hit's emission time minus `P_s`. Includes the detector delay, waiting for the rest of the packet, network delay/jitter, reordering-buffer waiting and the processing delay. `None` if not detected |
| `reported_timestamp_error_s` | reported (sensor-clock) trigger time minus true trigger sample time; `None` unless a `clock_offset` fault was applied |
| `false_triggers` | number of pre-event triggers (for a noise-only scenario: every detection) |
| `scored_pre_event_s` | seconds of pre-event data in which a false trigger could be counted: `max(0, P_s - pre_margin - detector warm-up)`; for a noise-only scenario `max(0, duration - warm-up)`. This is the denominator of the false-trigger rate |
| `completeness` | samples handed to the detector / samples generated. Lost, dropped (late or duplicate) and truncated packets reduce it; duplicates do not raise it |

Latencies are defined **only for detected stations**, so they are conditional on detection (a fault that removes the
slow stations can lower the median latency). Always read them together with `detection_fraction`.

## Per seed (aggregated over stations)

| metric | definition |
|---|---|
| `detection_fraction` | detected stations / stations (event scenarios) |
| `median_sample_latency_s`, `median_emission_latency_s` | median over detected stations (linear-interpolation quantile); `None` if none |
| `mean_completeness` | mean of the station completeness values |
| `false_triggers` | sum over stations |
| `false_trigger_rate_per_station_hour` | `false_triggers / (sum of scored_pre_event_s / 3600)`; `None` if no scored time |
| `event_detected` | 1 if a **true candidate** exists, else 0 (`None` if fewer than k stations have a P time) |
| `association_latency_s` | creation time (emission clock) of the first true candidate minus the reference time, `None` if none |
| `false_candidates` | candidates that are not true |

**Reference time** = the k-th smallest true P arrival over all stations: the earliest moment at which k stations could
have had a P arrival. A candidate is **true** if at least k of its contributing detections are hits (each station's
first hit). The reference is built from the truth, so a lost packet or an outage does not move it.

A first-trigger detector (`sta_lta_rms`) fires once per stream: a pre-event false trigger uses up the detector and
masks the real detection at that station. This is a property of that detector, not of the metric.

## Across seeds

- `summary_over_seeds[metric]`: `n` (seeds), `n_defined`, `median`, `q1`, `q3` (type-7 linear-interpolation
  quantiles), `min`, `max`, `mean`, over the seeds where the metric is defined.
- `event_detection_rate`: `k` of `n` seeds with `event_detected = 1`, the rate, and the Wilson 95% interval.
- `per_station[station]`: detection rate over seeds, latency distributions, completeness distribution, total false triggers.

## Fault sensitivity (sweeps)

For each sweep point and each headline metric, `paired_vs_control` pairs **seed by seed** with the no-fault control run
on the same seeds (same synthetic traces, because the scenario seed does not depend on faults):

`difference(seed) = metric(point, seed) - metric(control, seed)` for seeds where both are defined.

Reported: `n_seeds`, `n_paired`, `n_undefined` (seed excluded), counts of positive / negative / zero differences, the
distribution of the differences (median, quartiles, min, max) and a seeded 95% percentile bootstrap CI of the median
difference (2,000 resamples of seeds; `metrics.bootstrap_seed`, `null` disables it). With few seeds, treat the CI as
rough.

## Gap policy and filled samples

The gap policy (`pipeline.gap_policy`, `docs/gap_policies.md`) is named in `metrics.json` (`gap_policy`), the report and
every event line. Extra per-seed values: `gap_events` (number of gaps), `missing_samples_total` (indices skipped),
`filled_samples_total` (zeros inserted by `zero_fill`) and `detections_on_filled_samples`. A detection triggered on a
filled sample is not a hit and not a false trigger; it is counted only in `detections_on_filled_samples` and, by
default, kept out of fusion. `completeness` counts recorded samples only; per-station `filled_samples` is reported
beside it.

## Real recorded events

For `source: instance_event` the reference for station `s` is the catalog P sample (`trace_P_arrival_sample`) on a
shared timeline whose zero is the earliest trace start of the event; hits, `sample_latency_s` and `emission_latency_s`
are measured against it exactly as above. The stated P uncertainty (`trace_P_uncertainty_s`) is reported next to each
station (`p_uncertainty_s`) and is NOT used to widen the hit window (that stays `detection_pre_margin_s` /
`detection_post_horizon_s`). The event reference time defaults to the **earliest** catalog P time
(`metrics.event_reference: earliest_p`; synthetic scenarios default to `kth_p`). The catalog picks are reviewed
picks, a reference rather than truth. Outputs carry the input kind (`release_hdf5` or `mseed`).

## Not measured

Warning time at a target site, ground-motion prediction, location or magnitude error, and operational false-alert
rates are not metrics of this tool. The synthetic scenario has no ground motion model.
