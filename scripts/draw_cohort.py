"""Frozen Stage 1 cohort draw from the INSTANCE sample events metadata (metadata only; no waveforms).

Pool: network IV, channel family HH (component Z is requested downstream), trace_dt_s 0.01, trace_npts 12000.
Draw: sort trace_name, then random.Random(seed).sample(sorted_pool, n) (or the whole pool if smaller).
Output order is the sorted order of the drawn names.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
from pathlib import Path

SEED = 20261105
N = 1000


def eligible(row: dict[str, str]) -> bool:
    parts = row["trace_name"].split(".")
    return (
        len(parts) == 5
        and parts[1] == "IV"
        and parts[4] == "HH"
        and float(row["trace_dt_s"]) == 0.01
        and int(row["trace_npts"]) == 12000
    )


def draw(trace_names: list[str], seed: int, n: int) -> list[str]:
    pool = sorted(trace_names)
    chosen = pool if len(pool) <= n else random.Random(seed).sample(pool, n)
    return sorted(chosen)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="data/instance_sample/metadata/metadata_Instance_events_10k.csv")
    ap.add_argument("--out", default="docs/cohort_stage1_traces.txt")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--n", type=int, default=N)
    args = ap.parse_args()
    with open(args.csv, newline="") as f:
        names = [r["trace_name"] for r in csv.DictReader(f) if eligible(r)]
    chosen = draw(names, args.seed, args.n)
    text = "\n".join(chosen) + "\n"
    Path(args.out).write_text(text)
    print(f"pool={len(names)} drawn={len(chosen)} sha256={hashlib.sha256(text.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
