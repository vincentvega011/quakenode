## What this changes

<!-- One paragraph. Link the issue if there is one. -->

## Invariant the tests protect

<!-- For example: "no future-sample leakage" with a test that alters only future samples. Required for changes to timing, preprocessing, faults or replay. -->

## Checklist

- [ ] `ruff check .`, `ruff format --check .` and `pytest` pass locally
- [ ] New or changed behaviour has a test (a pinned-pattern test for any fault change)
- [ ] No waveform data, tokens or absolute local paths are committed
- [ ] Docs and `CHANGELOG.md` updated if user-visible
- [ ] No novelty, performance or operational-use claims; SYNTHETIC data labeled as such
