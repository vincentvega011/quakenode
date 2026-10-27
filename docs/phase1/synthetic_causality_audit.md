# Independent audit: synthetic causality proof of concept

**Audit scope:** code and report review, documented reproduction, focused tests, and isolated mutation checks. No implementation or test source was changed during the audit.  
**Runtime:** Python 3.9.6.  
**Recommendation:** **REVISE** before treating the detector comparison as evidence about causality. The prefix-dependence proof of concept is sound for the implemented functions; the detector differences need a narrower interpretation and a small record of the protocol's provenance.

## Findings

| # | Status | Finding | Evidence and impact |
|---:|---|---|---|
| 1 | **PASS** | The counterfactual holds the prefix fixed and changes only later samples. | [`synthetic_causality.py:66-72`](../../experiments/synthetic_causality.py) copies the input and changes indices `cutoff..end`; the fixed cutoff is 950 (`P_INDEX + 150`) at lines 17-26. [`test_synthetic_causality.py:20-35`](../../tests/test_synthetic_causality.py) asserts bitwise-equal raw prefix values, nonzero offline prefix effects, and unchanged causal prefix/first trigger decision. The experiment compares through index 949 at lines 184-191. |
| 2 | **PASS, with a narrow scope caveat** | The implemented one-pole recurrence has no indirect future dependency in the experiment path. | [`synthetic_causality.py:91-108`](../../experiments/synthetic_causality.py) initializes from the first sample and updates only from the current input and prior state. The experiment calls it with default `state=None` and fixed alpha at lines 169-180. There is no normalization, padding, or offline filter stage in this path. The detector's STA/LTA windows use the current and preceding samples only (`:127-137`). Chunk processing carries the returned state (`:111-124`). However, the aggregate experiment processes each array in a single call; chunk behavior is tested separately, not exercised in the aggregate run. The function API also permits caller-supplied state/alpha, so causal provenance depends on the caller; this run uses neither future-derived state nor custom alpha. |
| 3 | **CONCERN** | The detector and window are fixed across arms, but the arms are not response-matched. | All four arms call the same first-trigger function and use the same 20 s signal and detector constants ([`synthetic_causality.py:127-150,157-215`](../../experiments/synthetic_causality.py)). This is fair for comparing these four specified transforms. The causal one-pole's frequency response and initialization transient differ from the global mean and least-squares residual transforms. There is no delay compensation or matched transfer-function control. The observed hit and timing changes therefore cannot be attributed solely to future-sample dependence; filtering, amplitude/background scaling, and edge behavior also contribute. The report calls the filter illustrative but should make this causal-attribution limit prominent. |
| 4 | **CONCERN / UNVERIFIED** | It cannot be established from the artifacts that all choices were fixed before aggregate results were examined. | Signal cases, seeds, perturbation, thresholds, horizon, and metrics are explicit in code and report ([`synthetic_causality.py:15-45,157-253`](../../experiments/synthetic_causality.py); [`synthetic_causality_experiment.md:15-55`](synthetic_causality_experiment.md)). But the workspace has no `.git` metadata, preregistration, timestamped protocol snapshot, or run manifest connecting a frozen specification to the first result. The word “frozen” describes the present implementation, not independently verifiable pre-result commitment. The report should say this plainly. |
| 5 | **PASS within a runtime; CONCERN across runtimes** | Seeds and all planned cases are reproducibly enumerated and aggregated. | Each case uses all 12 listed seeds (`:27`, `:162-166`); each seed gets a fresh `random.Random(seed)` (`:48-63`). Results loop across all four cases and all four arms and emit aggregate plus per-seed values (`:157-253`). The documented command reproduced the displayed result table. Python version was 3.9.6 in this audit, but the JSON manifest does not record the Python version or source hash. The standard-library random stream is not an environment lock; exact cross-version bitwise reproduction is therefore unverified. |
| 6 | **PASS, limited coverage** | The controls are meaningful checks for this narrow synthetic setup. | `quiet_noise_control` and `trend_only_control` have no event and produce zero full-window triggers across all 12 seeds/arms; the unit test asserts this (`synthetic_causality.py:40-45,212-215`; [`test_synthetic_causality.py:57-61`](../../tests/test_synthetic_causality.py)). `flat_event` supplies a no-trend positive control: all arms hit all seeds, although trigger indices can differ. These controls can expose gross threshold or trend-only-trigger errors in this fixture. They do not calibrate a real-world false-trigger rate or establish that the synthetic noise/trend distributions are representative. |
| 7 | **CONCERN** | Detector differences may reflect preprocessing response and scaling, not only causal leakage. | The detector is a raw RMS ratio with a zero-only LTA guard and a fixed threshold (`synthetic_causality.py:127-137`). Subtracting a global mean, a global line, or an exponential baseline changes the local energy and transient response differently. The report does not include transfer-function, group-delay, or scale-matched controls. The future-suffix comparison does isolate noncausal dependence for the two offline operators: it changes earlier outputs while input prefixes are identical. But the across-arm detection comparison combines that effect with each operator's distinct signal response. No confirmed code defect here; this is a causal interpretation limitation. |
| 8 | **PASS** | Trigger sample indices and P-relative time arithmetic are consistent with the declared grid. | The code sets `P_INDEX=int(100*8)=800` (`synthetic_causality.py:15-18`) and computes `(trigger_index-P_INDEX)/FS_HZ` (`:205`, aggregate `:226-230`). The hit interval includes indices 800 through 1000 (`:140-146`), corresponding to P through P+2 s. It reports sample-grid timing in 10 ms increments; no sub-sample onset estimate is claimed. The generated pulse begins at sample 800 (`:57-62`). |
| 9 | **PASS** | Focused tests detect representative future-leakage and chunk-state regressions. | With isolated in-memory test doubles (no file edits), replacing the causal recurrence with complete-window mean removal caused `test_future_changes_affect_offline_prefix_but_not_causal_prefix_or_decision` to fail. Replacing the chunk helper with a version that reinitialized each chunk caused its chunk-equivalence test to fail. Replacing the preserved original contract helper with a version that ignored the passed state caused the original chunk-boundary test to fail. All three mutations were detected. |
| 10 | **PASS, with one requested clarification** | The report avoids claims of real-record or operational performance, but should explicitly narrow the detector interpretation and preregistration status. | [`synthetic_causality_experiment.md:104-108`](../../docs/phase1/synthetic_causality_experiment.md) states that this is not real-waveform validation, not EEW performance, and not a novelty result. It accurately reports the synthetic outcomes. However, the causal-filter versus offline detector difference is not isolated from response/delay/scaling, and the artifacts cannot establish pre-result freezing. Those qualifications should accompany any reuse of the result. |

