"""Evaluate the final self-play defender on EXP-I3, EXP-I4 and EXP-I5."""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import yaml

from wafarena.agents import load_checkpoint
from wafarena.agents.base import check_contract_versions
from wafarena.attackers.driver import AttackerDriver
from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs.attacker_env import _load_bases
from wafarena.envs.defender_env import DefenderEnv
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness
from wafarena.eval.final_generalization import (
    aggregate_generalization,
    cached_cell,
    file_sha256,
    i5_plan,
    rank_dyna,
    select_pool_champion,
)
from wafarena.mutations.payload import Payload
from wafarena.runmeta import (
    DirtyTreeError,
    build_meta,
    git_info,
    run_id,
    uncommitted_changes,
    write_meta,
)
from wafarena.selfplay.report import write_csv

SPEC = Path("configs/selfplay/exp_i345.yaml")
MODSEC_BASELINES = Path("results/summary/modsec_defender_suites.csv")


def load_spec(path: Path) -> dict:
    """Load the frozen F4-T08 evaluation design."""
    config = yaml.safe_load(Path(path).read_text())
    expected = {
        "source_exp_id": "EXP-I1",
        "source_condition": "pool",
        "source_git_sha": "eea6f78",
        "source_seeds": [0, 1, 2],
        "source_generation": 8,
        "history_csv": "results/summary/EXP-I1_history.csv",
        "checkpoint_root": "checkpoints/selfplay",
        "fpr_cap": 0.0,
        "ppo_config": "configs/exp/EXP-I5/ppo-unseen-defref1.yaml",
        "ppo_seed": 5,
        "ppo_results_root": "results/_i5_ppo_final",
        "dyna_results_root": "results/_h1_final_9d54cd2",
        "dyna_method": "dyna-5-defref1",
        "dyna_seed": 0,
        "reference_checkpoint": "checkpoints/refs/DEF-REF-1",
        "modsec_level": 2,
        "backend": "fast",
        "i3_suite": "defender-eval-family-v1",
        "i4_suite": "defender-eval-hard-v1",
        "i5_sessions": 2000,
        "i5_attack_ratio": 0.1,
    }
    if not isinstance(config, dict) or set(config) != set(expected):
        raise ValueError("invalid F4-T08 configuration fields")
    for key, value in expected.items():
        if config[key] != value or type(config[key]) is not type(value):
            raise ValueError(f"F4-T08 {key} must be {value!r}")
    return config


def load_modsec_baseline(path: Path, suite: str) -> dict:
    """Read PL2's previously registered result on the same fixed suite."""
    with Path(path).open(newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["defender"] == "modsec-pl2" and row["suite"] == suite
        ]
    if len(rows) != 1:
        raise ValueError(f"expected one modsec-pl2 baseline for {suite}")
    values = {name: float(rows[0][name]) for name in ("tpr", "fpr", "er_d")}
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values.values()):
        raise ValueError(f"invalid modsec-pl2 baseline for {suite}")
    return {
        "exp_id": "EXP-I3" if suite == "defender-eval-family-v1" else "EXP-I4",
        "defender": "modsec-pl2",
        "seed": None,
        "attacker": "suite-default",
        "suite": suite,
        "split": harness.DEFENDER_SUITES[suite].benign_split,
        "attack_split": harness.DEFENDER_SUITES[suite].attack_split,
        "sessions": 2000 * len(harness.DEFENDER_SUITES[suite].attackers),
        "requests": int(rows[0]["requests"]),
        "attack_requests": int(rows[0]["attack_requests"]),
        "eval_run_id": "modsec-defender-suites__d9d7d49",
        "source_run_id": "modsec-defender-suites__d9d7d49",
        "source_git_sha": "d9d7d49",
        **values,
    }


def discover_pool_defenders(root: Path, source_sha: str) -> list[dict]:
    """Validate the three final EXP-I1 pool defender checkpoints."""
    sources = []
    for seed in range(3):
        run_id = f"EXP-I1__pool__s{seed}__{source_sha}"
        checkpoint = Path(root) / run_id / "def-gen-08"
        meta_path = checkpoint / "meta.yaml"
        weights = checkpoint / "dqn.pt"
        if not meta_path.is_file() or not weights.is_file():
            raise ValueError(f"missing final pool checkpoint: {checkpoint}")
        meta = yaml.safe_load(meta_path.read_text())
        train = meta.get("train", {})
        if meta.get("role") != "defender" or any(
            train.get(key) != value
            for key, value in {
                "exp_id": "EXP-I1",
                "run_id": run_id,
                "seed": seed,
                "git_sha": source_sha,
                "generation": 8,
            }.items()
        ):
            raise ValueError(f"final pool checkpoint provenance mismatch: {checkpoint}")
        if "contract_versions" in meta:
            check_contract_versions(meta["contract_versions"])
        sources.append(
            {
                "defender": "selfplay",
                "seed": seed,
                "path": checkpoint,
                "source_run_id": run_id,
                "source_git_sha": source_sha,
                "defender_sha256": file_sha256(weights),
            }
        )
    return sources


