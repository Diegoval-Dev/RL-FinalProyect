"""Run EXP-R1 reduced checkpoint evaluations in fast and real backends."""

import argparse
import csv
import json
from pathlib import Path

import yaml

from scripts.run_i345 import discover_pool_defenders, i5_emitting_plan
from wafarena.agents import load_checkpoint
from wafarena.agents.base import check_contract_versions
from wafarena.defenders.driver import DefenderDriver
from wafarena.envs.attacker_env import AttackerEnv
from wafarena.envs.defender_env import DefenderEnv
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness
from wafarena.eval.final_generalization import file_sha256, select_pool_champion
from wafarena.eval.real_gap import (
    ATTACKER_METRICS,
    DEFENDER_METRICS,
    aggregate_gaps,
    attacker_episode_seeds,
    cached_r1_cell,
    defender_plans,
    load_spec,
    plan_sha256,
)
from wafarena.runmeta import (
    DirtyTreeError,
    build_meta,
    git_info,
    run_id,
    uncommitted_changes,
    write_meta,
)
from wafarena.selfplay.report import write_csv

SPEC = Path("configs/eval/EXP-R1/real-validation.yaml")
HISTORY = Path("results/summary/EXP-I1_history.csv")
WEIGHTS = {"ATK-REF-0": "bandit.npz", "ATK-REF-1": "pg.pt", "DEF-REF-1": "dqn.pt"}


def _reference(path: Path, agent: str, role: str) -> dict:
    weights = Path(path) / WEIGHTS[agent]
    meta_path = Path(path) / "meta.yaml"
    if not weights.is_file() or not meta_path.is_file():
        raise ValueError(f"missing EXP-R1 reference checkpoint: {path}")
    meta = yaml.safe_load(meta_path.read_text())
    train = meta.get("train", {})
    if (
        meta.get("agent_id") != agent
        or meta.get("role") != role
        or not isinstance(train.get("run_id"), str)
        or not isinstance(train.get("git_sha"), str)
        or type(train.get("seed")) is not int
        or not train["run_id"].endswith(f"__{train['git_sha']}")
    ):
        raise ValueError(f"EXP-R1 reference provenance mismatch: {path}")
    check_contract_versions(meta["contract_versions"])
    return {
        "agent": agent,
        "role": role,
        "path": Path(path),
        "source_run_id": train["run_id"],
        "source_git_sha": train["git_sha"],
        "weight_sha256": file_sha256(weights),
    }


def discover_sources(config: dict) -> dict[str, dict]:
    """Validate the three references and the T08 val-selected champion."""
    refs = Path(config["reference_checkpoint_root"])
    sources = {
        agent: _reference(refs / agent, agent, "attacker") for agent in config["attacker_refs"]
    }
    sources["DEF-REF-1"] = _reference(refs / "DEF-REF-1", "DEF-REF-1", "defender")
    with HISTORY.open(newline="") as handle:
        history = list(csv.DictReader(handle))
    selection = select_pool_champion(
        history, source_sha=config["champion_training_sha"], fpr_cap=0.0
    )
    saved = json.loads(Path(config["champion_selection"]).read_text())
    if saved != selection:
        raise ValueError("EXP-R1 champion selection differs from EXP-I1 val history")
    candidates = discover_pool_defenders(
        Path(config["pool_checkpoint_root"]), config["champion_training_sha"]
    )
    chosen = next(item for item in candidates if item["seed"] == selection["winner_seed"])
    sources["selfplay-champion"] = {
        "agent": "selfplay-champion",
        "role": "defender",
        "path": chosen["path"],
        "source_run_id": chosen["source_run_id"],
        "source_git_sha": chosen["source_git_sha"],
        "weight_sha256": chosen["defender_sha256"],
    }
    return sources


def _run_dir(root: Path, agent: str, mode: str, seed: int, role: str) -> Path:
    return root / "EXP-R1" / f"{role}-{agent}-{mode}" / f"s{seed}"


def _prepare_run(directory: Path, name: str, seed: int, sha: str, expected: dict) -> str:
    identity = run_id("EXP-R1", name, seed, sha)
    meta_path = directory / "meta.yaml"
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text())
        if any(
            meta.get(key) != value
            for key, value in (
                ("run_id", identity),
                ("git_sha", sha),
                ("source_run_id", expected["source_run_id"]),
                ("plan_sha256", expected["plan_sha256"]),
                ("dirty", False),
            )
        ):
            raise ValueError(f"stale EXP-R1 run metadata: {directory}")
    else:
        meta = build_meta(
            {"exp_id": "EXP-R1", "run_name": name},
            seed=seed,
            repo=Path.cwd(),
            allow_dirty=False,
        )
        if meta["dirty"]:
            raise DirtyTreeError("refusing EXP-R1 with an uncommitted tree")
        meta["source_run_id"] = expected["source_run_id"]
        meta["plan_sha256"] = expected["plan_sha256"]
        write_meta(directory, meta)
    return identity


def _attacker_metrics(source: dict, defender: dict, backend, seeds: list[int]) -> dict:
    agent = load_checkpoint(source["path"])
    policy = DefenderDriver(load_checkpoint(defender["path"]))
    env = AttackerEnv(backend=backend, defender=policy, split="test", query_budget=50)
    episodes = [harness._play_episode(agent, env, seed) for seed in seeds]
    return harness.summarize_attacker(episodes, query_budget=50)


