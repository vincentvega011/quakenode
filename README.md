# QuakeNode

# QuakeNode

[![CI](https://github.com/vincentvega011/quakenode/actions/workflows/ci.yml/badge.svg)](https://github.com/vincentvega011/quakenode/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10 | 3.11 | 3.12](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)

> **Research testbed, not an operational warning system.** Do not use QuakeNode to issue, suppress, or inform real alerts or any safety decision. The network scenarios it generates are **SYNTHETIC**: they exercise the software and are not a seismological model.

QuakeNode is an open-source Python package and research testbed for evaluating earthquake early warning (EEW) detectors as **causal streaming systems**. You describe a multi-station experiment in a YAML file; QuakeNode replays station data as packets on a logical clock, injects seeded network faults (delay, jitter, loss, outages, reordering, clock offsets), runs streaming detectors and a k-of-n fusion rule, and writes metrics, a report with plots, an event log and a reproducibility manifest. A sweep compares a range of fault settings against a matched no-fault control; `quakenode compare` runs one scenario under two settings (for example two detectors, two gap policies, or two input kinds) and pairs the results per station.

## Why this exists

A detector that looks good on a pre-processed, whole-window benchmark file has seen data that a live system would not have had yet, and a live system also sees late, lost and reordered packets. QuakeNode is a small software testbed for asking such questions in a controlled, repeatable way: every detector only sees the samples that the logical clock has delivered, every fault is seeded and logged, and every run writes a manifest. How a gap in the stream is handled changes the results a lot (see `docs/gap_policies.md`), which is why it is an explicit, configurable policy. Results from the synthetic scenarios support software-invariant claims only; see "Status and limitations".

![SYNTHETIC packet-loss sweep over three gap policies](docs/img/synthetic_gap_policy_sweep.png)

*Figure: SYNTHETIC data. Metric versus packet-loss probability for the 5-station example under the three gap policies
(median and IQR over 8 seeds; dashed = matched no-fault control). Produced by
`quakenode sweep examples/synthetic_network/sweep.yaml`.*

**How to read it.** Under the default `reset` policy a lost packet is a gap, the detector is reset and it is blind
until its 4 s LTA window has refilled, so even 1-2% loss removes many detections. With `hold` (state kept across the
gap) the same loss costs almost nothing, so the large sensitivity under `reset` comes from the reset rule plus the LTA
window length, **not from loss itself**. `zero_fill` is worse than both here because inserted zeros against the
scenario's baseline trigger the detector (labeled, and kept out of the metrics and the fusion rule). All of this is
SYNTHETIC; see `docs/gap_policies.md`.

## Quickstart (about a minute)

Requires Python >= 3.10. From a clone of this repository:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install ".[plots]"          # pyyaml is the only runtime dependency; matplotlib (plots) is optional
quakenode demo                  # writes ./quakenode_demo/{config.yaml,sweep.yaml} and runs the SYNTHETIC example
quakenode sweep quakenode_demo/sweep.yaml                                  # packet loss x three gap policies
quakenode run quakenode_demo/config.yaml --set pipeline.gap_policy=hold    # override any config value
quakenode compare quakenode_demo/config.yaml --a pipeline.gap_policy=reset --b pipeline.gap_policy=hold
```

`quakenode demo` needs no repository files (the example configs are packaged), so it also works after installing a built
wheel. The repository copies are in `examples/synthetic_network/`, including the detector comparison
`sweep_detector.yaml`. Each command prints the research-testbed banner, writes a **new** directory (never overwriting)
and prints its path. A run directory holds `manifest.json`, `events.jsonl`, `metrics.json`, `metrics.csv`, `report.md`
and `plots/`; a sweep prints a comparison table; `compare` writes `compare.md`, `compare.csv`, `compare.json` and a plot.
Other commands: `quakenode validate CONFIG`, `quakenode report RUN_DIR`, `quakenode version`. `--set key=value`
(repeatable, dotted paths) overrides any config value and is validated by the same strict schema; applied overrides are
recorded in the manifest. A detector switch needs that detector's own parameters, for example
`--set detector.name=recursive_sta_lta --set 'detector.params={sta_s: 0.5, lta_s: 4.0}'`. Walk-through:
`examples/synthetic_network/README.md`.

A condensed example of what `quakenode demo` prints (run directory names carry a timestamp and a random suffix):

```
$ quakenode demo
QuakeNode is a research testbed, not an operational warning system.
wrote quakenode_demo/config.yaml and quakenode_demo/sweep.yaml (SYNTHETIC example scenario)
run directory: quakenode_demo/runs/synthetic_network_demo-<timestamp>-<id>
report: quakenode_demo/runs/synthetic_network_demo-<timestamp>-<id>/report.md
```

(An animated terminal recording was not produced: no recording tool is part of the project's toolchain.)

## Status and limitations

- **Alpha research software, version 0.2.0.** The configuration schema and output files may change between minor versions
  (see `CHANGELOG.md`). It is not published on PyPI by this repository's tooling; install from a clone.
- Scenario data are **SYNTHETIC** unless a real recorded event is replayed (a tool demonstration on a few events). The
  synthetic results say nothing about real earthquakes, real networks, real detector performance, or warning times.
- Two built-in detectors (RMS STA/LTA first trigger; recursive STA/LTA) and one fusion rule (k-of-n). No location,
  magnitude, ground-motion or target-site warning-time estimation.
- Gap handling is a policy (`reset`, `hold`, `zero_fill`; nothing is interpolated), each with caveats
  (`docs/gap_policies.md`). With the default `reset` and a long LTA window, small loss rates remove many detections;
  that is a property of the policy and the detector, not of loss itself.
- Tested locally on macOS with Python 3.11 and 3.12. CI also runs Python 3.10 on Linux; see the CI workflow for the
  operating systems exercised. Windows has not been verified by the maintainers beyond what CI reports.
- Real-event replay is optional (extra `data`), uses the user's own copy of the INSTANCE v3 sample (CC BY 4.0, INGV)
  and ships no waveforms.

## What it does

```
YAML config -> SYNTHETIC traces -> packets (sample / ready / arrival times) -> seeded faults
   -> replay engine (a packet is visible only after its arrival time) -> streaming detectors
   -> k-of-n fusion -> metrics, events.jsonl, report, manifest
```

| module | purpose |
|---|---|
| `quakenode.config` | strict YAML validation (unknown keys rejected, ranges checked, errors name file and key) |
| `quakenode.scenario` | SYNTHETIC N-station network and event generator (constant-velocity P, arbitrary amplitude decay, seeded noise), and the scenario loader shared with real events |
| `quakenode.faults` | fixed delay, jitter (uniform, exponential), packet loss (Bernoulli, Gilbert-Elliott burst), duplicate, reorder, station outage, clock offset, missing samples; composed in declared order; each writes a `FaultRecord` |
| `quakenode.replay` | `Packet`, logical clock, replay engine and a receiver that only holds delivered packets |
| `quakenode.streaming` | `StreamDetector` protocol, detector registry, built-in `sta_lta_rms` and `recursive_sta_lta`, pipeline with configurable out-of-order (`reject`, `drop_late`, `buffer`) and gap (`reset`, `hold`, `zero_fill`) policies |
| `quakenode.fusion` | k-of-n event candidates on the emission (or arrival) clock, with a decision log |
| `quakenode.evaluation` | latencies, detection rates, false triggers, completeness, association latency, seed-paired fault sensitivity (`docs/metrics.md`) |
| `quakenode.manifest` | run manifest: config snapshot, seeds, git commit, versions, dataset records |
| `quakenode.data` | optional INSTANCE / miniSEED adapters and the real-event source (extra `data`); not needed for the synthetic workflow |

Design notes, the data-flow diagram and the four clocks (sample, ready, arrival, emission) are in `docs/architecture.md`.
Metric definitions are in `docs/metrics.md`.

## Replay a real recorded event (optional, tool demonstration)

With the extra `data` and your own copy of the INSTANCE v3 sample (CC BY 4.0, INGV), `source: instance_event` replays
one recorded event through the same chain: input `release_hdf5` (the INSTANCE release product, full-window processed,
**not causal input**) or `mseed` (raw INGV miniSEED, fetched politely by `scripts/fetch_dev_events.py`). Stations are
placed on one clock, the reference for per-station latency is the catalog P sample with its stated uncertainty, and
every output is labeled with the input kind and data source. Steps and configs: `examples/instance_event/`. A write-up
of what was run on 3 development events (not part of the paused pre-registered study) is in `docs/real_event_demo.md`:
**tool demonstrations, not performance evidence.** The repository contains no waveform data.

## Add a detector

Implement the streaming detector protocol (`quakenode.streaming.StreamDetector`): attributes `name`, `version`,
`warmup_s`, a `warming_up` flag, `reset()` (called after a gap) and `process(packet, processed_at_s) -> list[Detection]`,
which consumes ONE in-order packet. Then register a spec with its parameter table:

```python
from quakenode.streaming import DetectorSpec, Param, register_detector

register_detector(
    DetectorSpec(
        "my_detector",
        {"threshold": Param(float, 3.0, minimum=0.0, exclusive_min=True)},
        lambda params, processing_delay_s: lambda station, channel, rate_hz: MyDetector(params["threshold"], rate_hz),
    )
)
```

and use `detector: {name: my_detector, params: {threshold: 4.0}}` in a config. See `src/quakenode/streaming/detectors.py`
for two complete examples and `tests/test_pipeline_policies.py` for a minimal plug-in test.

## Add a fault

A fault is a frozen dataclass with a `type` and `apply(packets, seed) -> (packets, FaultRecord)` that only changes packet
metadata, presence or length, never sample values, and draws randomness only from `quakenode.faults.Stream(seed)`.
Add its parameter spec to `quakenode.config.FAULT_SPECS` and a branch in `quakenode.experiment.build_fault`. Include a
test with a pinned pattern for a fixed seed (see `tests/test_faults.py`).

## Earlier real-data research thread (paused)

An earlier research thread compared the released INSTANCE full-window detrended counts with causally processed raw
miniSEED. That work is paused in favour of the tool (decision D7); its documents, scripts and the frozen cohort list stay
in the repository and are not needed for the synthetic workflow: `docs/instance_access.md`,
`docs/detrend_check_results.md`, `docs/cohort_stage1_summary.md`, `docs/stage1_protocol_options.md` (draft). The
adapters are in `quakenode.data` (extra `pip install -e ".[data]"`).

## Related tools

QuakeNode does not claim to be the only tool for replaying waveforms through EEW or picking software, and it covers a
much smaller scope than the tools below. This list uses only what `docs/prior_art_artifact_check.md` recorded (audit date
2026-10-26; documentation and READMEs read, most code not run):

- **SeisComP** (AGPL-3.0): an acquisition, processing and distribution system. Its documentation describes the
  `scautopick` STA/LTA picker with a `--playback` option for non-real-time runs and `msrtsimul` for real-time playback of
  miniSEED. The documentation pages read describe no fault injection. QuakeNode is not a production system; it adds a
  small pip-installable replay with seeded faults and a manifest for detector experiments.
- **ObsPy** (`obspy.realtime`, LGPL-3.0): `RtTrace` processes periodically appended data packets with causal
  time-domain operations. It is a library for such processing, not an evaluation harness. QuakeNode's optional `data`
  extra uses ObsPy to read miniSEED.
- **SeisBench** (GPL-3.0): data-set loaders (including INSTANCE) and machine-learning pickers applied to windows of
  waveform. The audit found no streaming evaluation mode in its code or documentation. Because of its licence QuakeNode
  never vendors it or imports it from the core package.
- **OpenEEW** (Apache-2.0): an open accelerometer data set and code, with a data layout meant to allow the same
  processing in real time. A keyword search of its main repository found no replay or evaluation tooling; whether another
  repository in the organisation has some was not verified.
- Others recorded in the audit: the EPOS CREW testing centre (not the SeisBench CREW data set) and published replay
  studies (for example Zuccolo et al. 2021).

What QuakeNode adds, if anything, is for its own experiments to show. We make no novelty claim; the audit's checklist for
one is not complete.

## Development

```bash
pip install -e ".[dev,data,plots]"
ruff check . && ruff format --check . && pytest
```

See `CONTRIBUTING.md` and `CHANGELOG.md`.

## License

MIT (code only). Datasets and model weights have their own terms.
