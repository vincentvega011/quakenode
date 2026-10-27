"""`quakenode demo` and the packaged example configs (SYNTHETIC)."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from importlib import resources
from pathlib import Path

from quakenode.cli import BANNER, main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "synthetic_network"


class Demo(unittest.TestCase):
    def test_packaged_configs_match_repo_examples(self):
        for name in ("config.yaml", "sweep.yaml"):
            packaged = resources.files("quakenode").joinpath("demo_data", name).read_text(encoding="utf-8")
            self.assertEqual(packaged, (EXAMPLES / name).read_text(encoding="utf-8"), name)

    def test_demo_writes_configs_runs_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "demo"
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["demo", "--dir", str(target)])
            self.assertEqual(code, 0, err.getvalue())
            self.assertIn(BANNER, out.getvalue())
            self.assertTrue((target / "config.yaml").exists() and (target / "sweep.yaml").exists())
            runs = list((target / "runs").iterdir())
            self.assertEqual(len(runs), 1)
            self.assertTrue((runs[0] / "report.md").exists())
            err2 = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err2):
                code2 = main(["demo", "--dir", str(target)])
            self.assertEqual(code2, 2)
            self.assertIn("already exists", err2.getvalue())
            self.assertEqual(len(list((target / "runs").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