## Reproduction evidence

Commands run in the workspace:

```sh
python3 experiments/synthetic_causality.py
python3 -m unittest -v tests/test_streaming_preprocessing_contract.py tests/test_synthetic_causality.py
```

The experiment reproduced all four cases and 12 seeds per case. It reported, among other values, 12/12 trended-event misses for the raw arm versus 0/12 for each detrending arm, 12/12 future-perturbed prefix-trigger-index changes for both offline detrenders on both event cases, and 0/12 for raw and causal one-pole. Each no-event control had 0/12 triggers in every arm.

Test output: **7 tests ran; all passed** (2 preserved original contract tests and 5 focused experiment tests). The mutation checks described above each caused the intended test to fail. They were temporary Python monkeypatches and did not modify committed source files.

## Defects, limitations, and unverified assumptions

### Confirmed defects

No confirmed future leakage was found in the active `causal_baseline` experiment path, and no index-to-time conversion defect was found. The tested mutation cases were detected.

### Methodological limitations

- The causal high-pass-like recurrence is not transfer-function matched to full-window mean removal or linear detrending. Their detector outputs are not a clean estimate of the effect of causality alone.
- Signal levels, trend sizes, pulse form, filter cutoff, and detector threshold are synthetic choices in arbitrary units, not empirically calibrated seismic values.
- Chunking invariance is unit-tested but the aggregate experiment does not deliver chunks through the causal arm.
- The hit/miss detector metric reports the first crossing only; an early crossing before P makes that trace a miss even if a later crossing would occur. This is a defined one-trigger detector rule, not a multi-trigger association metric.
- The trigger shift is relative to the known synthetic onset and must not be called warning time.

### Unverified assumptions

- No artifact proves that the signal, threshold, and metric specification was frozen before the aggregate outcomes were first viewed. The repository has no Git history or run-manifest snapshot to establish that chronology.
- Exact random streams and output values across Python versions were not verified; the audit runtime was Python 3.9.6, which is not recorded in the experiment JSON.

## Smallest recommended revisions

1. Amend the report's interpretation to state that the suffix counterfactual isolates future dependence of the offline transforms, while detector differences across arms also include filter response, scaling, and initialization effects.
2. Mark pre-result specification chronology as unverified unless a timestamped/hash-identified protocol snapshot exists. Do not describe choices as preregistered.
3. For stronger reruns, record Python version and source/config hash in JSON. If the aggregate is later presented as a streaming experiment, run the causal arm through chunk delivery in the aggregate path; the current standalone chunk tests establish the recurrence contract but not the complete experiment plumbing.

These are documentation and evidence improvements first. A response-matched detector study would be a separate experiment and should not be added without review.

## Final recommendation

**REVISE** — accept the prefix-causality demonstration as a valid synthetic software proof of concept, but revise the interpretation before treating cross-arm detector differences as an effect of future leakage. The code and tests support the narrow prefix claim; they do not isolate causality from the causal filter's distinct frequency/phase response, and the artifacts do not establish that the protocol was fixed before results were examined.