def _checkpoint(path: Path, role: str) -> dict:
    """Read one checkpoint's training identity and weight fingerprint."""
    path = Path(path)
    weights = {"defender": "dqn.pt", "ppo": "pg.pt", "dyna": "td.npz"}[role]
    if not (path / "meta.yaml").is_file() or not (path / weights).is_file():
        raise ValueError(f"missing {role} checkpoint: {path}")
    meta = yaml.safe_load((path / "meta.yaml").read_text())
    expected_role = "attacker" if role in ("ppo", "dyna") else "defender"
    train = meta.get("train", {})
    if (
        meta.get("role") != expected_role
        or not isinstance(train.get("run_id"), str)
        or not isinstance(train.get("git_sha"), str)
        or type(train.get("seed")) is not int
    ):
        raise ValueError(f"checkpoint provenance mismatch: {path}")
    check_contract_versions(meta["contract_versions"])
    return {
        "path": path,
        "source_run_id": train["run_id"],
        "source_git_sha": train["git_sha"],
        "weight_sha256": file_sha256(path / weights),
        "meta": meta,
    }


def discover_attackers(config: dict) -> list[dict]:
    """Find the clean new PPO and preselected lowest-cost H1 Dyna tie."""
    ppo_run = (
        Path(config["ppo_results_root"])
        / "EXP-I5"
        / "ppo-unseen-defref1"
        / f"s{config['ppo_seed']}"
    )
    ppo_run_meta = yaml.safe_load((ppo_run / "meta.yaml").read_text())
    ppo = _checkpoint(ppo_run / "checkpoint", "ppo")
    ppo_train = ppo["meta"]["train"]
    if (
        ppo_run_meta.get("dirty")
        or "duration_s" not in ppo_run_meta
        or ppo_run_meta.get("run_id") != ppo["source_run_id"]
        or ppo_run_meta.get("git_sha") != ppo["source_git_sha"]
        or ppo_train.get("seed") != config["ppo_seed"]
        or ppo_train.get("exp_id") != "EXP-I5"
        or ppo["meta"].get("algo") != "pg"
        or ppo_train.get("agent_params", {}).get("method") != "ppo"
    ):
        raise ValueError("new PPO checkpoint provenance mismatch")
    with (ppo_run / "eval.csv").open(newline="") as handle:
        evaluations = list(csv.DictReader(handle))
    if not evaluations or int(evaluations[-1]["step"]) != 200_000:
        raise ValueError("new PPO training run is incomplete")
    ppo.update(attacker="ppo-unseen-defref1", seed=config["ppo_seed"])

    candidates = []
    h1_root = Path(config["dyna_results_root"]) / "EXP-H1"
    for planning_steps in (5, 20, 50):
        method = f"dyna-{planning_steps}"
        for seed in range(10):
            run = h1_root / f"{method}-defref1" / f"s{seed}"
            source = _checkpoint(run / "checkpoint", "dyna")
            train = source["meta"]["train"]
            summary = source["meta"].get("eval_summary", {})
            run_meta = yaml.safe_load((run / "meta.yaml").read_text())
            if (
                run_meta.get("dirty")
                or "duration_s" not in run_meta
                or run_meta.get("run_id") != source["source_run_id"]
                or train.get("exp_id") != "EXP-H1"
                or train.get("seed") != seed
                or train.get("agent_params", {}).get("planning_steps") != planning_steps
                or summary.get("suite") != "attacker-val-v1"
                or summary.get("defender") != "DEF-REF-1"
            ):
                raise ValueError(f"H1 Dyna checkpoint provenance mismatch: {run}")
            candidates.append(
                {
                    **source,
                    "method": method,
                    "seed": seed,
                    "planning_steps": planning_steps,
                    "val_er": float(summary["evasion_rate"]),
                }
            )
    dyna = rank_dyna(candidates)[0]
    if f"{dyna['method']}-defref1" != config["dyna_method"] or dyna["seed"] != config["dyna_seed"]:
        raise ValueError("configured Dyna checkpoint differs from val-only ranking")
    dyna["attacker"] = "dyna-5-defref1"
    return [ppo, dyna]


def _run_directory(root: Path, exp_id: str, run_name: str, seed: int) -> Path:
    return root / exp_id / run_name / f"s{seed}"


