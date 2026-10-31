"""Run or resume all EXP-H1 seeds; completed clean runs are left intact.

Start the lab first, then run this script inside the runner container. Use --run-name and --seed
to profile one configuration before launching the full sweep.
"""

import argparse
import csv
from pathlib import Path

import yaml

from wafarena import runmeta
from wafarena.envs.resolve import resolve_backend
from wafarena.run import run_experiment
from wafarena.runconfig import load_config


def _complete(path: Path, *, seed: int, steps: int, sha: str) -> bool:
    meta_path = path / "meta.yaml"
    if not meta_path.exists():
        return False
    meta = yaml.safe_load(meta_path.read_text())
    if meta["dirty"] or meta["seed"] != seed or meta["git_sha"] != sha:
        raise ValueError(f"existing run has incompatible provenance: {path}")
    if "duration_s" not in meta or not (path / "eval.csv").exists():
        raise ValueError(f"incomplete run requires a new results root: {path}")
    with (path / "eval.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or int(rows[-1]["step"]) != steps:
        raise ValueError(f"incomplete validation curve requires a new results root: {path}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results/_h1_final"))
    parser.add_argument("--run-name", action="append")
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    repo = Path(".")
    sha = runmeta.git_info(repo).sha
    paths = sorted(Path("configs/exp/EXP-H1").glob("*.yaml"))
    if args.run_name:
        paths = [path for path in paths if path.stem in args.run_name]
        if len(paths) != len(set(args.run_name)):
            parser.error("unknown --run-name")
    for path in paths:
        config = load_config(path)
        seeds = [args.seed] if args.seed is not None else config["seeds"]
        if any(seed not in config["seeds"] for seed in seeds):
            parser.error(f"seed outside {path.name} configuration")
        backend = resolve_backend(config["env"]["backend"])
        try:
            for seed in seeds:
                directory = runmeta.run_dir(args.results, "EXP-H1", config["run_name"], seed)
                if _complete(directory, seed=seed, steps=config["train"]["total_steps"], sha=sha):
                    print(f"skip complete {directory}", flush=True)
                    continue
                one = dict(config)
                one["seeds"] = [seed]
                run_experiment(one, results_root=args.results, repo=repo, backend=backend)
                print(f"finished {directory}", flush=True)
        finally:
            backend.close()


if __name__ == "__main__":
    main()
