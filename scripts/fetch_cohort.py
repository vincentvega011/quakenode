"""Resumable, polite fetch of raw INGV miniSEED for the frozen Stage 1 cohort (network only; no analysis).

For each trace in docs/cohort_stage1_traces.txt: one sequential FDSN dataselect request for the Z channel over
[trace_start_time - 15 s, trace_start_time + 135 s]. Files are cached under data/raw/cohort/ and every attempt is
appended to data/raw/cohort/fetch_log.jsonl (URL, HTTP status, bytes, sha256, error). Re-running skips traces whose
last log entry is `ok` or `empty` (HTTP 200/204 with an empty body is final) and retries `error` entries.

    python scripts/fetch_cohort.py --sleep 1.0
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

FDSN = "https://webservices.ingv.it/fdsnws/dataselect/1/query"
USER_AGENT = "quakenode-research/0.0.1 (sequential, cached, resumable)"
PAD_BEFORE_S, PAD_AFTER_S, WINDOW_S = 15.0, 15.0, 120.0


def request_url(trace_name: str, start_time: str) -> str:
    """FDSN URL for the Z channel of a trace. start_time is the metadata `trace_start_time` (UTC, trailing Z)."""
    from datetime import datetime, timedelta, timezone

    _, net, sta, loc, fam = trace_name.split(".")
    base, _, frac = start_time.rstrip("Z").partition(".")
    t0 = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    t0 += timedelta(microseconds=int(frac.ljust(6, "0")) if frac else 0)
    fmt = "%Y-%m-%dT%H:%M:%S"
    q = {
        "network": net, "station": sta, "location": loc or "--", "channel": fam + "Z",
        "starttime": (t0 - timedelta(seconds=PAD_BEFORE_S)).strftime(fmt),
        "endtime": (t0 + timedelta(seconds=WINDOW_S + PAD_AFTER_S)).strftime(fmt),
        "format": "miniseed",
    }  # fmt: skip
    return FDSN + "?" + urllib.parse.urlencode(q)


def last_status(log_path: Path) -> dict[str, str]:
    status: dict[str, str] = {}
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            if line.strip():
                e = json.loads(line)
                status[e["trace"]] = e["status"]
    return status


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cohort", default="docs/cohort_stage1_traces.txt")
    ap.add_argument("--csv", default="data/instance_sample/metadata/metadata_Instance_events_10k.csv")
    ap.add_argument("--raw-dir", default="data/raw/cohort")
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()
    raw_dir = Path(args.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    log_path = raw_dir / "fetch_log.jsonl"
    names = [n for n in Path(args.cohort).read_text().split() if n]
    with open(args.csv, newline="") as f:
        meta = {r["trace_name"]: r["trace_start_time"] for r in csv.DictReader(f)}
    done = {t for t, s in last_status(log_path).items() if s in ("ok", "empty")}
    todo = [n for n in names if n not in done]
    print(f"cohort={len(names)} already_done={len(done)} to_fetch={len(todo)}", flush=True)
    with open(log_path, "a") as log:
        for i, name in enumerate(todo, 1):
            url = request_url(name, meta[name])
            entry = {"trace": name, "url": url, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            blob, err, http = b"", None, None
            for attempt in (1, 2, 3):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (fixed https endpoint)
                        http, blob = r.status, r.read()
                    err = None
                    break
                except Exception as exc:
                    err = f"{type(exc).__name__}: {exc}"
                    if getattr(exc, "code", None) == 204:  # urllib may raise for no-content in some setups
                        http, err = 204, None
                        break
                    time.sleep(5.0 * attempt)
            if err:
                entry.update(status="error", error=err)
            elif not blob:
                entry.update(status="empty", http_status=http, bytes=0)
            else:
                path = raw_dir / f"{name.replace('..', '.')}.Z.mseed"
                path.write_bytes(blob)
                entry.update(
                    status="ok",
                    http_status=http,
                    bytes=len(blob),
                    sha256=hashlib.sha256(blob).hexdigest(),
                    file=path.name,
                )
            log.write(json.dumps(entry, sort_keys=True) + "\n")
            log.flush()
            if i % 25 == 0 or i == len(todo):
                print(f"[{i}/{len(todo)}] {name} {entry['status']}", flush=True)
            time.sleep(args.sleep)
    print("done", flush=True)


if __name__ == "__main__":
    main()
