"""Resumable, polite fetch of raw INGV miniSEED for the development events (network only; no analysis).

Same approach as scripts/fetch_cohort.py: sequential requests with a pause, files cached under data/raw/dev/, every
attempt logged (URL, HTTP status, bytes, sha256) in data/raw/dev/fetch_log.jsonl; `ok` and `empty` entries are final,
`error` entries are retried on the next run. Traces come from docs/dev_events.txt.

    python scripts/fetch_dev_events.py --sleep 1.0
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.fetch_cohort import USER_AGENT, last_status, request_url  # noqa: E402


def traces_from_dev_file(path: Path) -> list[str]:
    names: list[str] = []
    for line in path.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            names += line.split("\t")[2].split(",")
    return names


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dev-events", default="docs/dev_events.txt")
    ap.add_argument("--csv", default="data/instance_sample/metadata/metadata_Instance_events_10k.csv")
    ap.add_argument("--raw-dir", default="data/raw/dev")
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()
    raw_dir = Path(args.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    log_path = raw_dir / "fetch_log.jsonl"
    names = traces_from_dev_file(Path(args.dev_events))
    with open(args.csv, newline="") as f:
        meta = {r["trace_name"]: r["trace_start_time"] for r in csv.DictReader(f)}
    done = {t for t, s in last_status(log_path).items() if s in ("ok", "empty")}
    todo = [n for n in names if n not in done]
    print(f"dev traces={len(names)} already_done={len(done)} to_fetch={len(todo)}", flush=True)
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
                    time.sleep(5.0 * attempt)
            if err:
                entry.update(status="error", error=err)
            elif not blob:
                entry.update(status="empty", http_status=http, bytes=0)
            else:
                path = raw_dir / f"{name.replace('..', '.')}.Z.mseed"
                path.write_bytes(blob)
                entry.update(status="ok", http_status=http, bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(),
                             file=path.name)  # fmt: skip
            log.write(json.dumps(entry, sort_keys=True) + "\n")
            log.flush()
            print(f"[{i}/{len(todo)}] {name} {entry['status']}", flush=True)
            time.sleep(args.sleep)
    print("done", flush=True)


if __name__ == "__main__":
    main()
