# Example: SYNTHETIC 5-station network

Research testbed, not an operational warning system. Everything in this example is **SYNTHETIC**: stations, event,
noise and signal are generated in-process (constant-velocity P arrival, an arbitrary amplitude decay, seeded Gaussian
noise). It exercises the software; it is not a seismological model and says nothing about real earthquakes.

Files:

| file | what it does |
|---|---|
| `config.yaml` | 5 stations, one event, `sta_lta_rms` detector, reordering buffer, three composed faults (fixed delay 0.3 s, exponential jitter, 10% Bernoulli loss), 3-of-5 fusion on the emission clock, 8 seeds |
| `config_recursive.yaml` | the same scenario with the `recursive_sta_lta` detector, for a side-by-side comparison |
| `sweep.yaml` | packet-loss sweep (`faults.0.p` = 0, 0.01, 0.02, 0.05, 0.1, 0.2) paired against a no-fault control, same 8 seeds |

Run from the repository root (each command takes a few seconds and writes a NEW directory under `runs/`):

```bash
quakenode validate examples/synthetic_network/config.yaml
quakenode run      examples/synthetic_network/config.yaml
quakenode run      examples/synthetic_network/config_recursive.yaml
quakenode sweep    examples/synthetic_network/sweep.yaml
quakenode report   runs/<a run or sweep directory>      # rewrite report.md and plots
```

A run directory contains `manifest.json`, `events.jsonl` (faults, detections, gaps, dropped packets, fusion decisions,
candidates), `metrics.json`, `metrics.csv`, `report.md` and `plots/*.png` (if matplotlib is installed). A sweep
directory contains `sweep_results.json`, `sweep_table.md/.csv`, `report.md`, `plots/sweep.png` and one full run
directory per point plus `runs/control`.

What to look at: lost packets make gaps, a gap resets the detector, and the detector then needs its LTA window of clean
data before it can detect again, so even a few percent of packet loss costs many detections in this configuration. That
is a property of the gap rule and the detector warm-up (see `docs/architecture.md`), shown on synthetic data.