def _prepare_run(directory: Path, exp_id: str, run_name: str, seed: int, sha: str, source: dict):
    meta_path = directory / "meta.yaml"
    expected_id = run_id(exp_id, run_name, seed, sha)
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text())
        if (
            meta.get("run_id") != expected_id
            or meta.get("git_sha") != sha
            or meta.get("source_run_id") != source["source_run_id"]
            or meta.get("source_git_sha") != source["source_git_sha"]
            or meta.get("dirty")
        ):
            raise ValueError(f"stale evaluation run metadata: {directory}")
    else:
        meta = build_meta(
            {"exp_id": exp_id, "run_name": run_name},
            seed=seed,
            repo=Path.cwd(),
            allow_dirty=False,
        )
        meta["source_run_id"] = source["source_run_id"]
        meta["source_git_sha"] = source["source_git_sha"]
        if meta["dirty"]:
            raise DirtyTreeError("refusing final evaluation with an uncommitted tree")
        write_meta(directory, meta)
    return expected_id


def i5_emitting_plan(attacker: dict, plan) -> tuple[list, int]:
    """Keep the fixed attack sessions where the checkpoint actually sends a request."""
    bases = {base.base_id: base for base in _load_bases("test")}
    driver = AttackerDriver(load_checkpoint(attacker["path"]))
    emitting = []
    empty = 0
    for item in plan:
        if not item.is_attack:
            emitting.append(item)
            continue
        base = bases[item.ref]
        driver.reset(
            Payload(base.text, base.location, 0), base.endpoint, np.random.default_rng(item.seed)
        )
        if driver.next_request(0) is None:
            empty += 1
        else:
            emitting.append(item)
    return emitting, empty


def _evaluate_i5(defender, attacker: dict, backend, plan, emitting_plan, empty: int) -> dict:
    env = DefenderEnv(
        backend=backend,
        attacker={"type": "checkpoint", "path": str(attacker["path"])},
        split="test",
        attack_split="test",
    )
    records = [
        record for item in emitting_plan for record in harness._play_session(defender, env, item)
    ]
    return {
        **harness.summarize_defender(records),
        "sessions": len(plan),
        "attack_sessions": sum(item.is_attack for item in plan),
        "evaluated_sessions": len(emitting_plan),
        "emitting_attack_sessions": sum(item.is_attack for item in emitting_plan),
        "empty_attack_sessions": empty,
        "empty_attack_attempts": env.empty_attack_attempts,
    }


def _compact(row: dict) -> dict:
    keys = (
        "exp_id",
        "defender",
        "seed",
        "attacker",
        "suite",
        "split",
        "attack_split",
        "sessions",
        "attack_sessions",
        "evaluated_sessions",
        "emitting_attack_sessions",
        "empty_attack_sessions",
        "requests",
        "attack_requests",
        "empty_attack_attempts",
        "tpr",
        "fpr",
        "er_d",
        "eval_run_id",
        "eval_git_sha",
        "source_run_id",
        "source_git_sha",
        "defender_sha256",
        "attacker_run_id",
        "attacker_git_sha",
        "attacker_sha256",
    )
    return {key: row.get(key) for key in keys}


