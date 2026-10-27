# Contributing

QuakeNode is a research testbed, not an operational warning system. Please keep it honest.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,data,plots]"
ruff check . && ruff format --check . && pytest
quakenode run examples/synthetic_network/config.yaml
```

Python >= 3.10. CI runs ruff, `ruff format --check`, pytest on Linux with 3.10, 3.11 and 3.12, on macOS with 3.12 and (experimental, unverified) Windows with 3.12, the CLI quickstart and a wheel build. Starter tasks: `docs/good_first_issues.md`.

## Rules that every change must respect

- **No future-sample leakage.** A detector only sees data the logical clock has delivered. Changes touching timing,
  preprocessing, faults or replay need a test that alters only future samples/packets and asserts identical earlier
  outputs.
- **Keep the four clocks apart:** sample, ready, arrival, emission. Do not merge them in names or types.
- **No fabricated data or numbers.** Synthetic data is labeled SYNTHETIC and only supports software-invariant claims.
  Unknown values are `None` with a reason.
- **Determinism.** Seeded randomness only (`quakenode.faults.rng`), no wall-clock sleeps in simulation logic. Use `math.fsum` for float sums that reach outputs: the built-in `sum()` rounds differently from Python 3.12 on, which silently changed result hashes between 3.11 and 3.12 before this was fixed.
- **Fail loudly** on invalid config; no silent fallbacks.
- No novelty claims and no operational-system claims in docs or code.
- Never commit waveform data (`data/` is gitignored); respect dataset licences.

## Adding a detector or a fault

See "Extending" in `docs/architecture.md`. Include tests: a hand-computed toy case, chunking/packetization
independence for detectors, and determinism with a pinned pattern for faults.

## Style

`ruff` (config in `pyproject.toml`), type hints on public APIs, small functions, tests next to the behaviour they pin.
