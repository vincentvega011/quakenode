"""`quakenode compare`: run the same scenario twice with different overrides and pair the arms.

Both arms use the same seeds. Pairing is per (station, seed): a station is paired only if it exists in both arms
(stations in one arm only are dropped and listed, never silently). Differences are always B minus A. Latencies are
conditional on detection in both arms. The data are whatever the config says (SYNTHETIC or a recorded event); the
input kind of each arm is carried through unchanged.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from quakenode import __version__
from quakenode.config import ConfigError, apply_overrides, parse_config
from quakenode.evaluation import distribution
from quakenode.manifest import RunManifest, results_sha256
from quakenode.scenario.loader import load_scenario

COMPARE_SCHEMA = "quakenode_compare_v1"
CATEGORIES = ("both", "only_a", "only_b", "neither", "undefined")


def split_arm(spec: str) -> list[str]:
    """'a.b=1,c=[x,y]' -> ['a.b=1', 'c=[x,y]'] (commas inside brackets, braces or quotes do not split)."""
    parts: list[str] = []
    depth, quote, cur = 0, "", []
    for ch in spec:
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        elif ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    parts.append("".join(cur).strip())
    parts = [p for p in parts if p]
    if not parts:
        raise ConfigError(f"empty arm specification {spec!r}: expected KEY=VALUE[,KEY=VALUE]")
    return parts


def _category(a: bool | None, b: bool | None) -> str:
    if a is None or b is None:
        return "undefined"
    return "both" if a and b else "only_a" if a else "only_b" if b else "neither"


def _stations_by_seed(metrics: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    return {sd: {s["station_id"]: s for s in v["stations"]} for sd, v in metrics["per_seed"].items()}


def pair_arms(
    ma: dict[str, Any],
    mb: dict[str, Any],
    dropped_a: list[str] | None = None,
    dropped_b: list[str] | None = None,
    station_match: str = "intersection_only",
) -> dict[str, Any]:
    """Pair two metrics.json mappings (arm A, arm B). Pure: no I/O, no clock.

    dropped_a / dropped_b: stations that existed only in that arm BEFORE the arms were restricted to a common set
    (default: computed from the two metrics). station_match records how the station sets were handled.
    """
    if ma["seeds"] != mb["seeds"]:
        raise ConfigError(f"arms must use the same seeds, got A {ma['seeds']} and B {mb['seeds']}")
    seeds = [str(s) for s in ma["seeds"]]
    sa, sb = _stations_by_seed(ma), _stations_by_seed(mb)
    ids_a = {i for sd in seeds for i in sa[sd]}
    ids_b = {i for sd in seeds for i in sb[sd]}
    common = sorted(ids_a & ids_b)
    only_a_stations, only_b_stations = sorted(ids_a - ids_b), sorted(ids_b - ids_a)
    if not common:
        raise ConfigError("the two arms have no station in common; nothing to pair")

    rows, all_sample, all_emission = [], [], []
    totals = dict.fromkeys(CATEGORIES, 0)
    for sid in common:
        counts = dict.fromkeys(CATEGORIES, 0)
        lat_a, lat_b, d_sample, d_emission = [], [], [], []
        p_unc = None
        for sd in seeds:
            ra, rb = sa[sd].get(sid), sb[sd].get(sid)
            if ra is None or rb is None:
                raise ConfigError(f"station {sid} is missing for seed {sd} in one arm")
            p_unc = ra["p_uncertainty_s"]
            cat = _category(ra["detected"], rb["detected"])
            counts[cat] += 1
            if ra["detected"]:
                lat_a.append(ra["sample_latency_s"])
            if rb["detected"]:
                lat_b.append(rb["sample_latency_s"])
            if cat == "both":
                d_sample.append(rb["sample_latency_s"] - ra["sample_latency_s"])
                d_emission.append(rb["emission_latency_s"] - ra["emission_latency_s"])
        for k, v in counts.items():
            totals[k] += v
        all_sample += d_sample
        all_emission += d_emission
        rows.append(
            {
                "station_id": sid,
                "p_uncertainty_s": p_unc,
                "n_seeds": len(seeds),
                **counts,
                "median_sample_latency_a_s": distribution(lat_a)["median"],
                "median_sample_latency_b_s": distribution(lat_b)["median"],
                "median_sample_latency_diff_s": distribution(d_sample)["median"],
                "median_emission_latency_diff_s": distribution(d_emission)["median"],
            }
        )

    events, ev_a, ev_b, ev_d = [], [], [], []
    for sd in seeds:
        ea, eb = ma["per_seed"][sd]["event"], mb["per_seed"][sd]["event"]
        la, lb = ea["association_latency_s"], eb["association_latency_s"]
        diff = (lb - la) if la is not None and lb is not None else None
        events.append(
            {
                "seed": int(sd),
                "event_detected_a": ea["event_detected"],
                "event_detected_b": eb["event_detected"],
                "association_latency_a_s": la,
                "association_latency_b_s": lb,
                "association_latency_diff_s": diff,
            }
        )
        ev_a.append(la)
        ev_b.append(lb)
        ev_d.append(diff)

    def arm(m: dict[str, Any]) -> dict[str, Any]:
        d = m["data"]
        return {
            "input_kind": d.get("input_kind"),
            "data": d,
            "detector": m["detector"],
            "gap_policy": m["gap_policy"],
            "order_policy": m["order_policy"],
            "arm_results_sha256": m["results_sha256"],
        }

    return {
        "schema": COMPARE_SCHEMA,
        "difference_definition": "B minus A; latencies only where the station is detected in both arms",
        "synthetic": bool(ma["synthetic"] and mb["synthetic"]),
        "seeds": ma["seeds"],
        "arm_a": arm(ma),
        "arm_b": arm(mb),
        "stations_paired": common,
        "stations_dropped_only_in_a": only_a_stations if dropped_a is None else dropped_a,
        "stations_dropped_only_in_b": only_b_stations if dropped_b is None else dropped_b,
        "station_match": station_match,
        "station_seed_pairs": totals,
        "per_station": rows,
        "paired_sample_latency_diff_s": distribution(all_sample),
        "paired_emission_latency_diff_s": distribution(all_emission),
        "event": {
            "per_seed": events,
            "association_latency_a_s": distribution(ev_a),
            "association_latency_b_s": distribution(ev_b),
            "association_latency_diff_s": distribution(ev_d),
        },
    }


# ---- output -----------------------------------------------------------------------------------------------------


def _num(v: Any, nd: int) -> str:
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def _signed(v: Any) -> str:
    return "n/a" if v is None else f"{v:+.3f}"


def _dist(d: dict, signed: bool = False) -> str:
    if d["n_defined"] == 0:
        return "n/a"
    f = _signed if signed else (lambda x: _num(x, 3))
    return f"{f(d['median'])} [{f(d['q1'])}, {f(d['q3'])}] (n={d['n_defined']}/{d['n']})"


def _arm_line(label: str, arm: dict[str, Any], sets: list[str]) -> str:
    from quakenode.report import _data_line

    ov = ", ".join(f"`{s}`" for s in sets) or "(no overrides)"
    head = f"- **Arm {label}**: input `{arm['input_kind']}`, detector `{arm['detector']}`, "
    head += f"gap policy `{arm['gap_policy']}`; "
    return head + f"overrides {ov}\n  - {_data_line(arm['data'])}"


def render_markdown(res: dict[str, Any], a_sets: list[str], b_sets: list[str], banner: str) -> str:
    from quakenode.report import _notice

    t = res["station_seed_pairs"]
    out = [
        "# QuakeNode arm comparison",
        "",
        f"> {banner}",
        "",
        _notice(res["arm_a"]["data"]),
    ]
    kinds = {res["arm_a"]["input_kind"], res["arm_b"]["input_kind"]}
    if "release_hdf5" in kinds:
        out += [
            "",
            "**An arm uses `release_hdf5`: the INSTANCE release product, full-window processed, NOT causal input.**",
        ]
    out += ["", _arm_line("A", res["arm_a"], a_sets), _arm_line("B", res["arm_b"], b_sets), ""]
    out += [
        f"Seeds: {res['seeds']}. Differences are **B minus A** and defined only where a station is detected in both "
        "arms.",
        "",
    ]
    out += [f"Stations paired ({len(res['stations_paired'])}): {', '.join(res['stations_paired'])}.", ""]
    out += [_MATCH_TEXT[res["station_match"]], ""]
    for key, name in (("stations_dropped_only_in_a", "A"), ("stations_dropped_only_in_b", "B")):
        if res[key]:
            out.append(f"**Dropped (present only in arm {name}):** {', '.join(res[key])}.")
        else:
            out.append(f"Dropped (present only in arm {name}): none.")
    out += ["", "## Detection status over (station, seed) pairs", ""]
    out += ["| both | only A | only B | neither | undefined |", "|---|---|---|---|---|"]
    out += [f"| {t['both']} | {t['only_a']} | {t['only_b']} | {t['neither']} | {t['undefined']} |", ""]
    out += ["## Paired differences (B minus A, seconds)", ""]
    out += [f"- sample-clock latency: median [Q1, Q3] = {_dist(res['paired_sample_latency_diff_s'], True)}"]
    out += [f"- emission-clock latency: median [Q1, Q3] = {_dist(res['paired_emission_latency_diff_s'], True)}", ""]
    out += ["## Per station", ""]
    out += [
        "| station | P unc (s) | both | only A | only B | neither | median latency A (s) | median latency B (s) "
        "| median diff B-A (s) |"
    ]
    out += ["|---|---|---|---|---|---|---|---|---|"]
    for r in res["per_station"]:
        out.append(
            f"| {r['station_id']} | {_num(r['p_uncertainty_s'], 2) if r['p_uncertainty_s'] is not None else 'n/a'} | "
            f"{r['both']} | {r['only_a']} | {r['only_b']} | {r['neither']} | "
            f"{_dist_one(r['median_sample_latency_a_s'])} | {_dist_one(r['median_sample_latency_b_s'])} | "
            f"{_signed(r['median_sample_latency_diff_s'])} |"
        )
    ev = res["event"]
    out += ["", "## Event association latency (emission clock, relative to the earliest reference P)", ""]
    out += [
        "| seed | detected A | detected B | latency A (s) | latency B (s) | diff B-A (s) |",
        "|---|---|---|---|---|---|",
    ]
    for e in ev["per_seed"]:
        out.append(
            f"| {e['seed']} | {e['event_detected_a']} | {e['event_detected_b']} | "
            f"{_dist_one(e['association_latency_a_s'])} | "
            f"{_dist_one(e['association_latency_b_s'])} | {_signed(e['association_latency_diff_s'])} |"
        )
    out += [
        "",
        f"A: {_dist(ev['association_latency_a_s'])}; B: {_dist(ev['association_latency_b_s'])}; "
        f"diff: {_dist(ev['association_latency_diff_s'], True)}",
    ]
    out += ["", "## Caveats", ""]
    out += [
        "- Reference P times are reviewed catalog picks with the stated uncertainty in the table; they are not truth."
    ]
    out += ["- Latencies are conditional on detection; a station detected in only one arm contributes no difference."]
    out += ["- Medians and quartiles pool (station, seed) pairs; with no faults the seeds repeat identical data."]
    out += [
        "- Tool demonstration; no claim about detector performance, the release product in general, or warning times."
    ]
    return "\n".join(out) + "\n"


_MATCH_TEXT = {
    "identical": "Both arms contain the same stations.",
    "rerun_with_common_stations": (
        "The arms had different stations, so both were re-run restricted to the common stations "
        "(`scenario.instance.stations` override, recorded in the manifest): detection and event metrics below use the "
        "same stations in both arms."
    ),
    "intersection_only": (
        "Only per-station rows are restricted to the common stations; event metrics use each arm's own stations."
    ),
}


def _dist_one(v: Any) -> str:
    return "n/a" if v is None else _num(v, 3)


def write_csv(res: dict[str, Any], path: Path) -> None:
    cols = [
        "station_id", "p_uncertainty_s", "n_seeds", *CATEGORIES, "median_sample_latency_a_s",
        "median_sample_latency_b_s", "median_sample_latency_diff_s", "median_emission_latency_diff_s",
    ]  # fmt: skip
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in res["per_station"]:
            w.writerow(["" if r[c] is None else r[c] for c in cols])


def plot_compare(res: dict[str, Any], path: Path) -> bool:
    from quakenode.report import _mpl, _title

    plt = _mpl()
    if plt is None:
        return False
    rows = res["per_station"]
    fig, ax = plt.subplots(figsize=(7, 0.35 * len(rows) + 1.8))
    ys = list(range(len(rows)))
    for y, r in zip(ys, rows):
        d = r["median_sample_latency_diff_s"]
        if d is None:
            ax.plot([0], [y], "x", color="0.4")
            ax.annotate(
                "not detected in both", (0, y), xytext=(6, 0), textcoords="offset points", va="center", fontsize=7
            )
        else:
            ax.barh(y, d, color="tab:blue")
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(ys, [r["station_id"] for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("median paired sample-clock latency difference, B minus A (s)")
    a, b = res["arm_a"], res["arm_b"]
    ax.set_title(_title(a["data"], f"A={a['input_kind']} vs B={b['input_kind']}"), fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return True


def run_compare(
    raw: dict[str, Any],
    config_path: str,
    a_sets: list[str],
    b_sets: list[str],
    common_sets: list[str] | None = None,
    out_root: Path | None = None,
) -> Path:
    """Run both arms (new unique directory, never overwritten), pair them and write compare.* outputs."""
    from quakenode.experiment import BANNER, METRIC_VERSION, _unique_dir, run_experiment

    common_sets = common_sets or []
    cfg0 = parse_config(raw, config_path)
    out = _unique_dir(out_root or Path(cfg0.output_dir), f"{cfg0.name}-compare")
    base = {k: v for k, v in raw.items() if k != "sweep"}
    arm_sets = {"a": [*common_sets, *a_sets], "b": [*common_sets, *b_sets]}
    match, drop_a, drop_b = "identical", None, None
    if cfg0.scenario.source == "instance_event":  # station sets can differ between input kinds (missing raw data)
        ids = {}
        for label, sets in arm_sets.items():
            cfg = parse_config(apply_overrides(base, sets)[0], config_path)
            ids[label] = {s["station_id"] for s in load_scenario(cfg).stations}
        common = sorted(ids["a"] & ids["b"])
        if ids["a"] != ids["b"]:
            if not common:
                raise ConfigError("the two arms have no station in common; nothing to pair")
            drop_a, drop_b = sorted(ids["a"] - ids["b"]), sorted(ids["b"] - ids["a"])
            match = "rerun_with_common_stations"
            restrict = "scenario.instance.stations=" + json.dumps(common)
            arm_sets = {k: [*v, restrict] for k, v in arm_sets.items()}
    else:
        match = "intersection_only"
    metrics, applied = {}, {}
    for label, sets in arm_sets.items():
        arm_raw, ov = apply_overrides(base, sets)
        arm_raw["name"] = f"{cfg0.name}-arm-{label}"
        parse_config(arm_raw, config_path)
        d = run_experiment(arm_raw, config_path, out_dir=out / "arms" / label, overrides=ov)
        metrics[label] = json.loads((d / "metrics.json").read_text(encoding="utf-8"))
        applied[label] = ov
    res = pair_arms(metrics["a"], metrics["b"], drop_a, drop_b, match)
    if match == "intersection_only" and not (res["stations_dropped_only_in_a"] or res["stations_dropped_only_in_b"]):
        res["station_match"] = "identical"
    res["results_sha256"] = results_sha256(res)
    manifest = RunManifest.create(
        config={
            "config_file": config_path,
            "experiment": raw,
            "common_overrides": common_sets,
            "arm_a_overrides": a_sets,
            "arm_b_overrides": b_sets,
            "applied_overrides": applied,
            "quakenode_version": __version__,
        },
        seeds=list(metrics["a"]["seeds"]),
        metric_definition_version=METRIC_VERSION,
        repo_dir=Path.cwd(),
        output_paths=[str(out / n) for n in ("compare.md", "compare.csv", "compare.json", "manifest.json")],
        warnings=[metrics["a"]["notice"], metrics["b"]["notice"], BANNER],
    )
    (out / "manifest.json").write_text(manifest.to_json() + "\n", encoding="utf-8")
    (out / "compare.json").write_text(
        json.dumps({**res, "manifest": manifest.to_dict()}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "compare.md").write_text(render_markdown(res, arm_sets["a"], arm_sets["b"], BANNER), encoding="utf-8")
    write_csv(res, out / "compare.csv")
    (out / "plots").mkdir()
    plot_compare(res, out / "plots" / "compare_latency.png")
    return out
