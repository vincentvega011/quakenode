"""Guard against .gitignore rules that silently hide package, test or script source from commits.

An unanchored `data/` rule once ignored `src/quakenode/data/`, so a fresh clone lacked that package and CI failed.
Skipped when not inside a git work tree (for example an installed sdist).
"""

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _in_git_tree() -> bool:
    if shutil.which("git") is None:
        return False
    r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


@unittest.skipUnless(_in_git_tree(), "not a git work tree")
class SourceNotIgnored(unittest.TestCase):
    def test_no_source_file_is_gitignored(self):
        files = [
            p.relative_to(ROOT).as_posix()
            for top in ("src", "tests", "scripts", "examples")
            for p in (ROOT / top).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and ".egg-info" not in str(p)
        ]
        r = subprocess.run(
            ["git", "check-ignore", "--stdin"], cwd=ROOT, input="\n".join(files), capture_output=True, text=True
        )
        self.assertEqual(
            r.stdout.split(), [], "source files matched by .gitignore (they would be missing from a clone)"
        )


if __name__ == "__main__":
    unittest.main()
