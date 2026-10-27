# Synthetic causality proof of concept

**Status:** completed deterministic software experiment; not a real-waveform study and not an EEW performance evaluation.  
**Data:** generated in memory; no archive or network data accessed.  
**Dependencies:** Python standard library only.

## Question and hypotheses

The experiment asks whether full-window mean removal and least-squares linear detrending allow samples after a fixed cutoff to change processed values or fixed-detector decisions before that cutoff, and whether the preprocessing choices can alter the same detector's output on controlled signals.

**Hypothesis:** full-window mean removal and linear detrending change at least some pre-cutoff outputs under a suffix-only perturbation, while the specified one-sided baseline estimator and raw path leave those earlier outputs and decisions unchanged. On signals with a baseline trend, at least one fixed detector outcome (hit/miss or trigger time) may differ among preprocessing arms.

The null interpretation for the first claim is zero prefix difference and unchanged prefix trigger index for every arm. For the second claim, no detector-output differences across arms on the trended positive signals would weaken the synthetic example, while not disproving that offline operations are noncausal.

## Frozen synthetic protocol

Implementation: [`experiments/synthetic_causality.py`](../../experiments/synthetic_causality.py). The input is 20 seconds at 100 Hz (2,000 samples); the known P onset is sample 800 / 8.00 s. Each positive contains a 6 Hz sinusoid multiplied by `exp(-2.2*tau)`, beginning at P and ending at 0.8 s, with amplitude 1.0. Each trace also contains seeded Gaussian noise with standard deviation 0.08 arbitrary units.

The 12 fixed seeds are 202601 through 202612. Each seed is passed to a fresh `random.Random(seed)` generator. No shared or ambient random state is used. Signal cases are fixed in source:

| Case | P-like event | Baseline | Linear trend | Noise SD | Purpose |
|---|---:|---:|---:|---:|---|
| `trended_event` | amplitude 1.0 | 0.8 | 0.04 units/s | 0.08 | Positive with offset and drift |
| `flat_event` | amplitude 1.0 | 0 | 0 | 0.08 | Positive negative-control case for baseline detrending effects |
| `quiet_noise_control` | none | 0 | 0 | 0.08 | No-event negative control |
| `trend_only_control` | none | 0.8 | 0.04 units/s | 0.08 | No-event trend control |

The future-only counterfactual keeps sample indices 0–949 unchanged and modifies indices 950–1999 only by adding `2.0 + 0.25*(i-950)/100` units. Thus its first changed sample is at 9.50 s, 1.50 s after P. The same perturbation rule is applied to every seed and case. The fixed prefix comparison uses samples 0–949; trigger decisions are compared only through sample 949. This prevents a new trigger caused by the later perturbation itself from being counted as an earlier decision change.

### Preprocessing arms

- **Raw:** identity transform.
- **Offline mean removal:** subtract the arithmetic mean over all 2,000 samples.
- **Offline linear detrending:** fit one least-squares line over all 2,000 samples and subtract its value at each sample.
- **Causal one-pole baseline:** initialize the baseline estimate with the first observed sample (`m[0]=x[0]`); for each later sample use `m[n]=alpha*m[n-1]+(1-alpha)*x[n]`, output `y[n]=x[n]-m[n]`. `alpha=exp(-2*pi*0.5/100)=0.969072426305` (0.5 Hz parameter, 100 Hz sample rate). Carry the final `m` state across chunks. No gap or missing-sample behavior is simulated.

The causal estimator is a defined candidate for this synthetic test, not a recommended seismic filter or a claim of equivalence to a particular instrument or EEW preprocessing chain.

### Fixed detector and metrics

Every arm uses the same deterministic single-channel energy ratio. At each sample from index 109, calculate RMS over the current 10 samples (0.10 s STA) and RMS over the immediately preceding, non-overlapping 100 samples (1.00 s LTA). Trigger on the first index whose STA/LTA ratio is at least 3.0; otherwise return no trigger. There is no tuning by arm, no rearming, and no per-case threshold changes.

Primary software-causality outcomes:

1. Maximum absolute and RMS processed-prefix difference between original and suffix-perturbed traces, in arbitrary signal units.
2. Whether the first threshold crossing at or before index 949 changes, reported as changed trigger-index decisions / 12 seeds.

Detector outcomes on unperturbed traces:

