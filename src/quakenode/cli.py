"""Command line interface: `quakenode demo|run|sweep|compare|report|validate|version`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quakenode import __version__
from quakenode.config import ConfigError, apply_overrides, load_raw, parse_config

BANNER = "QuakeNode is a research testbed, not an operational warning system."


def _cmd_validate(args: argparse.Namespace) -> int:
    raw, _ = apply_overrides(load_raw(args.config), args.set)
    cfg = parse_config(raw, args.config)
    print(
        f"{args.config}: OK (experiment {cfg.name!r}, {len(cfg.seeds)} seeds, {len(cfg.scenario.stations)} stations, "
        f"{len(cfg.faults)} fault(s), detector {cfg.detector.name!r}, sweep: {'yes' if cfg.sweep else 'no'})"
    )
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    from quakenode.experiment import run_experiment

    raw, applied = apply_overrides(load_raw(args.config), args.set)
    parse_config(raw, args.config)
    if applied:
        print("overrides: " + ", ".join(f"{a['path']}={a['value']!r}" for a in applied))
    out = run_experiment(raw, args.config, out_root=Path(args.out_dir) if args.out_dir else None, overrides=applied)
    print(f"run directory: {out}")
    print(f"report: {out / 'report.md'}")
    return 0


def _cmd_sweep(args: argparse.Namespace) -> int:
    from quakenode.experiment import run_sweep

    raw, applied = apply_overrides(load_raw(args.config), args.set)
    parse_config(raw, args.config)
    if applied:
        print("overrides: " + ", ".join(f"{a['path']}={a['value']!r}" for a in applied))
    out = run_sweep(raw, args.config, out_root=Path(args.out_dir) if args.out_dir else None, overrides=applied)
    print(f"sweep directory: {out}\n")
    print((out / "sweep_table.md").read_text(encoding="utf-8"))
    print(f"report: {out / 'report.md'}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    from quakenode.compare import run_compare, split_arm

    raw = load_raw(args.config)
    a_sets, b_sets = split_arm(args.a), split_arm(args.b)
    parse_config(apply_overrides(raw, [*args.set, *a_sets])[0], args.config)
    parse_config(apply_overrides(raw, [*args.set, *b_sets])[0], args.config)
    print(f"arm A overrides: {', '.join(a_sets)}\narm B overrides: {', '.join(b_sets)}")
    out = run_compare(raw, args.config, a_sets, b_sets, args.set, Path(args.out_dir) if args.out_dir else None)
    print(f"compare directory: {out}\n")
    print((out / "compare.md").read_text(encoding="utf-8"))
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    """Write the packaged SYNTHETIC example configs to a directory and run the first one."""
    from importlib import resources

    from quakenode.experiment import run_experiment

    target = Path(args.dir)
    names = ("config.yaml", "sweep.yaml")
    existing = [n for n in names if (target / n).exists()]
    if existing:
        raise ConfigError(
            f"{target}: {', '.join(existing)} already exists; choose another --dir (nothing is overwritten)"
        )
    target.mkdir(parents=True, exist_ok=True)
    for n in names:
        text = resources.files("quakenode").joinpath("demo_data", n).read_text(encoding="utf-8")
        (target / n).write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {target / 'config.yaml'} and {target / 'sweep.yaml'} (SYNTHETIC example scenario)")
    cfg = str(target / "config.yaml")
    raw = load_raw(cfg)
    parse_config(raw, cfg)
    out = run_experiment(raw, cfg, out_root=target / "runs")
    print(f"run directory: {out}")
    print(f"report: {out / 'report.md'}")
    print(f"next: quakenode sweep {target / 'sweep.yaml'} --out-dir {target / 'runs'}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from quakenode.report import write_report, write_sweep_report

    d = Path(args.run_dir)
    if (d / "sweep_results.json").exists():
        print(f"report: {write_sweep_report(d)}")
    elif (d / "metrics.json").exists():
        print(f"report: {write_report(d)}")
    else:
        raise ConfigError(f"{d}: not a QuakeNode run or sweep directory (no metrics.json / sweep_results.json)")
    return 0


def _cmd_version(args: argparse.Namespace) -> int:
    print(f"quakenode {__version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quakenode", description=f"{BANNER} All scenario data are SYNTHETIC.")
    sub = p.add_subparsers(dest="command", required=True)
    for name, fn, help_ in (
        ("run", _cmd_run, "run one experiment from a YAML config"),
        ("sweep", _cmd_sweep, "grid over one or two fault parameters, paired against a no-fault control"),
        ("validate", _cmd_validate, "validate a YAML config without running"),
    ):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("config", help="path to the YAML config")
        sp.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="override a config value by dotted path, e.g. detector.name=recursive_sta_lta "
                             "or faults.0.p=0.02 (repeatable; validated by the same strict schema)")  # fmt: skip
        if name != "validate":
            sp.add_argument("--out-dir", default=None, help="parent directory for the new run directory")
        sp.set_defaults(func=fn)
    sp = sub.add_parser("compare", help="run two arms of one scenario with different overrides and pair them")
    sp.add_argument("config", help="path to the YAML config")
    sp.add_argument("--a", required=True, metavar="KEY=VALUE[,KEY=VALUE]", help="overrides for arm A")
    sp.add_argument("--b", required=True, metavar="KEY=VALUE[,KEY=VALUE]", help="overrides for arm B")
    sp.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override applied to both arms")
    sp.add_argument("--out-dir", default=None, help="parent directory for the new compare directory")
    sp.set_defaults(func=_cmd_compare)
    sp = sub.add_parser("demo", help="write the SYNTHETIC example configs to a directory and run the first one")
    sp.add_argument("--dir", default="quakenode_demo", help="directory to create (default: ./quakenode_demo)")
    sp.set_defaults(func=_cmd_demo)
    sp = sub.add_parser("report", help="(re)write report.md and plots for a run or sweep directory")
    sp.add_argument("run_dir")
    sp.set_defaults(func=_cmd_report)
    sp = sub.add_parser("version", help="print the version")
    sp.set_defaults(func=_cmd_version)
    return p


def main(argv: list[str] | None = None) -> int:
    print(BANNER)
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
