"""Markdown reports and (optional) PNG plots from a finished run or sweep directory.

Plots need matplotlib (`pip install 'quakenode[plots]'`); without it the report says so and skips them.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

BANNER = "QuakeNode is a research testbed, not an operational warning system."
SYNTH = (
    "All synthetic-scenario data are SYNTHETIC (generated in-process); results support software-invariant claims only."
)
REAL = "Real-event runs are tool demonstrations on a few events, not performance evidence."


def _fmt(v: Any, nd: int = 3) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def _dist(d: dict | None) -> str:
    if not d or d.get("n_defined", 0) == 0:
        return "n/a"
    return f"{_fmt(d['median'])} [{_fmt(d['q1'])}, {_fmt(d['q3'])}] (n={d['n_defined']}/{d['n']})"


def _data_line(d: dict) -> str:
    if d.get("source") == "instance_event":
        nets = ", ".join(f"{n} (DOI {v or 'not checked'})" for n, v in d.get("network_dois", {}).items())
        return (
            f"**REAL RECORDED EVENT {d['event_id']}, input kind `{d['input_kind']}`: {d['input_description']}.** "
            f"Source: {d['data_source']}, DOI {d['doi']}, {d['license']}; networks: {nets}. "
            f"{d['p_reference']}. TOOL DEMONSTRATION, not performance evidence."
        )
    return "SYNTHETIC (generated in-process; not a seismological model)"


def _notice(d: dict) -> str:
    return REAL if d.get("source") == "instance_event" else SYNTH


def _mpl():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except ImportError:
        return None


def _title(d: dict, text: str) -> str:
    if d.get("source") == "instance_event":
        return f"REAL event {d['event_id']} ({d['input_kind']}), tool demo: {text}"
    return f"SYNTHETIC data: {text}"


def plot_run(run: Path, metrics: dict) -> list[str]:
    plt = _mpl()
    if plt is None:
        return []
    (run / "plots").mkdir(exist_ok=True)
    made = []
    stations = list(metrics["per_station"])
    data = metrics.get("data", {})
    width = 0.38
    fig, ax = plt.subplots(figsize=(max(7, 0.7 * len(stations) + 3), 3.6))
    for j, (key, label) in enumerate(
        (
            ("sample_latency_s", "sample clock (detector delay)"),
            ("emission_latency_s", "emission clock (incl. packetization, network)"),
        )
    ):
        xs, med, lo, hi = [], [], [], []
        for i, s in enumerate(stations):
            d = metrics["per_station"][s][key]
            if d["n_defined"]:
                xs.append(i + (j - 0.5) * width)
                med.append(d["median"])
                lo.append(d["median"] - d["q1"])
                hi.append(d["q3"] - d["median"])
        ax.bar(xs, med, width, yerr=[lo, hi], label=label, capsize=2)
    ax.set_xticks(range(len(stations)), stations, rotation=45 if len(stations) > 8 else 0)
    ax.set_ylabel("latency after reference P (s)")
    ax.set_title(_title(data, "detection latency per station (median, IQR over seeds)"), fontsize=8)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(run / "plots" / "latency_per_station.png", dpi=130)
    plt.close(fig)
    made.append("plots/latency_per_station.png")

    fig, ax = plt.subplots(figsize=(max(7, 0.7 * len(stations) + 3), 3.6))
    rate = [metrics["per_station"][s]["detection_rate"] or 0.0 for s in stations]
    comp = [metrics["per_station"][s]["completeness"]["mean"] or 0.0 for s in stations]
    ax.bar([i - width / 2 for i in range(len(stations))], rate, width, label="detection rate")
    ax.bar([i + width / 2 for i in range(len(stations))], comp, width, label="data completeness")
    ax.set_xticks(range(len(stations)), stations, rotation=45 if len(stations) > 8 else 0)
    ax.set_ylim(0, 1.05)
    ax.set_title(_title(data, "detection rate and completeness per station"), fontsize=8)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(run / "plots" / "rate_completeness.png", dpi=130)
    plt.close(fig)
    made.append("plots/rate_completeness.png")
    return made


def write_report(run: Path) -> Path:
    run = Path(run)
    m = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    man = json.loads((run / "manifest.json").read_text(encoding="utf-8")) if (run / "manifest.json").exists() else {}
    exp = man.get("config", {}).get("experiment", {})
    data = m.get("data", {})
    plots = plot_run(run, m)
    ev = m["event_detection_rate"]
    lines = [
        "# QuakeNode run report",
        "",
        f"> {BANNER}",
        f"> {_notice(data)}",
        "",
        f"- Run: `{run.name}`  (experiment `{exp.get('name', '?')}`)",
        f"- Data: {_data_line(data)}",
        f"- Seeds: {m['n_seeds']} ({m['seeds'][0]}..{m['seeds'][-1]}), git commit `{man.get('git_commit')}`, "
        f"dirty: {man.get('git_dirty')}, Python {man.get('python_version')}",
        f"- Detector: `{m.get('detector', exp.get('detector', {}).get('name', 'sta_lta_rms'))}`; "
        f"gap policy: **{m.get('gap_policy', 'reset')}**; order policy: {m.get('order_policy', 'reject')}",
        f"- Fusion: {exp.get('fusion', {})}",
        f"- Faults (in order): {exp.get('faults', []) or 'none (control)'}",
        f"- Overrides applied: {man.get('config', {}).get('overrides') or 'none'}",
        f"- results_sha256: `{m['results_sha256']}`",
    ]
    if m.get("station_exclusions"):
        lines.append(f"- Stations excluded: {m['station_exclusions']}")
    lines += [
        "",
        "## Seed-level summary (median [Q1, Q3], defined/total seeds)",
        "",
        "| metric | value |",
        "|---|---|",
    ]
    for k, d in m["summary_over_seeds"].items():
        lines.append(f"| {k} | {_dist(d)} |")
    lo, hi = ev["wilson95"]
    lines += [
        "",
        f"Event detection rate: {ev['k']}/{ev['n']} = {_fmt(ev['rate'])} (Wilson 95%: {_fmt(lo)} to {_fmt(hi)}).",
        "",
        "## Per station (over seeds)",
        "",
        "| station | stated P unc. (s) | detection rate | sample latency (s) | emission latency (s) | "
        "completeness | filled samples (mean) | false triggers |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s, d in m["per_station"].items():
        lines.append(
            f"| {s} | {_fmt(d.get('p_uncertainty_s'))} | {_fmt(d['detection_rate'])} | "
            f"{_dist(d['sample_latency_s'])} | "
            f"{_dist(d['emission_latency_s'])} | {_fmt(d['completeness']['mean'])} | "
            f"{_fmt(d['filled_samples']['mean'], 1)} | {d['false_triggers_total']} |"
        )
    first = next(iter(m["per_seed"].values()))
    lines += ["", "## Fault records (first seed)", ""]
    if first["faults"]:
        lines += ["| # | type | status | considered | affected | parameters |", "|---|---|---|---|---|---|"]
        for i, f in enumerate(first["faults"]):
            cells = [i, f["type"], f["status"], f["packets_considered"], f["packets_affected"], f["parameters"]]
            lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    else:
        lines.append("No faults (control scenario).")
    lines += ["", "## Plots", ""]
    lines += (
        [f"![{p}]({p})" for p in plots] if plots else ["matplotlib is not installed: `pip install 'quakenode[plots]'`."]
    )
    lines += [
        "",
        "Definitions of every metric: `docs/metrics.md`; gap policies: `docs/gap_policies.md`. "
        "Raw events: `events.jsonl`. Manifest: `manifest.json`.",
        "",
    ]
    path = run / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---- sweeps -----------------------------------------------------------------------------------------------------

PANELS = (
    ("detection_fraction", "station detection fraction"),
    ("median_emission_latency_s", "median emission latency (s)"),
    ("event_detected", "event detected (fraction of seeds)"),
)


def _numeric(values: list) -> bool:
    return all(isinstance(v, int | float) and not isinstance(v, bool) for v in values)


def _control_for(res: dict, point: dict) -> dict:
    return next(c for c in res["controls"] if c["index"] == point["control_index"])


def _sweep_plot(sweep: Path, res: dict) -> list[str]:
    plt = _mpl()
    if plt is None:
        return []
    params = [p["path"] for p in res["parameters"]]
    xs_name = params[0]
    xvals = [p["values"] for p in res["parameters"]][0]
    categorical = not _numeric(xvals)
    series: dict[Any, list] = {}
    for pt in res["points"]:
        key = pt["parameters"][params[1]] if len(params) > 1 else None
        series.setdefault(key, []).append(pt)
    fig, axes = plt.subplots(1, len(PANELS), figsize=(12.5, 3.8))
    for ax, (metric, label) in zip(axes, PANELS, strict=True):
        n_series = len(series)
        for si, (key, pts) in enumerate(series.items()):
            order = {v: i for i, v in enumerate(xvals)}
            pts = sorted(pts, key=lambda p: order[p["parameters"][xs_name]])
            d = [p["aggregate"]["summary_over_seeds"][metric] for p in pts]
            y = [v["median"] if v["median"] is not None else float("nan") for v in d]
            lo = [v["q1"] if v["q1"] is not None else float("nan") for v in d]
            hi = [v["q3"] if v["q3"] is not None else float("nan") for v in d]
            ctrl = [_control_for(res, p)["aggregate"]["summary_over_seeds"][metric]["median"] for p in pts]
            name = f"{params[1]}={key}" if key is not None else "with faults"
            if categorical:
                w = 0.8 / (2 * n_series)
                x = [order[p["parameters"][xs_name]] + (si - (n_series - 1) / 2) * 2 * w for p in pts]
                err = [[a - b for a, b in zip(y, lo, strict=True)], [b - a for a, b in zip(y, hi, strict=True)]]
                err = [[v if v == v else 0.0 for v in e] for e in err]
                ax.bar(x, [v if v == v else 0.0 for v in y], w, yerr=err, capsize=2, label=name)
                ax.bar([xi + w for xi in x], [c if c is not None else 0.0 for c in ctrl], w, color="0.7",
                       label="no-fault control" if si == 0 else None)  # fmt: skip
            else:
                x = [p["parameters"][xs_name] for p in pts]
                (line,) = ax.plot(x, y, marker="o", label=name)
                ax.fill_between(x, lo, hi, alpha=0.18, color=line.get_color())
                cvals = [c for c in ctrl if c is not None]
                if cvals:
                    ax.axhline(cvals[0], color=line.get_color(), ls="--", lw=0.9, alpha=0.7)
        if categorical:
            ax.set_xticks(range(len(xvals)), [str(v) for v in xvals], rotation=15)
        ax.set_xlabel(xs_name)
        ax.set_ylabel(label)
    axes[0].legend(fontsize=7)
    fig.suptitle(
        _title(
            res["data"], "metric vs swept parameter (median and IQR over seeds; dashed/gray = matched no-fault control)"
        ),
        fontsize=8,
    )
    fig.tight_layout()
    (sweep / "plots").mkdir(exist_ok=True)
    fig.savefig(sweep / "plots" / "sweep.png", dpi=130)
    plt.close(fig)
    return ["plots/sweep.png"]


def write_sweep_report(sweep: Path) -> Path:
    sweep = Path(sweep)
    res = json.loads((sweep / "sweep_results.json").read_text(encoding="utf-8"))
    params = [p["path"] for p in res["parameters"]]
    head = res["headline_metric"]
    hdr = [
        *params,
        f"{head} median [Q1,Q3]",
        f"paired diff vs matched control ({head})",
        "event detected (rate)",
        "median emission latency (s)",
        "false triggers (median)",
    ]
    rows = []
    for c in res["controls"]:
        a = c["aggregate"]["summary_over_seeds"]
        label = "control (no faults)" + (f" [{', '.join(f'{k}={v}' for k, v in c['key'].items())}]" if c["key"] else "")
        rows.append(
            [label]
            + [""] * (len(params) - 1)
            + [
                _dist(a[head]),
                "-",
                _fmt(c["aggregate"]["event_detection_rate"]["rate"]),
                _fmt(a["median_emission_latency_s"]["median"]),
                _fmt(a["false_triggers"]["median"]),
            ]
        )
    csv_rows = []
    for pt in res["points"]:
        a = pt["aggregate"]["summary_over_seeds"]
        pd = pt["paired_vs_control"][head]
        diff, ci = pd["differences"], pd["bootstrap_ci95_median"]
        if not diff["n_defined"]:
            diff_s = "n/a"
        else:
            diff_s = _fmt(diff["median"])
            if ci:
                diff_s += f" [{_fmt(ci[0])}, {_fmt(ci[1])}]"
            diff_s += f" (+{pd['n_positive']}/-{pd['n_negative']}/={pd['n_zero']} of {pd['n_paired']})"
        vals = [str(pt["parameters"][p]) for p in params]
        ev = pt["aggregate"]["event_detection_rate"]["rate"]
        rows.append([*vals, _dist(a[head]), diff_s, _fmt(ev), _fmt(a["median_emission_latency_s"]["median"]),
                     _fmt(a["false_triggers"]["median"])])  # fmt: skip
        csv_rows.append([*vals, a[head]["median"], diff["median"], pd["n_paired"], ev,
                         a["median_emission_latency_s"]["median"], a["false_triggers"]["median"]])  # fmt: skip
    table = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)] + ["| " + " | ".join(r) + " |" for r in rows]
    (sweep / "sweep_table.md").write_text("\n".join(table) + "\n", encoding="utf-8")
    with open(sweep / "sweep_table.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([*params, f"{head}_median", f"paired_diff_{head}_median", "n_paired", "event_detection_rate",
                    "median_emission_latency_s", "false_triggers_median"])  # fmt: skip
        w.writerows(csv_rows)
    plots = _sweep_plot(sweep, res)
    lines = [
        "# QuakeNode sweep report",
        "",
        f"> {BANNER}",
        f"> {_notice(res['data'])}",
        "",
        f"- Sweep `{res['name']}`, {len(res['seeds'])} seeds, same seeds for every point and its control; paired "
        "differences are point minus MATCHED control per seed (same settings, faults removed).",
        f"- Data: {_data_line(res['data'])}",
        f"- Base gap policy: {res['base_gap_policy']}. Overrides: {res['overrides'] or 'none'}",
        f"- Parameters: {res['parameters']}",
        f"- results_sha256: `{res['results_sha256']}`",
        "",
        "## Comparison table",
        "",
        *table,
        "",
        "'paired diff' = median over seeds of (point - control) with a seeded 95% bootstrap CI of the median, and "
        "(+positive/-negative/=zero of n paired seeds). Definitions: `docs/metrics.md`; "
        "gap policies: `docs/gap_policies.md`.",
        "",
        "## Plot",
        "",
    ]
    lines += (
        [f"![{p}]({p})" for p in plots] if plots else ["matplotlib is not installed: `pip install 'quakenode[plots]'`."]
    )
    (sweep / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sweep / "report.md"