- **Hit:** first detector trigger lies from the known P sample through P+2.00 s inclusive.
- **Miss:** no first trigger in that interval (including no trigger, or any trigger before P).
- **P-relative trigger shift:** `(trigger_sample - 800)/100` seconds, reported only for hits. This is synthetic detector delay relative to the known input onset, not warning time.
- **Control false trigger:** any trigger over the full 20-second unperturbed no-event control trace; denominator is 12 traces per control and arm.

The report does not use “accuracy.” All denominators are stated explicitly. All seed-level outputs are available with `--json`.

## Results

### Deterministic software-contract results

The future-only perturbation changed offline prefixes in all cases. Mean removal had maximum absolute and RMS prefix difference of **1.73840625 units**. Linear detrending had maximum absolute prefix difference **1.595037401431 units** and RMS prefix difference **0.81709259445 units**. Raw and causal one-pole prefixes were unchanged exactly (both differences 0). Across positive cases, offline mean and linear detrending changed the first trigger index by the cutoff in **12/12** seeds; raw and causal one-pole changed it in **0/12**. Both controls had no prefix trigger-index changes for any arm (**0/12**).

The new tests verify future-suffix independence, prefix detector-decision independence, chunk-boundary equivalence including an empty chunk, initialization from the first sample, preserved state across empty chunks, and no control triggers for the frozen controls and seeds. These are software contract checks only.

### Aggregate synthetic detector outcomes

| Signal case | Arm | Hits / 12 | Misses / 12 | Control false triggers / 12 | Mean P-relative shift (range), seconds |
|---|---|---:|---:|---:|---:|
| Trended event | Raw | 0 | 12 | — | no hits |
| Trended event | Mean removal | 12 | 0 | — | 0.040833 (0.04–0.05) |
| Trended event | Linear detrend | 12 | 0 | — | 0.025 (0.02–0.03) |
| Trended event | Causal one-pole | 12 | 0 | — | 0.024167 (0.02–0.03) |
| Flat event | Raw | 12 | 0 | — | 0.025 (0.02–0.03) |
| Flat event | Mean removal | 12 | 0 | — | 0.025 (0.02–0.03) |
| Flat event | Linear detrend | 12 | 0 | — | 0.025 (0.02–0.03) |
| Flat event | Causal one-pole | 12 | 0 | — | 0.024167 (0.02–0.03) |
| Quiet-noise control | All four arms | — | — | 0 / 12 each | not applicable |
| Trend-only control | All four arms | — | — | 0 / 12 each | not applicable |

The offline arms changed exact trigger indices under the suffix perturbation in both positive cases while preserving all 12/12 hits within the declared horizon. This means the counterfactual can affect timing even when the binary hit/miss outcome is stable. On the trended positive, raw input missed 12/12 while the three baseline-removal methods detected 12/12. The flat-event and no-event controls behaved as intended under this detector and parameterization. Full per-seed trigger indices and differences are emitted by the JSON mode.

## Reproduction and tests

Run the aggregate experiment:

```sh
python3 experiments/synthetic_causality.py
```

Run with all protocol values and per-seed outcomes as JSON:

```sh
python3 experiments/synthetic_causality.py --json
```

Run the preserved original contract tests and the focused experiment tests:

```sh
python3 -m unittest -v tests/test_streaming_preprocessing_contract.py tests/test_synthetic_causality.py
```

**Test result:** 7 tests ran and passed. The original `tests/test_streaming_preprocessing_contract.py` was left unchanged. No external packages were installed. The experiment and JSON-output commands were run in this workspace; JSON parsed successfully with four cases and twelve seeds.

## Limitations and interpretation

These generated waveforms are simple, stationary Gaussian-noise examples with one analytic pulse, fixed smooth trends, no clipping, gaps, instrument response, sample-clock error, multiple phases, station association, or network arrival delay. The high-pass candidate and STA/LTA parameterization are intentionally fixed examples, not seismologically calibrated choices. The result demonstrates that these particular full-window transforms depend on future samples and that this dependence changed a particular fixed detector's trigger indices in these synthetic cases. It also shows an illustrative trend-related raw-versus-preprocessed detector difference under the stated model.

This does not validate behavior on INSTANCE or any real earthquake waveform, reproduce INSTANCE preprocessing, establish detector superiority, estimate earthquake recall or false-alert rates, estimate warning time, support operational EEW claims, or resolve the project's novelty question. The detector results are conditional on the chosen signal equations, noise scale, trend values, filter, threshold, and 12 deterministic seeds; they are not a population estimate. Synthetic results are not validation on real earthquake records.
