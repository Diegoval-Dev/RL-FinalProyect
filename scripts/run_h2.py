"""Run EXP-H2 seeds with seed-boundary resume after starting the Docker lab.

An interrupted seed remains in place for diagnosis; use a fresh results root to rerun it.
"""

import argparse
from pathlib import Path

from scripts.run_h1 import _complete
from wafarena import runmeta
from wafarena.envs.resolve import resolve_backend
from wafarena.run import run_experiment
from wafarena.runconfig import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results/_h2_final"))
    parser.add_argument("--run-name", action="append")
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    repo = Path(".")
    sha = runmeta.git_info(repo).sha
    paths = sorted(Path("configs/exp/EXP-H2").glob("*.yaml"))
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
                directory = runmeta.run_dir(args.results, "EXP-H2", config["run_name"], seed)
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
