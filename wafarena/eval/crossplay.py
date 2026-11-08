"""Checkpoint-only EXP-I2 attacker–defender cross-play evaluation."""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PoolRun:
    seed: int
    source_run_id: str
    source_git_sha: str
    checkpoint_dir: Path
    generations: int


@dataclass(frozen=True)
class CellPair:
    seed: int
    source_run_id: str
    source_git_sha: str
    defender_generation: int
    attacker_generation: int
    defender_checkpoint: Path
    attacker_checkpoint: Path


def load_config(path: Path) -> dict:
    """Load the fixed EXP-I2 matrix design from YAML."""
    config = yaml.safe_load(Path(path).read_text())
    expected = {
        "exp_id": "EXP-I2",
        "run_name": "pool-crossplay",
        "source_exp_id": "EXP-I1",
        "source_condition": "pool",
        "source_seeds": [0, 1, 2],
        "generations": 8,
        "suite": "attacker-eval-v1",
        "backend": "fast",
    }
    if not isinstance(config, dict) or set(config) != set(expected):
        raise ValueError("invalid EXP-I2 configuration fields")
    for key, value in expected.items():
        if config[key] != value or type(config[key]) is not type(value):
            raise ValueError(f"EXP-I2 {key} must be {value!r}")
    return config


def discover_runs(run_path: Path, config: dict) -> list[PoolRun]:
    """Discover and validate all sibling pool seeds from one checkpoint run path."""
    run_path = Path(run_path)
    prefix = f"{config['source_exp_id']}__{config['source_condition']}"
    match = re.fullmatch(rf"{re.escape(prefix)}__s(\d+)__([0-9a-f]{{7,40}})", run_path.name)
    if match is None:
        raise ValueError(f"expected a {prefix} checkpoint run: {run_path}")
    anchor_seed, sha = int(match[1]), match[2]
    if anchor_seed not in config["source_seeds"]:
        raise ValueError(f"anchor seed s{anchor_seed} is not configured")
    runs = []
    for seed in config["source_seeds"]:
        run_id = f"{prefix}__s{seed}__{sha}"
        directory = run_path.parent / run_id
        if not directory.is_dir():
            raise ValueError(f"missing checkpoint run s{seed}: {directory}")
        for generation in range(1, config["generations"] + 1):
            for role_prefix, role, weight in (
                ("atk", "attacker", "pg.pt"),
                ("def", "defender", "dqn.pt"),
            ):
                checkpoint = directory / f"{role_prefix}-gen-{generation:02d}"
                if not all(
                    (checkpoint / name).is_file()
                    for name in ("meta.yaml", weight, "training_state.pt")
                ):
                    raise ValueError(f"missing checkpoint files: {checkpoint}")
                meta = yaml.safe_load((checkpoint / "meta.yaml").read_text())
                expected = {
                    "exp_id": config["source_exp_id"],
                    "run_id": run_id,
                    "seed": seed,
                    "git_sha": sha,
                    "generation": generation,
                }
                if meta.get("role") != role or any(
                    meta.get("train", {}).get(key) != value for key, value in expected.items()
                ):
                    raise ValueError(f"checkpoint provenance mismatch: {checkpoint}")
        runs.append(PoolRun(seed, run_id, sha, directory, config["generations"]))
    return runs


def pair_cells(runs: list[PoolRun]) -> list[CellPair]:
    """Build every same-run defender/attacker generation pair."""
    return [
        CellPair(
            run.seed,
            run.source_run_id,
            run.source_git_sha,
            defender,
            attacker,
            run.checkpoint_dir / f"def-gen-{defender:02d}",
            run.checkpoint_dir / f"atk-gen-{attacker:02d}",
        )
        for run in runs
        for defender in range(1, run.generations + 1)
        for attacker in range(1, run.generations + 1)
    ]
