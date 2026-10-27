"""Run manifest contracts."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from quakenode import manifest
from quakenode.manifest import DatasetRecord, RunManifest, git_state


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _make_repo(path: Path) -> None:
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "t@example.invalid")
    _git(path, "config", "user.name", "t")
    (path / "a.txt").write_text("one")
    _git(path, "add", "a.txt")
    _git(path, "commit", "-q", "-m", "init")


class ManifestTests(unittest.TestCase):
    def _manifest(self, repo_dir) -> RunManifest:
        return RunManifest.create(
            config={"k": 1},
            seeds=[1, 2],
            metric_definition_version="test_v1",
            repo_dir=repo_dir,
            datasets=[DatasetRecord(id="synthetic")],
            warnings=["w"],
        )

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = self._manifest(tmp)
        restored = RunManifest.from_json(original.to_json())
        self.assertEqual(original, restored)
        self.assertEqual(restored.datasets[0].doi, None)
        self.assertEqual(restored.schema_version, manifest.SCHEMA_VERSION)

    def test_unknown_schema_version_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._manifest(tmp).to_dict()
        data["schema_version"] = "999"
        with self.assertRaises(ValueError):
            RunManifest.from_dict(data)
        del data["schema_version"]
        with self.assertRaises(ValueError):
            RunManifest.from_dict(data)

    def test_unknown_or_missing_fields_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._manifest(tmp).to_dict()
        with self.assertRaises(ValueError):
            RunManifest.from_dict({**data, "surprise": 1})
        del data["seeds"]
        with self.assertRaises(ValueError):
            RunManifest.from_dict(data)

    def test_git_dirty_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _make_repo(repo)
            commit, dirty, reason = git_state(repo)
            self.assertEqual(len(commit), 40)
            self.assertIs(dirty, False)
            self.assertIsNone(reason)
            (repo / "a.txt").write_text("two")
            self.assertIs(git_state(repo)[1], True)

    def test_not_a_repo_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            commit, dirty, reason = git_state(tmp)
        self.assertIsNone(commit)
        self.assertIsNone(dirty)
        self.assertIn("not a git repository", reason)

    def test_missing_git_executable_is_explicit(self):
        with mock.patch.object(manifest.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(git_state("."), (None, None, "git executable not found"))

    def test_dependencies_report_none_when_not_installed(self):
        versions = manifest.dependency_versions(("quakenode", "definitely-not-installed-pkg"))
        self.assertIsNotNone(versions["quakenode"])
        self.assertIsNone(versions["definitely-not-installed-pkg"])

    def test_json_is_plain_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed = json.loads(self._manifest(tmp).to_json())
        self.assertEqual(parsed["seeds"], [1, 2])


if __name__ == "__main__":
    unittest.main()


class ResultsHashTests(unittest.TestCase):
    def test_hash_ignores_manifest_and_provenance_only(self):
        base = {"a": 1, "b": [1.5, 2]}
        h = manifest.results_sha256(base)
        self.assertEqual(h, manifest.results_sha256({**base, "manifest": {"run_id": "x"}, "provenance": {"p": 1}}))
        self.assertNotEqual(h, manifest.results_sha256({**base, "a": 2}))
