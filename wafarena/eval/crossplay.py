"""Checkpoint-only EXP-I2 attacker–defender cross-play evaluation."""

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from wafarena.agents import load_checkpoint
from wafarena.agents.base import (
    ContractVersionError,
    check_contract_versions,
    current_contract_versions,
)
from wafarena.eval import harness
from wafarena.eval.stats import bootstrap_ci


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
                contracts = meta.get("contract_versions")
                if not isinstance(contracts, dict) or set(contracts) != set(
                    current_contract_versions(role)
                ):
                    raise ValueError(f"checkpoint contract metadata mismatch: {checkpoint}")
                try:
                    check_contract_versions(contracts)
                except ContractVersionError as exc:
                    raise ValueError(f"checkpoint contract mismatch: {checkpoint}") from exc
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


def _weight_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _check_cell(record: dict, expected: dict, cell: Path, episodes: int) -> None:
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError(f"stale or malformed cross-play cell: {cell}")
    evasions = record.get("evasions")
    rate = record.get("evasion_rate")
    queries = record.get("queries_total")
    if (
        record.get("episodes") != episodes
        or type(evasions) is not int
        or not 0 <= evasions <= episodes
        or type(queries) is not int
        or not 0 <= queries <= episodes * expected["query_budget"]
        or type(rate) not in (int, float)
        or not math.isfinite(rate)
        or not math.isclose(rate, evasions / episodes, abs_tol=1e-12)
    ):
        raise ValueError(f"stale or malformed cross-play cell: {cell}")


def evaluate_cell(
    pair: CellPair,
    config: dict,
    cell: Path,
    eval_run_id: str,
    eval_sha: str,
    backend,
) -> dict:
    """Evaluate one fixed test-suite pair, or validate its cached result."""
    if eval_run_id != f"{config['exp_id']}__{config['run_name']}__s{pair.seed}__{eval_sha}":
        raise ValueError(f"evaluation run ID does not match seed s{pair.seed}")
    suite = harness.ATTACKER_SUITES[config["suite"]]
    if suite.split != "test" or len(suite.seeds) != 200 or suite.query_budget != 50:
        raise ValueError("EXP-I2 requires the full attacker-eval-v1 test suite")
    expected = {
        "seed": pair.seed,
        "source_run_id": pair.source_run_id,
        "source_git_sha": pair.source_git_sha,
        "eval_run_id": eval_run_id,
        "eval_git_sha": eval_sha,
        "defender_generation": pair.defender_generation,
        "attacker_generation": pair.attacker_generation,
        "suite": suite.name,
        "split": suite.split,
        "backend": config["backend"],
        "query_budget": suite.query_budget,
        "attacker_sha256": _weight_hash(pair.attacker_checkpoint / "pg.pt"),
        "defender_sha256": _weight_hash(pair.defender_checkpoint / "dqn.pt"),
    }
    cell = Path(cell)
    if cell.exists():
        record = json.loads(cell.read_text())
    else:
        attacker = load_checkpoint(pair.attacker_checkpoint)
        results = harness.run_attacker_suite(
            attacker,
            suite.name,
            defender={"type": "checkpoint", "path": str(pair.defender_checkpoint)},
            backend=backend,
        )
        if len(results) != 200 or [item.seed for item in results] != list(suite.seeds):
            raise ValueError(f"cross-play cell requires 200 episodes: {cell}")
        if any(
            type(item.evaded) is not bool or not 0 <= item.queries_used <= 50 for item in results
        ):
            raise ValueError(f"invalid cross-play episode result: {cell}")
        evasions = sum(item.evaded for item in results)
        record = {
            **expected,
            "episodes": len(results),
            "evasions": evasions,
            "evasion_rate": evasions / len(results),
            "queries_total": sum(item.queries_used for item in results),
        }
        _check_cell(record, expected, cell, 200)
        cell.parent.mkdir(parents=True, exist_ok=True)
        temporary = cell.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
        os.replace(temporary, cell)
    _check_cell(record, expected, cell, 200)
    return record


def aggregate_cells(rows: list[dict], config: dict) -> list[dict]:
    """Summarize each matrix position over exactly three distinct pool seeds."""
    expected_count = len(config["source_seeds"]) * config["generations"] ** 2
    if len(rows) != expected_count:
        raise ValueError(f"EXP-I2 requires {expected_count} cells, got {len(rows)}")
    seen = set()
    groups = {}
    source_shas, eval_shas = set(), set()
    for row in rows:
        seed = row["seed"]
        defender = row["defender_generation"]
        attacker = row["attacker_generation"]
        key = (seed, defender, attacker)
        if key in seen:
            raise ValueError(f"duplicate EXP-I2 cell {key}")
        seen.add(key)
        if (
            seed not in config["source_seeds"]
            or not 1 <= defender <= config["generations"]
            or not 1 <= attacker <= config["generations"]
            or row["episodes"] != 200
            or row["evasions"] != round(row["evasion_rate"] * 200)
        ):
            raise ValueError(f"invalid EXP-I2 cell {key}")
        source_shas.add(row["source_git_sha"])
        eval_shas.add(row["eval_git_sha"])
        groups.setdefault((defender, attacker), []).append(row)
    if len(source_shas) != 1 or len(eval_shas) != 1:
        raise ValueError("EXP-I2 cells have mixed source or evaluation code SHA")
    matrix = []
    for defender in range(1, config["generations"] + 1):
        for attacker in range(1, config["generations"] + 1):
            group = groups.get((defender, attacker), [])
            if {row["seed"] for row in group} != set(config["source_seeds"]):
                raise ValueError(f"missing EXP-I2 seed at def-{defender}/atk-{attacker}")
            ci = bootstrap_ci(
                [row["evasion_rate"] for row in sorted(group, key=lambda r: r["seed"])]
            )
            matrix.append(
                {
                    "defender_generation": defender,
                    "attacker_generation": attacker,
                    "mean_er": ci.mean,
                    "ci_low": ci.low,
                    "ci_high": ci.high,
                    "n_seeds": len(group),
                    "episodes_total": sum(row["episodes"] for row in group),
                    "evasions_total": sum(row["evasions"] for row in group),
                    "source_git_sha": next(iter(source_shas)),
                    "eval_git_sha": next(iter(eval_shas)),
                    "suite": config["suite"],
                }
            )
    return matrix
