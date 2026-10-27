# ADR 0001: Minimum research prototype

- **Status:** Accepted for design; implementation not started
- **Date:** 2026-10-26
- **Decision owners:** QuakeNode research team
- **Related:** evaluation_protocol.md; dataset_feasibility.md; research_gap_decision.md; prior_art_audit.md

## Context

The inspected workspace has project documentation and a protocol, but no application code, package metadata, tests, CI or dependency stack. The project context recommends software-first, single-process Python with explicit causal timing and reproducibility.

The first protocol is narrower than the original platform concept: INSTANCE v3 sample; per-trace HNZ classic STA/LTA replay; packetized no-fault control versus 5% independent one-second packet loss as primary contrast; restricted detection time, misses and sampled-noise false triggers. Sample access/schema/HNZ coverage and joins remain unverified. There is no target-site threshold timeline, so warning utility is out of scope. Prior work already includes real-time EEW evaluation and network-failure simulation.

## Decision

Design a small single-process Python package with:
1. Strict INSTANCE v3 adapter producing canonical read-only traces and failing on unknown schema/time/unit mappings.
2. Packetizer and virtual-clock replay engine exposing only delivered packets.
3. Deterministic fault-plan module for protocol loss, outage and delay.
4. One fixed causal STA/LTA detector with explicit gap reset/warm-up.
5. Pure evaluator for matching, RDT/miss/false-trigger metrics, equal-event aggregation and bootstrap.
6. Reporter writing provenance manifest and trace/event/summary outputs.
7. Unit and tiny synthetic end-to-end tests for scientific invariants.

Do not implement fusion, association, alerts, warning utility, physical sensor connectivity, database/cloud services, model training or dashboard in this version.

## Alternatives considered

- **Implement the broad original architecture now:** rejected. No code exists and data do not establish fusion or target-site utility; broad scope would obscure the first answer.
- **Use synthetic signals as the detector experiment:** rejected. Synthetic fixtures establish software invariants, not real detector behavior. If INSTANCE fails, synthetic-only work must be labeled software validation and the research question revised.
- **Start with continuous EarthScope TA:** deferred. It is technically attractive for continuous multi-station replay, but candidate window/coverage and redistribution rights require more verification. INSTANCE has clearer published sample/license for a bounded detector sensitivity pilot.
- **Add ObsPy, SeisBench, pandas, SciPy or a framework now:** rejected. HDF5/metadata and a direct STA/LTA baseline do not currently require them; add only for a demonstrated format/API need.
- **Implement identity/no-op fusion:** rejected. It adds machinery without a scientific function. Document a future causal detection-only boundary instead.

## Consequences

### Benefits
- Every component maps to an experiment step.
- API structure enforces causality: detector receives packets/gaps, never a whole trace or future iterator.
- Sample time, arrival and emission remain distinct.
- Deterministic faults and paired event-level metrics support audit and reruns.
- Waveforms can stay outside Git; manifests identify source files by DOI/checksum.

### Costs and limitations
- Single-station only; no fusion or event association conclusions.
- One-second packetization and reset/re-warm are modeling choices affecting results.
- Counts avoid physical-unit mixing but do not make station amplitudes comparable.
- INSTANCE access/schema/HNZ cohort must pass feasibility gates.
- No warning utility, network realism or broad generalization claim.

## Deferred decisions

- Whether the sample contains an eligible HNZ cohort; actual schema and joins.
- Exact epsilon/precision, bootstrap seed, checksums and frozen event IDs; set before run without outcome-driven changes.
- Exact dependency pins and OS matrix; propose Python 3.11+ with initial macOS/Linux validation.
- Whether a later continuous archive is appropriate, after rights/access checks.
- Any fusion rule, target threshold, physical adapter, MQTT/SeedLink transport or alert semantics.
- Whether results justify a publication after focused prior-art comparison; publication is not promised.

## Revisit triggers

Reopen this ADR if INSTANCE feasibility fails, protocol changes introduce fusion/target utility, a new dataset requires another adapter, or implementation cannot enforce causal packet access. Any such change requires protocol amendment before outcome analysis.