def _evaluate_cell(
    root: Path,
    exp_id: str,
    suite: str,
    defender: dict,
    attacker: dict | None,
    backend,
    plan,
    eval_sha: str,
    emitting_plan=None,
    empty_attack_sessions: int = 0,
) -> dict:
    name = defender["defender"]
    attacker_name = attacker["attacker"] if attacker else "suite-default"
    run_name = name if attacker is None else f"{name}-{attacker_name}"
    eval_seed = defender["seed"] if defender["seed"] is not None else 0
    directory = _run_directory(root, exp_id, run_name, eval_seed)
    eval_run_id = _prepare_run(directory, exp_id, run_name, eval_seed, eval_sha, defender)
    sessions = 2000 * len(harness.DEFENDER_SUITES[suite].attackers) if attacker is None else 2000
    suite_spec = harness.DEFENDER_SUITES.get(suite)
    expected = {
        "exp_id": exp_id,
        "defender": name,
        "seed": defender["seed"],
        "attacker": attacker_name,
        "suite": suite,
        "split": suite_spec.benign_split if suite_spec else "test",
        "attack_split": suite_spec.attack_split if suite_spec else "test",
        "backend": "fast",
        "sessions": sessions,
        "eval_run_id": eval_run_id,
        "eval_git_sha": eval_sha,
        "source_run_id": defender["source_run_id"],
        "source_git_sha": defender["source_git_sha"],
        "defender_sha256": defender.get("defender_sha256"),
        "attacker_run_id": attacker["source_run_id"] if attacker else None,
        "attacker_git_sha": attacker["source_git_sha"] if attacker else None,
        "attacker_sha256": attacker["weight_sha256"] if attacker else None,
    }
    if attacker is not None:
        if emitting_plan is None:
            raise ValueError("EXP-I5 needs its fixed emitting session plan")
        expected.update(
            evaluated_sessions=len(emitting_plan),
            attack_sessions=sum(item.is_attack for item in plan),
            emitting_attack_sessions=sum(item.is_attack for item in emitting_plan),
            empty_attack_sessions=empty_attack_sessions,
        )

    def compute():
        policy = ModSecDefender(2) if name == "modsec-pl2" else load_checkpoint(defender["path"])
        if attacker is None:
            return {
                **harness.evaluate_defender(policy, suite, backend=backend),
                "sessions": sessions,
            }
        return _evaluate_i5(policy, attacker, backend, plan, emitting_plan, empty_attack_sessions)

    return cached_cell(directory / "cell.json", expected, compute)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=SPEC)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--summary-dir", type=Path, default=Path("results/summary"))
    args = parser.parse_args()
    changes = uncommitted_changes(Path.cwd(), ("wafarena", "configs", "scripts", "Makefile"))
    if changes:
        raise DirtyTreeError(f"refusing F4-T08 with uncommitted evaluation code: {changes}")
    config = load_spec(args.config)
    eval_sha = git_info(Path.cwd()).sha
    root = args.results or Path("results") / f"_i345_final_{eval_sha}"
    with Path(config["history_csv"]).open(newline="") as handle:
        history = list(csv.DictReader(handle))
    selection = select_pool_champion(
        history, source_sha=config["source_git_sha"], fpr_cap=config["fpr_cap"]
    )
    defenders = discover_pool_defenders(config["checkpoint_root"], config["source_git_sha"])
    reference = _checkpoint(config["reference_checkpoint"], "defender")
    defenders.append(
        {
            **reference,
            "defender": "DEF-REF-1",
            "seed": None,
            "defender_sha256": reference["weight_sha256"],
        }
    )
    modsec = {
        "defender": "modsec-pl2",
        "seed": None,
        "source_run_id": "modsec-defender-suites__d9d7d49",
        "source_git_sha": "d9d7d49",
    }
    attackers = discover_attackers(config)
    plan = i5_plan()
    if len(plan) != 2000 or sum(item.is_attack for item in plan) != 200:
        raise ValueError("EXP-I5 requires 2000 sessions with 200 attacks")
    backend = resolve_backend(config["backend"])
    cells_by_exp = {}
    table = []
    try:
        for exp_id, suite in (("EXP-I3", config["i3_suite"]), ("EXP-I4", config["i4_suite"])):
            cells = []
            for defender in defenders:
                cells.append(
                    _evaluate_cell(root, exp_id, suite, defender, None, backend, plan, eval_sha)
                )
                print(f"{exp_id}: {defender['defender']} s{defender['seed']}", flush=True)
            cells.append(load_modsec_baseline(MODSEC_BASELINES, suite))
            cells_by_exp[exp_id] = cells
            table.extend(
                aggregate_generalization(
                    cells, exp_id=exp_id, champion_seed=selection["winner_seed"]
                )
            )
        cells = []
        for attacker in attackers:
            group = []
            emitting_plan, empty_attack_sessions = i5_emitting_plan(attacker, plan)
            for defender in [*defenders, modsec]:
                row = _evaluate_cell(
                    root,
                    "EXP-I5",
                    "unseen-attacker-test-v1",
                    defender,
                    attacker,
                    backend,
                    plan,
                    eval_sha,
                    emitting_plan,
                    empty_attack_sessions,
                )
                group.append(row)
                print(
                    f"EXP-I5: {defender['defender']} s{defender['seed']} vs {attacker['attacker']}",
                    flush=True,
                )
            cells.extend(group)
            table.extend(
                aggregate_generalization(
                    group,
                    exp_id="EXP-I5",
                    champion_seed=selection["winner_seed"],
                    attacker_id=attacker["attacker"],
                )
            )
        cells_by_exp["EXP-I5"] = cells
    finally:
        backend.close()
    for exp_id, cells in cells_by_exp.items():
        write_csv(args.summary_dir / f"{exp_id}.csv", [_compact(row) for row in cells])
    write_csv(args.summary_dir / "RQ5_final.csv", table)
    (args.summary_dir / "EXP-I3_selection.json").write_text(
        json.dumps(selection, indent=2, allow_nan=False) + "\n"
    )
    print(f"F4-T08 {eval_sha}: wrote EXP-I3, I4, I5 and RQ5_final summaries")


if __name__ == "__main__":
    main()
