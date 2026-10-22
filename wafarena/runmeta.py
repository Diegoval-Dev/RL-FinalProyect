"""Run identity and provenance: run_id, results tree, git guard, meta.yaml (experimentos.md)."""

import platform
import socket
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

import wafarena

GUARDED_PATHS = ("wafarena", "configs")
META_FILE = "meta.yaml"


class DirtyTreeError(RuntimeError):
    """The working tree has uncommitted changes in code or configs."""


@dataclass(frozen=True)
class GitInfo:
    sha: str
    branch: str


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


def git_info(repo: Path) -> GitInfo:
    return GitInfo(
        sha=_git(repo, "rev-parse", "--short=7", "HEAD"),
        branch=_git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
    )


def uncommitted_changes(repo: Path, paths: tuple[str, ...] = GUARDED_PATHS) -> list[str]:
    """Modified, staged or untracked files under `paths`, as `git status --porcelain` lines."""
    out = _git(repo, "status", "--porcelain", "--untracked-files=all", "--", *paths)
    return [line for line in out.splitlines() if line.strip()]


def ensure_clean(repo: Path, *, allow_dirty: bool) -> None:
    changes = uncommitted_changes(repo)
    if changes and not allow_dirty:
        listing = "\n  ".join(changes)
        raise DirtyTreeError(
            f"refusing to run with uncommitted changes in {', '.join(GUARDED_PATHS)} "
            "(commit them or pass --allow-dirty; such runs do not count for the report):\n"
            f"  {listing}"
        )


def run_id(exp_id: str, run_name: str, seed: int, sha: str) -> str:
    return f"{exp_id}__{run_name}__s{seed}__{sha}"


def run_dir(results_root: Path, exp_id: str, run_name: str, seed: int) -> Path:
    return Path(results_root) / exp_id / run_name / f"s{seed}"


def build_meta(config: dict[str, Any], *, seed: int, repo: Path, allow_dirty: bool) -> dict:
    info = git_info(repo)
    return {
        "run_id": run_id(config["exp_id"], config["run_name"], seed, info.sha),
        "exp_id": config["exp_id"],
        "run_name": config["run_name"],
        "seed": seed,
        "git_sha": info.sha,
        "branch": info.branch,
        "dirty": bool(uncommitted_changes(repo)),
        "allow_dirty": allow_dirty,
        "date": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "machine": socket.gethostname(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "contract_versions": dict(wafarena.CONTRACT_VERSIONS),
    }


def write_meta(directory: Path, meta: dict[str, Any]) -> None:
    Path(directory).mkdir(parents=True, exist_ok=True)
    (Path(directory) / META_FILE).write_text(yaml.safe_dump(meta, sort_keys=False))


def finalize_meta(directory: Path, *, duration_s: float) -> None:
    path = Path(directory) / META_FILE
    meta = yaml.safe_load(path.read_text())
    meta["duration_s"] = duration_s
    path.write_text(yaml.safe_dump(meta, sort_keys=False))
