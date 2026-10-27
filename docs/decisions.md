# Decisions log (append-only)

Dated entries; do not edit past entries, add new ones that supersede them.

## 2026-10-26

**D1. Offline arm = the released INSTANCE HDF5 array, labeled "release product".**
The pre-registered check (`docs/preregistration_detrend_check.md`, results in `docs/detrend_check_results.md`) found that a least-squares line fitted over the 120 s window, subtracted, and truncated to integer reproduces HH Z traces to within 1 count (T1-trunc: 84/88 pooled, Wilson 95% 88.9 to 98.2%; HH 77/80; HN only 7/8 of 8 traces). This is reported as a **caveated equivalence, not an exact reproduction**: no variant reproduced any trace exactly (0/88 with max abs 0), and the result is effectively HH only.

**D2. Cohort family = IV network, HH, Z component, 100 Hz native.**
HN is excluded for now: only 8 HN traces were comparable in the check, 38 of 100 sampled HN traces were archived at 200 Hz, and 53 returned empty responses. Reopening HN needs a separate pre-registration.

**D3. Causal arm = raw INGV miniSEED processed causally.**
The causal arm starts from the original INGV miniSEED for the same trace (nearest raw sample to `trace_start_time`, no shifting) and applies only causal operations.

## 2026-10-26 (later)

**D4. Positioning = P2 in two stages** (see `docs/prior_art_artifact_check.md`).
Stage 1: STA/LTA on the released HDF5 array (release-product arm) versus raw INGV miniSEED processed causally (causal arm), cohort IV / HH / Z / 100 Hz. Stage 2: SeisBench pickers in causal streaming versus the standard window evaluation. SeisBench is GPL-3.0: never vendor it, never import it from the core `quakenode` package; only from optional scripts or an extra, stated in the README.

**D5. Stage 1 cohort draw (frozen before any raw data was fetched).**
Pool: INSTANCE sample events metadata rows with network IV, channel family HH, `trace_dt_s` 0.01, `trace_npts` 12000: **3,701** traces. Draw: sort `trace_name`, then `random.Random(20261105).sample(sorted_pool, 1000)`; output sorted. List: `docs/cohort_stage1_traces.txt` (1,000 names), sha256 `2f32530fbf4c4cafcfe24419331748d873425a275d916809c86abaf71a1796ff`, produced by `scripts/draw_cohort.py` (re-run reproduces the hash). No replacements for excluded traces. The 11 + 200 traces inspected in earlier checks are not removed from the pool.

**D5 outcome (2026-10-26).** Fetch of the 1,000 cohort traces finished: 830 files returned, 170 empty responses (no errors). Exclusions: `fetch_failed` 170; all other pre-declared reasons 0. Comparable: 830 (238 events, 141 stations). Not replaced. Details in `docs/cohort_stage1_summary.md`. Note that the `grid_offset_gt_0.5_sample` criterion cannot trigger by construction (nearest-sample alignment); the observed maximum offset was 0.44 sample (4.4 ms).

## 2026-10-27

**D7. Near-term goal = a credible, usable open-source tool, not a paper.**
Real-data Stage 1/2 work is paused. All existing pre-registration files, cohort files and scripts stay untouched. (No D6 entry exists in this repository's history; the number is skipped, not lost work.) Hard rules in docs/DEVELOPMENT.md still apply: no future leakage, separate clocks, no fabricated data, synthetic data labeled synthetic, no operational-system claims. The target is: `pip install`, one command on a YAML config, a reproducible multi-station streaming experiment with seeded fault injection, metrics, a report with plots and a manifest, plus a fault sweep paired against a matched no-fault control. Scenario data in this tool are SYNTHETIC and say so everywhere.

## 2026-10-27 (later)

**D8. Gap handling becomes a configurable policy; the tool gains real recorded event replay on a development set only.**
(a) `pipeline.gap_policy`: `reset` (default, previous behaviour), `hold` (keep filter and detector state across the gap, insert no samples; a fault-tolerance policy, not a repair), `zero_fill` (insert zeros for the missing indices, labeled as filled samples everywhere). No interpolation. Details and caveats in `docs/gap_policies.md`.
(b) Real recorded event replay (extra `data`) uses ONLY a development set of INSTANCE events (IV/HH/Z/100 Hz) that have no trace in the frozen Stage 1 draw (`docs/cohort_stage1_traces.txt`, sha256 `2f32530f...`), so the paused pre-registered study is not contaminated. Stage 1 files, cohort files and the pre-registration stay untouched. Real-event runs are tool demonstrations, not scientific claims. The development events and their selection rule are in `docs/dev_events.txt`.

**D9. Near-term goal: a public-ready 0.2.0 release of the tool.**
Scope: a `quakenode compare` subcommand (two arms of the same scenario with different overrides, paired per station and seed), package metadata and a verified wheel, a newcomer `quakenode demo` command, GitHub scaffolding, a good-first-issues list, and an honest README (status, limitations, related tools restricted to facts in `docs/prior_art_artifact_check.md`). No novelty claims. Real-data work stays paused (D7); Stage 1 files, cohort files and the pre-registration stay untouched. Publishing (push, tag) is done by the maintainer, not by the assistant.
