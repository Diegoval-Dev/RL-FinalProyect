"""Evaluation-only experiments: re-evaluate already trained checkpoints on other suites (EXP-F6,
EXP-F7, and the G experiments' evaluation against DEF-REF-1), without retraining.

The experiment is a YAML in configs/ like any other (experimentos.md), with an `evaluate`
section instead of `env`/`agent`/`train`:

    exp_id: EXP-F6
    run_name: alpha-4
    owner: joaquin
    rq: [RQ5]
    seeds: [0, 1, 2, 3, 4]
    evaluate:
      checkpoints: {exp_id: EXP-F5, run_name: alpha-4}   # results/EXP-F5/alpha-4/s<seed>/checkpoint
      suites: [defender-eval-family-v1]
      defender: {type: checkpoint, path: DEF-REF-1}      # attacker checkpoints only (optional)

Each seed writes results/<exp_id>/<run_name>/s<seed>/ with `meta.yaml` (git state of the
evaluation plus `source_run_id`, the run that trained the checkpoint), `config.resolved.yaml` and
`final_eval.json` (`{source_run_id, suites: {<suite>: metrics}}`), so `make summarize` works on
evaluation-only experiments exactly as on trained ones. Like the runner, it refuses a dirty tree.

Usage: python -m wafarena.evaluate --config configs/exp/EXP-F6/alpha-4.yaml [--results DIR]
       (make evaluate CONFIG=...; runs inside the lab runner like make run)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from wafarena import runmeta
from wafarena.agents import load_checkpoint
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness
from wafarena.runconfig import RUN_NAME_PATTERN, ConfigError, catalog_ids

PROJECT_ROOT = Path(__file__).parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results"
TOP_LEVEL_KEYS = {"exp_id", "run_name", "owner", "rq", "seeds", "evaluate"}
EVALUATE_KEYS = {"checkpoints", "suites", "defender"}
DEFENDER_SUITES = set(harness.DEFENDER_SUITES)
ATTACKER_SUITES = set(harness.ATTACKER_SUITES)


def resolve_eval_config(raw: dict[str, Any]) -> dict[str, Any]:
    for key in raw.keys() - TOP_LEVEL_KEYS:
        raise ConfigError(f"unknown key {key!r}")
    for key in ("exp_id", "run_name", "seeds", "evaluate"):
        if key not in raw:
            raise ConfigError(f"missing required key {key!r}")
    if raw["exp_id"] not in catalog_ids():
        raise ConfigError(f"exp_id {raw['exp_id']!r} is not in the experiment catalog")
    if not RUN_NAME_PATTERN.match(str(raw["run_name"])):
        raise ConfigError("run_name must be a slug of letters, digits, '.', '_' or '-'")
    seeds = raw["seeds"]
    if not (isinstance(seeds, list) and seeds and all(type(s) is int for s in seeds)):
        raise ConfigError("seeds must be a non-empty list of integers")
    evaluate = raw["evaluate"]
    for key in evaluate.keys() - EVALUATE_KEYS:
        raise ConfigError(f"unknown key {key!r} in evaluate")
    source = evaluate.get("checkpoints") or {}
    if set(source) != {"exp_id", "run_name"}:
        raise ConfigError("evaluate.checkpoints needs exactly exp_id and run_name")
    suites = evaluate.get("suites") or []
    unknown = set(suites) - DEFENDER_SUITES - ATTACKER_SUITES
    if not suites or unknown:
        raise ConfigError(f"evaluate.suites must be reportable suites, got {sorted(unknown)}")
    if len({s in DEFENDER_SUITES for s in suites}) > 1:
        raise ConfigError("evaluate.suites mixes defender and attacker suites")
    return {"owner": None, "rq": [], **raw}


def _evaluate_seed(
    config, seed: int, *, results_root: Path, repo: Path, backend, allow_dirty: bool
) -> Path:
    evaluate = config["evaluate"]
    source = runmeta.run_dir(
        results_root, evaluate["checkpoints"]["exp_id"], evaluate["checkpoints"]["run_name"], seed
    )
    checkpoint = source / "checkpoint"
    if not (checkpoint / "meta.yaml").exists():
        raise FileNotFoundError(f"no checkpoint to evaluate in {checkpoint}")
    source_run_id = yaml.safe_load((source / "meta.yaml").read_text())["run_id"]
    directory = runmeta.run_dir(results_root, config["exp_id"], config["run_name"], seed)
    meta = runmeta.build_meta(config, seed=seed, repo=repo, allow_dirty=allow_dirty)
    meta["source_run_id"] = source_run_id
    runmeta.write_meta(directory, meta)
    (directory / "config.resolved.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    started = time.monotonic()
    agent = load_checkpoint(checkpoint)
    suites = {}
    for suite in evaluate["suites"]:
        if suite in DEFENDER_SUITES:
            suites[suite] = harness.evaluate_defender(agent, suite, backend=backend)
        else:
            results = harness.run_attacker_suite(
                agent, suite, defender=evaluate.get("defender"), backend=backend
            )
            spec = harness.ATTACKER_SUITES[suite]
            suites[suite] = harness.summarize_attacker(results, query_budget=spec.query_budget)
    payload = {"source_run_id": source_run_id, "suites": suites}
    (directory / "final_eval.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    runmeta.finalize_meta(directory, duration_s=round(time.monotonic() - started, 3))
    return directory


def run_evaluation(
    config: dict[str, Any],
    *,
    results_root: Path = RESULTS_ROOT,
    repo: Path = PROJECT_ROOT,
    backend=None,
    allow_dirty: bool = False,
) -> list[Path]:
    config = resolve_eval_config(config)
    runmeta.ensure_clean(repo, allow_dirty=allow_dirty)
    owns_backend = backend is None
    backend = backend or resolve_backend("fast")
    try:
        return [
            _evaluate_seed(
                config,
                seed,
                results_root=results_root,
                repo=repo,
                backend=backend,
                allow_dirty=allow_dirty,
            )
            for seed in config["seeds"]
        ]
    finally:
        if owns_backend:
            backend.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate trained checkpoints on other suites")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="evaluate with uncommitted changes; marked in meta.yaml and not valid for the report",
    )
    args = parser.parse_args(argv)
    try:
        raw = yaml.safe_load(args.config.read_text())
        directories = run_evaluation(raw, results_root=args.results, allow_dirty=args.allow_dirty)
    except (ConfigError, runmeta.DirtyTreeError, FileNotFoundError) as error:
        parser.exit(2, f"error: {error}\n")
    for directory in directories:
        print(f"finished {directory}")


if __name__ == "__main__":
    sys.exit(main())
