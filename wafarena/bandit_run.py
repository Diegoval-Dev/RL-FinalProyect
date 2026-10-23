"""Bandit experiment runner (catalogo.md EXP-A1/EXP-A2): pulls.csv, regret and a final evaluation.

Shares the config/meta machinery of `wafarena.run`, but a k-armed bandit has no held-out
generalization to select a checkpoint on `val` for: the deliverable is the policy the bandit
converges to over all its pulls, so training writes one row per pull instead of per episode and
the final evaluation deploys that end-of-run policy (`explore=False`) on the plain `Attacker-v0`
suites, as "ER final en attacker-eval-v1 usando la política del bandit" asks.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from wafarena import runmeta
from wafarena.agents.base import Transition, build_agent, save_checkpoint, strip_ground_truth
from wafarena.envs.attacker_env import N_ACTIONS
from wafarena.envs.attacker_obs import OBS_SIZE
from wafarena.envs.backends.base import Backend
from wafarena.envs.bandit_env import BanditEnv
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness
from wafarena.eval.arm_means import defender_label, load_arm_means, regret_curve
from wafarena.runconfig import ConfigError, load_config, resolve_config
from wafarena.runmeta import DirtyTreeError

PROJECT_ROOT = Path(__file__).parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results"
DEFAULT_ARM_MEANS_PATH = RESULTS_ROOT / "summary" / "bandit_arm_means.csv"
ENV_ID = "WafArena/AttackerBandit-v0"
BANDIT_ENV_KWARGS = ("split", "query_budget", "ban_threshold", "max_steps", "families")


def run_experiment(
    config: dict[str, Any],
    *,
    results_root: Path = RESULTS_ROOT,
    repo: Path = PROJECT_ROOT,
    allow_dirty: bool = False,
    overwrite: bool = False,
    backend: Backend | None = None,
    arm_means_path: Path = DEFAULT_ARM_MEANS_PATH,
) -> list[Path]:
    """Run every seed of `config`; returns the run directories.

    One backend is built and reused across every seed (and closed once at the end): a fresh one
    per seed reloads the disk-persisted ModSec cache from scratch each time, which on a
    memory-constrained host was enough extra pressure to OOM (found running EXP-A1).
    """
    config = resolve_config(config)
    if config["env"]["id"] != ENV_ID:
        raise NotImplementedError(f"wafarena.bandit_run only runs {ENV_ID} configs")
    runmeta.ensure_clean(repo, allow_dirty=allow_dirty)
    owns_backend = backend is None
    backend = backend or resolve_backend(config["env"]["backend"])
    try:
        return [
            run_seed(
                config,
                seed,
                results_root=results_root,
                repo=repo,
                allow_dirty=allow_dirty,
                overwrite=overwrite,
                backend=backend,
                arm_means_path=arm_means_path,
            )
            for seed in config["seeds"]
        ]
    finally:
        if owns_backend:
            backend.close()


def run_seed(
    config: dict[str, Any],
    seed: int,
    *,
    results_root: Path,
    repo: Path,
    allow_dirty: bool,
    overwrite: bool = False,
    backend: Backend | None = None,
    arm_means_path: Path = DEFAULT_ARM_MEANS_PATH,
) -> Path:
    directory = runmeta.run_dir(results_root, config["exp_id"], config["run_name"], seed)
    if (directory / runmeta.META_FILE).exists() and not overwrite:
        raise FileExistsError(f"{directory} already holds a run (use --overwrite to replace it)")
    meta = runmeta.build_meta(config, seed=seed, repo=repo, allow_dirty=allow_dirty)
    runmeta.write_meta(directory, meta)
    (directory / "config.resolved.yaml").write_text(yaml.safe_dump(config, sort_keys=False))

    owns_backend = backend is None
    backend = backend or resolve_backend(config["env"]["backend"])
    started = time.monotonic()
    try:
        env_cfg = config["env"]
        agent = build_agent(
            config["agent"]["algo"],
            config["agent"]["params"],
            obs_dim=OBS_SIZE,
            n_actions=N_ACTIONS,
            seed=seed,
            agent_id=meta["run_id"],
        )
        env = BanditEnv(
            backend=backend,
            defender=env_cfg["defender"],
            switch_at=env_cfg.get("switch_at"),
            switch_defender=env_cfg.get("switch_defender"),
            **{k: env_cfg[k] for k in BANDIT_ENV_KWARGS if k in env_cfg},
        )
        _train(agent, env, config["train"]["total_steps"], seed, directory, arm_means_path, env_cfg)
        _save_checkpoint(agent, config, meta, directory / "checkpoint")
        if config["eval"]["final"]:
            _final_eval(config, agent, backend, directory)
    finally:
        if owns_backend:  # called directly (not via run_experiment): this call owns the backend
            backend.close()
    runmeta.finalize_meta(directory, duration_s=round(time.monotonic() - started, 3))
    return directory


def _train(
    agent, env: BanditEnv, total_steps: int, seed: int, directory: Path, arm_means_path, env_cfg
) -> None:
    mu = _mu_schedule(env_cfg, total_steps, arm_means_path)
    rows = []
    obs, info = env.reset(seed=seed)
    for step in range(total_steps):
        arm = int(agent.act(obs, strip_ground_truth(info), explore=True))
        next_obs, reward, terminated, truncated, next_info = env.step(arm)
        clean_info = strip_ground_truth(next_info)
        metrics = agent.observe(
            Transition(obs, arm, reward, next_obs, terminated, truncated, clean_info)
        )
        rows.append(
            {
                "step": step + 1,
                "arm": arm,
                "reward": reward,
                **{f"m_{name}": value for name, value in metrics.items()},
            }
        )
        obs, info = (next_obs, next_info) if not (terminated or truncated) else env.reset()
    arms = [row["arm"] for row in rows]
    regret = regret_curve(arms, mu)
    instant = mu.max(axis=1) - mu[range(len(rows)), arms]
    for row, one_instant, cumulative in zip(rows, instant, regret, strict=True):
        row["regret_instant"], row["regret_cumulative"] = float(one_instant), float(cumulative)
    with (directory / "pulls.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _mu_schedule(env_cfg: dict, total_steps: int, arm_means_path: Path):
    """One μ row per pull: the stationary case broadcasts; a switch concatenates two blocks."""
    mu = load_arm_means(arm_means_path, defender_label(env_cfg["defender"]))
    switch_at = env_cfg.get("switch_at")
    if switch_at is None:
        return np.tile(mu, (total_steps, 1))
    mu_after = load_arm_means(arm_means_path, defender_label(env_cfg["switch_defender"]))
    before = np.tile(mu, (switch_at, 1))
    after = np.tile(mu_after, (total_steps - switch_at, 1))
    return np.vstack([before, after])


def _save_checkpoint(agent, config, meta, path: Path) -> None:
    save_checkpoint(
        agent,
        path,
        algo=config["agent"]["algo"],
        obs_dim=OBS_SIZE,
        n_actions=N_ACTIONS,
        train={
            "exp_id": meta["exp_id"],
            "run_id": meta["run_id"],
            "seed": meta["seed"],
            "git_sha": meta["git_sha"],
            "agent_params": config["agent"]["params"],
        },
    )


def _final_eval(config, agent, backend, directory: Path) -> None:
    """Deploy the bandit's end-of-run (greedy) policy on the reportable suites."""
    env_cfg = config["env"]
    defender = env_cfg.get("switch_defender", env_cfg["defender"])
    suites = {}
    for name in config["eval"]["suites"]:
        results = harness.run_attacker_suite(agent, name, defender=defender, backend=backend)
        suites[name] = harness.summarize_attacker(results, query_budget=env_cfg["query_budget"])
    (directory / "final_eval.json").write_text(
        json.dumps({"suites": suites}, indent=2, sort_keys=True) + "\n"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run a bandit experiment config (EXP-A1/EXP-A2)")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--arm-means", type=Path, default=DEFAULT_ARM_MEANS_PATH)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="run with uncommitted changes; marked in meta.yaml and not valid for the report",
    )
    parser.add_argument("--overwrite", action="store_true", help="replace existing runs")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="run only this one seed instead of every config seed",
    )
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.seed is not None:
            if args.seed not in config["seeds"]:
                parser.exit(2, f"error: seed {args.seed} is not in config.seeds\n")
            config["seeds"] = [args.seed]
        directories = run_experiment(
            config,
            results_root=args.results,
            allow_dirty=args.allow_dirty,
            overwrite=args.overwrite,
            arm_means_path=args.arm_means,
        )
    except (ConfigError, DirtyTreeError, FileExistsError) as error:
        parser.exit(2, f"error: {error}\n")
    for directory in directories:
        print(f"finished {directory}")


if __name__ == "__main__":
    sys.exit(main())
