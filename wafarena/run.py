"""Experiment runner: train, select on `val`, evaluate the best checkpoint (experimentos.md)."""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from wafarena import runmeta
from wafarena.agents.base import Agent, build_agent, load_checkpoint, save_checkpoint
from wafarena.envs.attacker_env import N_ACTIONS, AttackerEnv
from wafarena.envs.attacker_obs import OBS_SIZE
from wafarena.envs.backends.base import Backend
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness
from wafarena.runconfig import ConfigError, load_config, resolve_config
from wafarena.runmeta import DirtyTreeError
from wafarena.trainer import train

PROJECT_ROOT = Path(__file__).parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results"
VALIDATION_SUITE = "attacker-val-v1"
ENV_KWARGS = ("defender", "split", "query_budget", "ban_threshold", "max_steps", "families")


def run_experiment(
    config: dict[str, Any],
    *,
    results_root: Path = RESULTS_ROOT,
    repo: Path = PROJECT_ROOT,
    allow_dirty: bool = False,
    overwrite: bool = False,
    backend: Backend | None = None,
) -> list[Path]:
    """Run every seed of `config`; returns the run directories.

    Validates the config and the git state before anything is written. `backend` overrides the
    one named in the config (used by tests). One backend is built and reused across every seed
    (and closed once at the end): a fresh one per seed reloads the disk-persisted ModSec cache
    from scratch each time, enough extra memory pressure to OOM on a constrained host (F2-T05).
    """
    config = resolve_config(config)
    if config["env"]["id"] != "WafArena/Attacker-v0":
        raise NotImplementedError("Defender-v0 runs arrive with Phase 3")
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
        agent = build_agent(
            config["agent"]["algo"],
            config["agent"]["params"],
            obs_dim=OBS_SIZE,
            n_actions=N_ACTIONS,
            seed=seed,
            agent_id=meta["run_id"],
        )
        selection = _train_and_select(config, agent, seed, directory, backend, meta)
        if config["eval"]["final"]:
            _final_eval(config, directory, backend, selection)
    finally:
        if owns_backend:  # called directly (not via run_experiment): this call owns the backend
            backend.close()
    runmeta.finalize_meta(directory, duration_s=round(time.monotonic() - started, 3))
    return directory


def _train_and_select(config, agent: Agent, seed, directory: Path, backend, meta) -> dict:
    env_cfg = config["env"]
    env = AttackerEnv(backend=backend, **{k: env_cfg[k] for k in ENV_KWARGS if k in env_cfg})
    selection: dict[str, Any] = {"best_step": None, "best_key": None}
    eval_rows: list[dict] = []

    def on_eval(step: int) -> None:
        results = harness.run_attacker_suite(
            agent, VALIDATION_SUITE, defender=env_cfg["defender"], backend=backend
        )
        summary = harness.summarize_attacker(results, query_budget=env_cfg["query_budget"])
        eval_rows.append({"step": step, "suite": VALIDATION_SUITE, **summary})
        key = (summary["evasion_rate"], -summary["qfe_c"])
        if selection["best_key"] is None or key > selection["best_key"]:
            selection.update(best_step=step, best_key=key, best_val=summary)
            _save_best(config, agent, directory / "checkpoint", meta, step, summary)

    try:
        train(
            agent,
            env,
            total_steps=config["train"]["total_steps"],
            seed=seed,
            out_dir=directory,
            eval_every=config["eval"]["every_steps"],
            on_eval=on_eval,
            tensorboard=config["logging"]["tensorboard"],
        )
    finally:
        _write_eval_csv(directory / "eval.csv", eval_rows)
    return selection


def _save_best(config, agent: Agent, path: Path, meta, step: int, summary: dict) -> None:
    defender = config["env"]["defender"]
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
            "step": step,
        },
        eval_summary={
            "suite": VALIDATION_SUITE,
            "defender": f"{defender['type']}-pl{defender.get('paranoia_level', '')}",
            "evasion_rate": summary["evasion_rate"],
        },
    )


def _write_eval_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _final_eval(config, directory: Path, backend, selection: dict) -> None:
    """Evaluate the best-on-val checkpoint (reloaded from disk) on the reportable suites."""
    best = load_checkpoint(directory / "checkpoint")
    env_cfg = config["env"]
    suites = {}
    for name in config["eval"]["suites"]:
        results = harness.run_attacker_suite(
            best, name, defender=env_cfg["defender"], backend=backend
        )
        suites[name] = harness.summarize_attacker(results, query_budget=env_cfg["query_budget"])
    payload = {
        "best_step": selection["best_step"],
        "val": selection["best_val"],
        "suites": suites,
    }
    (directory / "final_eval.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run an experiment config (one run per seed)")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
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
        )
    except (ConfigError, DirtyTreeError, FileExistsError) as error:
        parser.exit(2, f"error: {error}\n")
    for directory in directories:
        print(f"finished {directory}")


if __name__ == "__main__":
    sys.exit(main())
