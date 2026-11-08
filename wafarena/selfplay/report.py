"""Auditable EXP-I1 fixed-reference and historical-opponent comparisons."""

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path

import yaml

from wafarena.agents import load_checkpoint
from wafarena.envs.defender_env import DefenderEnv
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness
from wafarena.eval.stats import bootstrap_ci


def _probability(value, label: str, *, denominator: int | None = None):
    if value is None and denominator == 0:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"invalid {label}: {value!r}")
    return float(value)


def _count(value, label: str):
    if type(value) is not int or value < 0:
        raise ValueError(f"invalid {label}: {value!r}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _check_history_record(record: dict, pair: dict, hashes: dict, cell: Path) -> None:
    expected = {
        "condition": pair["condition"],
        "seed": pair["seed"],
        "run_id": pair["run_id"],
        "git_sha": pair["git_sha"],
        "defender_generation": pair["defender_generation"],
        "attacker_generation": pair["attacker_generation"],
        "split": "val",
        "sessions": pair["sessions"],
        **hashes,
    }
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError(f"stale or malformed historical cell: {cell}")
    requests = _count(record.get("requests"), f"historical cell requests {cell}")
    attack_requests = _count(
        record.get("attack_requests"), f"historical cell attack_requests {cell}"
    )
    if attack_requests > requests:
        raise ValueError(f"historical cell attack_requests exceeds requests: {cell}")
    _count(record.get("empty_attack_attempts"), f"historical cell empty_attack_attempts {cell}")
    _probability(record.get("tpr"), f"historical cell tpr {cell}", denominator=attack_requests)
    _probability(record.get("fpr"), f"historical cell fpr {cell}")
    for name in ("er_d", "f1", "fpr_h", "fpr_s", "fpr_h_s"):
        if name not in record:
            raise ValueError(f"missing historical cell {name}: {cell}")
        if record[name] is not None:
            _probability(record[name], f"historical cell {name} {cell}")


def collect_fixed(
    results_root: Path, checkpoint_root: Path, configurations: dict[str, dict]
) -> tuple[list[dict], list[dict], str]:
    """Require every configured clean run, generation, metric, and checkpoint."""
    rows, runs = [], []
    sha = None
    for condition, config in configurations.items():
        if condition != config["run_name"] or config["exp_id"] != "EXP-I1":
            raise ValueError(f"unexpected EXP-I1 condition {condition}")
        for seed in config["seeds"]:
            run_dir = Path(results_root) / "EXP-I1" / condition / f"s{seed}"
            if not (run_dir / "meta.yaml").is_file():
                raise ValueError(f"missing EXP-I1 run {run_dir}")
            meta = yaml.safe_load((run_dir / "meta.yaml").read_text())
            if meta.get("dirty") is not False:
                raise ValueError(f"dirty EXP-I1 run {run_dir}")
            if sha is None:
                sha = meta["git_sha"]
            if meta.get("git_sha") != sha:
                raise ValueError(f"EXP-I1 runs have different code SHA: {run_dir}")
            if (
                meta.get("exp_id") != "EXP-I1"
                or meta.get("run_name") != condition
                or meta.get("seed") != seed
                or meta.get("run_id") != f"EXP-I1__{condition}__s{seed}__{sha}"
            ):
                raise ValueError(f"EXP-I1 run metadata mismatch: {run_dir}")
            expected = dict(config)
            expected["seeds"] = [seed]
            resolved = yaml.safe_load((run_dir / "config.resolved.yaml").read_text())
            if resolved != expected:
                raise ValueError(f"EXP-I1 run config mismatch: {run_dir}")
            run_id = meta["run_id"]
            checkpoints = Path(checkpoint_root) / run_id
            markers = sorted(run_dir.glob("generation-*.json"))
            if len(markers) != config["generations"]:
                raise ValueError(f"incomplete EXP-I1 generations: {run_dir}")
            for generation in range(1, config["generations"] + 1):
                marker = run_dir / f"generation-{generation:02d}.json"
                if not marker.is_file():
                    raise ValueError(f"missing EXP-I1 generation {generation}: {run_dir}")
                record = json.loads(marker.read_text())
                if record.get("run_id") != run_id or record.get("generation") != generation:
                    raise ValueError(f"EXP-I1 generation provenance mismatch: {marker}")
                validation = record.get("validation", {})
                if validation.get("split") != "val":
                    raise ValueError(f"EXP-I1 generation is not on val: {marker}")
                if set(validation.get("attacker", {})) != set(
                    config["validation"]["attacker_defenders"]
                ) or set(validation.get("defender", {})) != set(
                    config["validation"]["defender_attackers"]
                ):
                    raise ValueError(f"missing fixed references in generation: {marker}")
                for role, weight in (("atk", "pg.pt"), ("def", "dqn.pt")):
                    checkpoint = checkpoints / f"{role}-gen-{generation:02d}"
                    if not all(
                        (checkpoint / item).is_file()
                        for item in ("meta.yaml", weight, "training_state.pt")
                    ):
                        raise ValueError(
                            f"missing checkpoint for generation {generation}: {checkpoint}"
                        )
                    checkpoint_meta = yaml.safe_load((checkpoint / "meta.yaml").read_text())
                    train = checkpoint_meta.get("train", {})
                    expected_role = "attacker" if role == "atk" else "defender"
                    if checkpoint_meta.get("role") != expected_role or any(
                        train.get(key) != value
                        for key, value in (
                            ("run_id", run_id),
                            ("seed", seed),
                            ("git_sha", sha),
                            ("generation", generation),
                        )
                    ):
                        raise ValueError(f"checkpoint provenance mismatch: {checkpoint}")
                common = {
                    "condition": condition,
                    "seed": seed,
                    "generation": generation,
                    "run_id": run_id,
                    "git_sha": sha,
                }
                for reference, metrics in validation["attacker"].items():
                    episodes = _count(metrics.get("episodes"), f"episodes {marker}")
                    if episodes != config["validation"]["attacker_episodes"]:
                        raise ValueError(f"wrong attacker episodes in generation: {marker}")
                    for name in ("evasion_rate", "episodes"):
                        value = (
                            _probability(
                                metrics.get(name), f"{name} {marker}", denominator=episodes
                            )
                            if name == "evasion_rate"
                            else episodes
                        )
                        rows.append(
                            {
                                **common,
                                "role": "attacker",
                                "reference": reference,
                                "metric": name,
                                "value": value,
                            }
                        )
                for reference, metrics in validation["defender"].items():
                    sessions = _count(metrics.get("sessions"), f"sessions {marker}")
                    if sessions != config["validation"]["defender_sessions"]:
                        raise ValueError(f"wrong defender sessions in generation: {marker}")
                    _count(
                        metrics.get("empty_attack_attempts"),
                        f"empty_attack_attempts {marker}",
                    )
                    attack_requests = _count(
                        metrics.get("attack_requests"), f"attack_requests {marker}"
                    )
                    requests = _count(metrics.get("requests"), f"requests {marker}")
                    if attack_requests > requests:
                        raise ValueError(f"attack_requests exceeds requests: {marker}")
                    for name in ("tpr", "fpr", "attack_requests"):
                        value = (
                            _probability(
                                metrics.get(name),
                                f"{name} {marker}",
                                denominator=attack_requests if name == "tpr" else None,
                            )
                            if name != "attack_requests"
                            else attack_requests
                        )
                        rows.append(
                            {
                                **common,
                                "role": "defender",
                                "reference": reference,
                                "metric": name,
                                "value": value,
                            }
                        )
            runs.append(
                {
                    "condition": condition,
                    "seed": seed,
                    "run_id": run_id,
                    "git_sha": sha,
                    "run_dir": run_dir,
                    "checkpoint_dir": checkpoints,
                    "generations": config["generations"],
                    "sessions": config["validation"]["defender_sessions"],
                }
            )
    return rows, runs, sha


def aggregate_fixed(rows: list[dict]) -> list[dict]:
    """Bootstrap over one value per seed, never over individual requests."""
    groups = defaultdict(list)
    for row in rows:
        key = (row["condition"], row["generation"], row["role"], row["reference"], row["metric"])
        groups[key].append(row)
    result = []
    for key, items in sorted(groups.items()):
        seeds = [row["seed"] for row in items]
        if len(seeds) != len(set(seeds)):
            raise ValueError(f"duplicate EXP-I1 seed for {key}")
        values = [row["value"] for row in items if row["value"] is not None]
        ci = bootstrap_ci(values) if values else None
        result.append(
            {
                "condition": key[0],
                "generation": key[1],
                "role": key[2],
                "reference": key[3],
                "metric": key[4],
                "mean": ci.mean if ci else None,
                "ci_low": ci.low if ci else None,
                "ci_high": ci.high if ci else None,
                "n_seeds": len(seeds),
                "n_defined": len(values),
                "git_sha": items[0]["git_sha"],
            }
        )
    return result


def historical_pairs(runs: list[dict]) -> list[dict]:
    """All earlier attackers from the *same* run for each defender generation."""
    return [
        {**run, "defender_generation": defender, "attacker_generation": attacker}
        for run in runs
        for defender in range(2, run["generations"] + 1)
        for attacker in range(1, defender)
    ]


def evaluate_history(runs: list[dict], results_root: Path, *, backend=None) -> list[dict]:
    """Evaluate and cache previous-generation cells on one fixed val session plan."""
    own_backend = backend is None
    backend = backend or resolve_backend("fast")
    rows = []
    try:
        for pair in historical_pairs(runs):
            condition, seed = pair["condition"], pair["seed"]
            defender_gen, attacker_gen = pair["defender_generation"], pair["attacker_generation"]
            cell = (
                Path(results_root)
                / "_history_cells"
                / condition
                / f"s{seed}"
                / f"def-{defender_gen:02d}_atk-{attacker_gen:02d}.json"
            )
            checkpoints = pair["checkpoint_dir"]
            hashes = {
                "defender_sha256": _file_sha256(checkpoints / f"def-gen-{defender_gen:02d}/dqn.pt"),
                "attacker_sha256": _file_sha256(checkpoints / f"atk-gen-{attacker_gen:02d}/pg.pt"),
            }
            if cell.exists():
                record = json.loads(cell.read_text())
            else:
                defender = load_checkpoint(checkpoints / f"def-gen-{defender_gen:02d}")
                env = DefenderEnv(
                    backend,
                    attacker={
                        "type": "checkpoint",
                        "path": str(checkpoints / f"atk-gen-{attacker_gen:02d}"),
                    },
                    split="val",
                    attack_split="val",
                )
                plan = harness.build_session_plan(
                    harness.DefenderSuite(
                        "EXP-I1-history",
                        "val",
                        "val",
                        (f"atk-gen-{attacker_gen:02d}",),
                        n_sessions=pair["sessions"],
                        attack_ratio=0.5,
                    )
                )
                records = [
                    item
                    for session in plan
                    for item in harness._play_session(defender, env, session)
                ]
                record = {
                    "condition": condition,
                    "seed": seed,
                    "run_id": pair["run_id"],
                    "git_sha": pair["git_sha"],
                    "defender_generation": defender_gen,
                    "attacker_generation": attacker_gen,
                    "split": "val",
                    "sessions": len(plan),
                    "empty_attack_attempts": env.empty_attack_attempts,
                    **hashes,
                    **{
                        key: None
                        if isinstance(value, float) and not math.isfinite(value)
                        else value
                        for key, value in harness.summarize_defender(records).items()
                    },
                }
                _check_history_record(record, pair, hashes, cell)
                cell.parent.mkdir(parents=True, exist_ok=True)
                temporary = cell.with_suffix(".json.tmp")
                temporary.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
                os.replace(temporary, cell)
            _check_history_record(record, pair, hashes, cell)
            rows.append(record)
    finally:
        if own_backend:
            backend.close()
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty EXP-I1 CSV: {path}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