def _defender_metrics(source: dict, attackers: dict, backend, plans: dict, emitting: dict) -> dict:
    policy = load_checkpoint(source["path"])
    records = []
    for name, source_attacker in attackers.items():
        env = DefenderEnv(
            backend=backend,
            attacker={"type": "checkpoint", "path": str(source_attacker["path"])},
            split="test",
            attack_split="test",
        )
        for item in emitting[name]:
            records.extend(harness._play_session(policy, env, item))
        if env.empty_attack_attempts:
            raise ValueError(f"EXP-R1 preflight disagrees with {name} defender sessions")
    attack_sessions = sum(item.is_attack for items in plans.values() for item in items)
    emitting_attacks = sum(item.is_attack for items in emitting.values() for item in items)
    return {
        **harness.summarize_defender(records),
        "evaluated_sessions": sum(map(len, emitting.values())),
        "attack_sessions": attack_sessions,
        "emitting_attack_sessions": emitting_attacks,
        "empty_attack_sessions": attack_sessions - emitting_attacks,
        "effect_attack_requests": sum(record.is_attack and record.effect for record in records),
    }


def _cell(root: Path, source: dict, opponents: dict, mode: str, seed: int, plan, sha: str) -> dict:
    role, agent = source["role"], source["agent"]
    run_name = f"{role}-{agent}-{mode}"
    directory = _run_dir(root, agent, mode, seed, role)
    plan_hash = plan_sha256(plan)
    expected = {
        "exp_id": "EXP-R1",
        "role": role,
        "agent": agent,
        "mode": mode,
        "seed": seed,
        "split": "test",
        "plan_sha256": plan_hash,
        "eval_git_sha": sha,
        "source_run_id": source["source_run_id"],
        "source_git_sha": source["source_git_sha"],
        "weight_sha256": source["weight_sha256"],
        "opponent_run_ids": " ".join(
            opponents[name]["source_run_id"] for name in sorted(opponents)
        ),
        "opponent_sha256": " ".join(opponents[name]["weight_sha256"] for name in sorted(opponents)),
        **(
            {"planned_episodes": 50, "query_budget": 50}
            if role == "attacker"
            else {"planned_sessions": 500, "planned_attack_sessions": 50}
        ),
    }
    expected["eval_run_id"] = _prepare_run(directory, run_name, seed, sha, expected)

    def compute():
        backend = resolve_backend(mode)
        try:
            if role == "attacker":
                return _attacker_metrics(source, opponents["DEF-REF-1"], backend, plan["seeds"])
            emitting = {
                name: i5_emitting_plan(opponents[name], items)[0] for name, items in plan.items()
            }
            return _defender_metrics(source, opponents, backend, plan, emitting)
        finally:
            backend.close()

    return cached_r1_cell(directory / "cell.json", expected, compute)


def _compact(row: dict) -> dict:
    fields = (
        "exp_id",
        "role",
        "agent",
        "mode",
        "seed",
        "split",
        "planned_episodes",
        "planned_sessions",
        "planned_attack_sessions",
        "episodes",
        "evasions",
        "evaluated_sessions",
        "attack_sessions",
        "emitting_attack_sessions",
        "empty_attack_sessions",
        "requests",
        "attack_requests",
        "effect_attack_requests",
        "plan_sha256",
        "eval_run_id",
        "eval_git_sha",
        "source_run_id",
        "source_git_sha",
        "weight_sha256",
        "opponent_run_ids",
        "opponent_sha256",
        *ATTACKER_METRICS,
        *DEFENDER_METRICS,
    )
    return {key: row.get(key) for key in fields}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=SPEC)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--summary-dir", type=Path, default=Path("results/summary"))
    args = parser.parse_args()
    if changes := uncommitted_changes(Path.cwd(), ("wafarena", "configs", "scripts", "Makefile")):
        raise DirtyTreeError(f"refusing EXP-R1 with uncommitted evaluation code: {changes}")
    config = load_spec(args.config)
    sources = discover_sources(config)
    sha = git_info(Path.cwd()).sha
    root = args.results or Path("results") / f"_r1_final_{sha}"
    cells = []
    for seed in config["eval_seeds"]:
        episode_plan = {
            "split": "test",
            "seeds": attacker_episode_seeds(config["attacker_episode_starts"][seed]),
            "query_budget": 50,
        }
        sessions = defender_plans(
            config["defender_plan_seeds"][seed], config["defender_env_seed_starts"][seed]
        )
        for agent in config["attacker_refs"]:
            for mode in ("fast", "real"):
                cells.append(
                    _cell(
                        root,
                        sources[agent],
                        {"DEF-REF-1": sources["DEF-REF-1"]},
                        mode,
                        seed,
                        episode_plan,
                        sha,
                    )
                )
                print(f"EXP-R1 {agent} s{seed} {mode}", flush=True)
        for agent in config["defender_refs"]:
            opponents = {name: sources[name] for name in config["attacker_refs"]}
            for mode in ("fast", "real"):
                cells.append(_cell(root, sources[agent], opponents, mode, seed, sessions, sha))
                print(f"EXP-R1 {agent} s{seed} {mode}", flush=True)
    write_csv(args.summary_dir / "EXP-R1_cells.csv", [_compact(cell) for cell in cells])
    write_csv(args.summary_dir / "EXP-R1_gap.csv", aggregate_gaps(cells))
    print(f"EXP-R1 {sha}: wrote 24 cells and GAP summary")


if __name__ == "__main__":
    main()
