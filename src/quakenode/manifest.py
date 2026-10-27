"""Run manifest: what produced a result (code, environment, config, seeds, datasets).

Unknown values are None with a stated reason, never guessed.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1"
TRACKED_DEPENDENCIES = ("quakenode", "numpy", "scipy", "obspy", "pyyaml", "pydantic", "matplotlib")


@dataclass(frozen=True)
class DatasetRecord:
    """Provenance of one dataset. Everything except id is optional but explicit (None = unknown)."""

    id: str
    source_url: str | None = None
    doi: str | None = None
    license_note: str | None = None
    sha256: str | None = None
    retrieval_date: str | None = None


@dataclass
class RunManifest:
    schema_version: str
    run_id: str
    created_utc: str
    git_commit: str | None
    git_dirty: bool | None
    git_unavailable_reason: str | None
    python_version: str
    platform: str
    dependencies: dict[str, str | None]
    config: dict[str, Any]
    seeds: list[int]
    datasets: list[DatasetRecord]
    metric_definition_version: str
    output_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        config: dict[str, Any],
        seeds: list[int],
        metric_definition_version: str,
        repo_dir: str | Path,
        datasets: list[DatasetRecord] | None = None,
        output_paths: list[str] | None = None,
        warnings: list[str] | None = None,
        exclusions: list[str] | None = None,
    ) -> RunManifest:
        """Collect environment facts now and bundle them with the caller's config."""
        commit, dirty, reason = git_state(repo_dir)
        return cls(
            schema_version=SCHEMA_VERSION,
            run_id=str(uuid.uuid4()),
            created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            git_commit=commit,
            git_dirty=dirty,
            git_unavailable_reason=reason,
            python_version=platform.python_version(),
            platform=platform.platform(),
            dependencies=dependency_versions(),
            config=config,
            seeds=list(seeds),
            datasets=list(datasets or []),
            metric_definition_version=metric_definition_version,
            output_paths=list(output_paths or []),
            warnings=list(warnings or []),
            exclusions=list(exclusions or []),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunManifest:
        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(f"unsupported manifest schema_version {version!r}; this build reads {SCHEMA_VERSION!r}")
        fields = dict(data)
        fields["datasets"] = [DatasetRecord(**d) for d in fields.get("datasets", [])]
        try:
            return cls(**fields)
        except TypeError as exc:  # missing or unknown keys
            raise ValueError(f"malformed manifest: {exc}") from exc

    @classmethod
    def from_json(cls, text: str) -> RunManifest:
        return cls.from_dict(json.loads(text))


def dependency_versions(names: tuple[str, ...] = TRACKED_DEPENDENCIES) -> dict[str, str | None]:
    """Installed version per distribution name; None if not installed."""
    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def git_state(repo_dir: str | Path) -> tuple[str | None, bool | None, str | None]:
    """Return (commit, dirty, reason). If git info is unavailable: (None, None, why).

    dirty is True when `git status --porcelain` lists anything, including untracked files
    that are not gitignored.
    """

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True, check=False)

    try:
        head = run("rev-parse", "HEAD")
    except FileNotFoundError:
        return None, None, "git executable not found"
    except NotADirectoryError:
        return None, None, f"{repo_dir} is not a directory"
    if head.returncode != 0:
        return None, None, f"not a git repository with a commit: {head.stderr.strip()}"
    status = run("status", "--porcelain")
    if status.returncode != 0:
        return head.stdout.strip(), None, f"git status failed: {status.stderr.strip()}"
    return head.stdout.strip(), bool(status.stdout.strip()), None


RESULT_HASH_EXCLUDED_KEYS = ("manifest", "provenance", "results_sha256")


def results_sha256(result: dict[str, Any]) -> str:
    """SHA-256 of the canonical JSON of a result payload, excluding run-specific keys.

    Excludes manifest (run_id, created_utc, git state) and provenance, so two runs of
    deterministic code give the same hash.
    """
    payload = {k: v for k, v in result.items() if k not in RESULT_HASH_EXCLUDED_KEYS}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def provenance(config: dict[str, Any], script: str | Path) -> dict[str, str]:
    """Python version plus hashes of the input config and of the source (script + quakenode package)."""
    script_path = Path(script).resolve()
    package_dir = Path(__file__).resolve().parent
    sources = {f"experiments/{script_path.name}": script_path}
    sources.update({f"quakenode/{p.relative_to(package_dir).as_posix()}": p for p in package_dir.rglob("*.py")})
    source_digest = hashlib.sha256()
    for name in sorted(sources):
        source_digest.update(name.encode() + b"\0" + sources[name].read_bytes() + b"\0")
    return {
        "python_version": platform.python_version(),
        "quakenode_version": metadata.version("quakenode"),
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        "source_sha256": source_digest.hexdigest(),
    }
