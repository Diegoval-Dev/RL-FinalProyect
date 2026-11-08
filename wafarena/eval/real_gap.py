"""Frozen reduced EXP-R1 plans and paired fast/real metric gaps."""

import hashlib
import json
import math
import os
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

from wafarena.eval.harness import EVAL_SEEDS, SessionPlan, _split_ids
from wafarena.eval.stats import bootstrap_ci

ATTACKERS = ("ATK-REF-0", "ATK-REF-1")
ATTACKER_METRICS = (
    "evasion_rate",
    "qfe",
    "qfe_c",
    "diversity",
    "uniqueness",
    "break_rate",
)
DEFENDER_METRICS = (
    "tpr",
    "er_d",
    "fpr",
    "fpr_h",
    "fpr_s",
    "fpr_h_s",
    "f1",
    "q_allow_attack",
)


def load_spec(path: Path) -> dict:
    """Require the frozen, reduced EXP-R1 design before running live traffic."""
    config = yaml.safe_load(Path(path).read_text())
    expected = {
        "exp_id": "EXP-R1",
        "eval_seeds": [0, 1, 2],
        "attacker_refs": ["ATK-REF-0", "ATK-REF-1"],
        "defender_refs": ["DEF-REF-1", "selfplay-champion"],
        "attacker_episode_starts": [1000, 1050, 1100],
        "attacker_episodes": 50,
        "attacker_query_budget": 50,
        "defender_plan_seeds": [7000, 8000, 9000],
        "defender_env_seed_starts": [10000, 10500, 11000],
        "defender_sessions": 500,
        "split": "test",
        "champion_selection": "results/summary/EXP-I3_selection.json",
        "champion_training_sha": "eea6f78",
        "champion_generation": 8,
        "reference_checkpoint_root": "checkpoints/refs",
        "pool_checkpoint_root": "checkpoints/selfplay",
    }
    if not isinstance(config, dict) or set(config) != set(expected):
        raise ValueError("invalid EXP-R1 configuration fields")
    for key, value in expected.items():
        if config[key] != value or type(config[key]) is not type(value):
            raise ValueError(f"EXP-R1 {key} must be {value!r}")
    return config


def attacker_episode_seeds(start: int) -> list[int]:
    """One 50-episode block within the frozen attacker test suite."""
    seeds = list(range(start, start + 50))
    if type(start) is not int or not set(seeds).issubset(EVAL_SEEDS):
        raise ValueError("EXP-R1 episodes must be inside attacker-eval-v1")
    return seeds


def defender_plans(plan_seed: int, env_seed_start: int) -> dict[str, list[SessionPlan]]:
    """Make 500 total test sessions, equally divided between reference attackers."""
    benign = _split_ids("benign", "test")
    attacks = _split_ids("payloads", "test")
    plans = {}
    for index, attacker in enumerate(ATTACKERS):
        offset = plan_seed + index * 10
        refs = [(True, str(ref)) for ref in np.random.default_rng(offset).choice(attacks, 25)]
        refs += [(False, str(ref)) for ref in np.random.default_rng(offset + 1).choice(benign, 225)]
        order = np.random.default_rng(offset + 2).permutation(len(refs))
        plans[attacker] = [
            SessionPlan(refs[i][0], refs[i][1], env_seed_start + index * 250 + position)
            for position, i in enumerate(order)
        ]
    return plans


