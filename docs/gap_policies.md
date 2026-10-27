# Gap policies

Research testbed, not an operational warning system. A **gap** appears when a packet starts after the next expected
sample index of its station/channel stream (a packet was lost, an outage lasted, samples were missing, or a buffered
packet never arrived in time). The pipeline option `pipeline.gap_policy` decides what happens to the detector.
Nothing is ever interpolated. Every policy logs a `GapEvent` with the policy name, the missing sample count and the
number of filled samples; `events.jsonl` lines carry `policy`, `missing_samples`, `filled_samples` and `state_kept`,
and `metrics.json`, `report.md` and every `events.jsonl` line name the policy.

| policy | detector and filter state | samples inserted | what it means |
|---|---|---|---|
| `reset` (default) | reset; the detector re-warms from the packet after the gap | none | the strict rule: after a gap the detector knows nothing about the past |
| `hold` | kept | none | the next packet continues the stream as if the gap were not there |
| `zero_fill` | kept | zeros for every missing index, fed through the detector | the missing time is occupied by zeros |

## reset

The previous behaviour (so existing results are unchanged). With a detector that needs a long window (an LTA of
several seconds) the detector is blind for one full warm-up length after every gap. In the SYNTHETIC example sweep this
alone explains most of the sensitivity to packet loss: with `hold` the same loss costs almost nothing (see the README
figure and `examples/synthetic_network/sweep.yaml`). The sensitivity under `reset` therefore comes from the reset rule
plus the LTA window length, not from loss itself.

## hold

A fault-tolerance policy, **not a repair**. Filter state and detector buffers are kept and no samples are inserted, so
the data on both sides of the gap are glued together:

- windowed statistics (STA, LTA, RMS, baseline estimates) span the discontinuity and mix samples that are not
  adjacent in time; a recursive average treats the new sample as the next one;
- the sample index and sample time of detections stay true (they come from the packet), but the detector's internal
  windows no longer correspond to a fixed time span;
- a step across the gap (different baseline or amplitude on the two sides) enters the statistics as if it had
  happened in one sample interval.

The discontinuity is recorded as a `GapEvent` with `state_kept: true`.

## zero_fill

Zeros are inserted for the missing indices and processed by the detector like data. They are **labeled**: the gap
event carries `filled_samples`; a detection whose triggering sample is one of the inserted zeros has
`on_filled_samples = true`; the run records `filled_samples` per station and `filled_samples_total` per seed.

Bias risk: zeros are arbitrary. On data with a baseline offset (raw counts, or the SYNTHETIC scenario's baseline of
800) the filled stretch is a large step against the baseline, which a baseline-removal filter and an STA/LTA detector
see as a strong transient: **inserted zeros can trigger the detector**. A first-trigger detector then spends its one
trigger on the artefact and can miss the real event. On zero-mean data (the INSTANCE release product is detrended)
the effect is much smaller. Neither is a property of the earthquake signal; both come from the fill.

How the rest of the tool treats filled samples:

- **Metrics:** detections triggered on filled samples are not evidence. They are left out of station hits and of
  the false-trigger count and reported separately (`detections_on_filled_samples`). Completeness counts recorded
  samples only; filled samples are reported next to it.
- **Fusion:** `fusion.exclude_filled_detections` (default `true`) keeps detections triggered on filled samples out of
  the k-of-n rule; each excluded detection is logged as a `fusion` decision `excluded_filled_detection`. With `false`
  they enter fusion like any detection.
- A detection just AFTER a filled stretch can still be contaminated (its windows contain zeros) without being flagged;
  only the triggering sample is checked.

## Which policy should I use?

None of them is "correct"; they are assumptions about what the missing data would have looked like. `reset` is the
conservative default, `hold` is the most tolerant of loss but glues unrelated data together, `zero_fill` makes the
gap visible as data and is the most likely to create artefacts. Compare them with a sweep (`quakenode sweep
examples/synthetic_network/sweep.yaml`), always against the matched no-fault control.
