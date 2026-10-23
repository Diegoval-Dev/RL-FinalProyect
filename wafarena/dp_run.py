"""EXP-B1 runner (catalogo.md): estimate the abstract MDP, solve it, evaluate the greedy policy.

Shares the config/meta machinery of `wafarena.run`, but there is no online training loop here:
collect `train.total_steps` transitions with a random policy, estimate `(P, R)`, solve with value
iteration and policy iteration, and deploy the value-iteration policy (the hypothesis is that both
agree; `model_summary.json` records whether they actually did).
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from wafarena import runmeta
from wafarena.agents.base import build_agent, save_checkpoint
from wafarena.agents.dp import estimate_model, policy_iteration, value_iteration
from wafarena.envs.abstract_state import N_STATES
from wafarena.envs.attacker_env import N_ACTIONS, AttackerEnv
from wafarena.envs.attacker_obs import OBS_SIZE
from wafarena.envs.backends.base import Backend
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness
from wafarena.runconfig import ConfigError, load_config, resolve_config
from wafarena.runmeta import DirtyTreeError

PROJECT_ROOT = Path(__file__).parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results"
ENV_ID = "WafArena/Attacker-v0"
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
    """Run every seed of `config`; returns the run directories."""
    config = resolve_config(config)
    if config["agent"]["algo"] != "dp":
        raise NotImplementedError("wafarena.dp_run only runs agent.algo: dp configs")
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
        env_cfg = config["env"]
        env = AttackerEnv(backend=backend, **{k: env_cfg[k] for k in ENV_KWARGS if k in env_cfg})
        transitions = collect_transitions(env, config["train"]["total_steps"], seed)
        agent = _solve(config, transitions, meta, directory)
        if config["eval"]["final"]:
            _final_eval(config, agent, backend, directory)
    finally:
        if owns_backend:
            backend.close()
    runmeta.finalize_meta(directory, duration_s=round(time.monotonic() - started, 3))
    return directory


def collect_transitions(env: AttackerEnv, n_transitions: int, seed: int) -> list[tuple]:
    """`n_transitions` abstract-state transitions `(s, a, r, s', done)` from a uniform random
    policy (the policy EXP-B1's model needs on-policy data from, per the task)."""
    rng = np.random.default_rng(seed)
    transitions = []
    _obs, info = env.reset(seed=seed)
    state = info["abstract_state"]
    for _ in range(n_transitions):
        action = int(rng.integers(N_ACTIONS))
        _obs, reward, terminated, truncated, info = env.step(action)
        next_state = info["abstract_state"]
        transitions.append((state, action, reward, next_state, terminated))
        if terminated or truncated:
            _obs, info = env.reset()
            state = info["abstract_state"]
        else:
            state = next_state
    return transitions


def _solve(config, transitions, meta, directory: Path):
    params = config["agent"]["params"]
    gamma, theta = params["gamma"], params["theta"]
    P, R = estimate_model(transitions, n_states=N_STATES, n_actions=N_ACTIONS)

    vi_started = time.monotonic()
    v_star, vi_policy, vi_iterations = value_iteration(P, R, gamma=gamma, theta=theta)
    vi_seconds = time.monotonic() - vi_started

    pi_started = time.monotonic()
    p_star, pi_policy, pi_iterations = policy_iteration(P, R, gamma=gamma, theta=theta)
    pi_seconds = time.monotonic() - pi_started

    summary = {
        "n_transitions": len(transitions),
        "value_iteration": {"iterations": vi_iterations, "seconds": round(vi_seconds, 4)},
        "policy_iteration": {"iterations": pi_iterations, "seconds": round(pi_seconds, 4)},
        "policies_agree": bool(np.array_equal(vi_policy, pi_policy)),
        "max_value_diff": float(np.max(np.abs(v_star - p_star))),
    }
    (directory / "model_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )

    agent = build_agent(
        "dp", params, obs_dim=OBS_SIZE, n_actions=N_ACTIONS, seed=0, agent_id=meta["run_id"]
    )
    agent.policy = vi_policy  # deploy value iteration's policy (the hypothesis: pi agrees)
    save_checkpoint(
        agent,
        directory / "checkpoint",
        algo="dp",
        obs_dim=OBS_SIZE,
        n_actions=N_ACTIONS,
        train={
            "exp_id": meta["exp_id"],
            "run_id": meta["run_id"],
            "seed": meta["seed"],
            "git_sha": meta["git_sha"],
        },
    )
    return agent


def _final_eval(config, agent, backend, directory: Path) -> None:
    env_cfg = config["env"]
    suites = {}
    for name in config["eval"]["suites"]:
        results = harness.run_attacker_suite(
            agent, name, defender=env_cfg["defender"], backend=backend
        )
        suites[name] = harness.summarize_attacker(results, query_budget=env_cfg["query_budget"])
    (directory / "final_eval.json").write_text(
        json.dumps({"suites": suites}, indent=2, sort_keys=True) + "\n"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run an EXP-B1 config (MDP model + DP)")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="run with uncommitted changes; marked in meta.yaml and not valid for the report",
    )
    parser.add_argument("--overwrite", action="store_true", help="replace existing runs")
    parser.add_argument(
        "--seed", type=int, default=None, help="run only this one seed instead of every config seed"
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