def plan_sha256(plan) -> str:
    """Fingerprint the exact opponent, IDs, and environment seeds of a plan."""
    encoded = json.dumps(plan, default=vars, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def cached_r1_cell(path: Path, expected: dict, compute) -> dict:
    """Reuse a complete cell or write its validated result atomically."""
    path = Path(path)
    if path.exists():
        row = json.loads(path.read_text())
    else:
        row = {**expected, **compute()}
        for key, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                row[key] = None
        _validate_cell(row, expected, path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(row, indent=2, allow_nan=False) + "\n")
        os.replace(temporary, path)
    _validate_cell(row, expected, path)
    return row


def _validate_cell(row: dict, expected: dict, path: Path) -> None:
    if any(row.get(key) != value for key, value in expected.items()):
        raise ValueError(f"stale EXP-R1 cell: {path}")
    role = expected["role"]
    if role == "attacker":
        if row.get("episodes") != expected["planned_episodes"]:
            raise ValueError(f"incomplete EXP-R1 attacker cell: {path}")
        metrics = ATTACKER_METRICS
    elif role == "defender":
        if (
            row.get("evaluated_sessions")
            != expected["planned_sessions"] - row.get("empty_attack_sessions", -1)
            or row.get("attack_sessions") != expected["planned_attack_sessions"]
            or row.get("emitting_attack_sessions")
            != row.get("attack_sessions") - row.get("empty_attack_sessions", -1)
        ):
            raise ValueError(f"incomplete EXP-R1 defender cell: {path}")
        metrics = DEFENDER_METRICS
    else:
        raise ValueError(f"invalid EXP-R1 role: {role}")
    for metric in metrics:
        if metric not in row:
            raise ValueError(f"missing EXP-R1 {metric}: {path}")
        value = row[metric]
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            raise ValueError(f"invalid EXP-R1 {metric}: {path}")


def aggregate_gaps(cells: list[dict]) -> list[dict]:
    """Summarize absolute per-seed gaps without treating evaluation seeds as training seeds."""
    groups = defaultdict(list)
    for cell in cells:
        groups[(cell["role"], cell["agent"])].append(cell)
    rows = []
    for (role, agent), group in sorted(groups.items()):
        metrics = ATTACKER_METRICS if role == "attacker" else DEFENDER_METRICS
        if role not in ("attacker", "defender") or len(group) != 6:
            raise ValueError(f"EXP-R1 needs three paired seeds for {role}/{agent}")
        pairs = {}
        for cell in group:
            key = (cell["seed"], cell["mode"])
            if key in pairs:
                raise ValueError(f"duplicate EXP-R1 cell {key} for {agent}")
            pairs[key] = cell
        if {seed for seed, _ in pairs} != {0, 1, 2} or {mode for _, mode in pairs} != {
            "fast",
            "real",
        }:
            raise ValueError(f"EXP-R1 modes or seeds incomplete for {agent}")
        for seed in range(3):
            fast, real = pairs[(seed, "fast")], pairs[(seed, "real")]
            if any(
                fast.get(key) != real.get(key)
                for key in (
                    "plan_sha256",
                    "source_run_id",
                    "weight_sha256",
                    "opponent_run_ids",
                    "opponent_sha256",
                )
            ):
                raise ValueError(f"EXP-R1 plan or checkpoint mismatch for {agent} s{seed}")
        for metric in metrics:
            defined = []
            for seed in range(3):
                fast = pairs[(seed, "fast")].get(metric)
                real = pairs[(seed, "real")].get(metric)
                if fast is None or real is None:
                    continue
                if not all(
                    type(value) in (int, float) and math.isfinite(value) for value in (fast, real)
                ):
                    raise ValueError(f"invalid EXP-R1 {metric} for {agent} s{seed}")
                defined.append((float(fast), float(real)))
            gaps = [abs(fast - real) for fast, real in defined]
            ci = bootstrap_ci(gaps) if len(gaps) == 3 else None
            rows.append(
                {
                    "role": role,
                    "agent": agent,
                    "metric": metric,
                    "n_seeds": 3,
                    "n_defined": len(gaps),
                    "fast_mean": statistics.mean(x[0] for x in defined) if defined else None,
                    "real_mean": statistics.mean(x[1] for x in defined) if defined else None,
                    "gap_mean": statistics.mean(gaps) if gaps else None,
                    "gap_low": ci.low if ci else None,
                    "gap_high": ci.high if ci else None,
                    "fast_run_ids": " ".join(
                        pairs[(seed, "fast")]["eval_run_id"] for seed in range(3)
                    ),
                    "real_run_ids": " ".join(
                        pairs[(seed, "real")]["eval_run_id"] for seed in range(3)
                    ),
                }
            )
    return rows
