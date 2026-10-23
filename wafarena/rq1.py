"""RQ1 vulnerability table (catalogo.md, F2-T09): ER, QFE and DIV per method and paranoia level.

For each method, evaluates one checkpoint per seed (already trained by an earlier task) against
every paranoia level with `attacker-eval-v1`, and reports the mean and 95 % bootstrap CI over
seeds. `random-mutation` and `corpus-replay` are not learned, so a fresh `ScriptedAgent` stands
in for "the checkpoint" of each seed, reproducing their exact F1 reference policy.
"""

import argparse
import csv
from pathlib import Path
from typing import Any

import numpy as np

from wafarena.agents.base import load_checkpoint
from wafarena.agents.scripted import ScriptedAgent
from wafarena.envs.attacker_env import N_ACTIONS
from wafarena.envs.attacker_obs import OBS_SIZE
from wafarena.envs.backends.base import Backend
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness
from wafarena.eval.stats import bootstrap_ci

PROJECT_ROOT = Path(__file__).parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results"
SUMMARY_DIR = RESULTS_ROOT / "summary"
SUITE = "attacker-eval-v1"
DEFAULT_PLS = (1, 2, 3, 4)
DEFAULT_N_SEEDS = 10
METRICS = ("evasion_rate", "qfe", "diversity")

# One representative checkpoint per method studied in F2-T05..F2-T08. All of them tie at
# ER = 0 in val (nothing evades with the current 16 operators), so "best" is not a meaningful
# ranking; each pick is simply that method's most standard or simplest configuration, not a
# result of comparing them. See the phase's Hallazgos for the ties this reflects.
DEFAULT_METHODS: dict[str, dict[str, Any]] = {
    "bandit-greedy": {"kind": "checkpoint", "exp_id": "EXP-A1", "run_name": "greedy-pl1"},
    "dp": {"kind": "checkpoint", "exp_id": "EXP-B1", "run_name": "value-policy-iteration-pl1"},
    "monte-carlo": {"kind": "checkpoint", "exp_id": "EXP-C1", "run_name": "first-visit-eps-01"},
    "sarsa": {"kind": "checkpoint", "exp_id": "EXP-D1", "run_name": "sarsa-pl1"},
    "qlearning": {"kind": "checkpoint", "exp_id": "EXP-D1", "run_name": "qlearning-pl1"},
    "sarsa-lambda": {"kind": "checkpoint", "exp_id": "EXP-D2", "run_name": "sarsa-lambda-09"},
    "corpus-replay": {"kind": "scripted", "variant": "corpus_replay"},
    "random-mutation": {"kind": "scripted", "variant": "random_mutation"},
}


def _agent_for_seed(spec: dict[str, Any], seed: int, results_root: Path):
    if spec["kind"] == "checkpoint":
        path = Path(results_root) / spec["exp_id"] / spec["run_name"] / f"s{seed}" / "checkpoint"
        return load_checkpoint(path)
    if spec["kind"] == "scripted":
        return ScriptedAgent.from_config(
            params={"variant": spec["variant"]},
            obs_dim=OBS_SIZE,
            n_actions=N_ACTIONS,
            seed=seed,
            agent_id=f"{spec['variant']}-s{seed}",
        )
    raise ValueError(f"unknown method kind {spec['kind']!r}")


def _interval(values: list[float]) -> tuple[str, str, str]:
    finite = [v for v in values if not np.isnan(v)]
    if not finite:
        return "", "", ""
    ci = bootstrap_ci(finite)
    return f"{ci.mean:.6f}", f"{ci.low:.6f}", f"{ci.high:.6f}"


def build_rq1_table(
    methods: dict[str, dict[str, Any]],
    *,
    results_root: Path,
    backend: Backend,
    pls: tuple[int, ...] = DEFAULT_PLS,
    n_seeds: int = DEFAULT_N_SEEDS,
) -> list[dict]:
    """One row per (method, pl): mean and 95 % bootstrap CI of ER, QFE and DIV over `n_seeds`."""
    rows = []
    for name, spec in methods.items():
        agents = [_agent_for_seed(spec, seed, results_root) for seed in range(n_seeds)]
        for pl in pls:
            defender = {"type": "modsec", "paranoia_level": pl}
            per_seed = [
                harness.summarize_attacker(
                    harness.run_attacker_suite(agent, SUITE, defender=defender, backend=backend),
                    query_budget=50,
                )
                for agent in agents
            ]
            row = {"method": name, "pl": pl, "n_seeds": n_seeds}
            for metric in METRICS:
                mean, low, high = _interval([s[metric] for s in per_seed])
                row.update({f"{metric}_mean": mean, f"{metric}_low": low, f"{metric}_high": high})
            rows.append(row)
    return rows


def write_rq1_table(
    methods: dict[str, dict[str, Any]],
    *,
    results_root: Path,
    out_path: Path,
    backend: Backend,
    pls: tuple[int, ...] = DEFAULT_PLS,
    n_seeds: int = DEFAULT_N_SEEDS,
) -> Path:
    rows = build_rq1_table(
        methods, results_root=results_root, backend=backend, pls=pls, n_seeds=n_seeds
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["method", "pl", "n_seeds"]
    for metric in METRICS:
        columns += [f"{metric}_mean", f"{metric}_low", f"{metric}_high"]
    with out_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the RQ1 vulnerability table")
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=SUMMARY_DIR / "RQ1_table.csv")
    parser.add_argument("--backend", default="fast")
    args = parser.parse_args(argv)
    backend = resolve_backend(args.backend)
    try:
        out = write_rq1_table(
            DEFAULT_METHODS, results_root=args.results, out_path=args.out, backend=backend
        )
    finally:
        backend.close()
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
