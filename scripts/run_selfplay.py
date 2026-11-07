"""Run or resume a self-play YAML protocol."""

import argparse
from pathlib import Path

from wafarena.selfplay.config import load_config
from wafarena.selfplay.orchestrator import run_selfplay


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run generation-based self-play")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--checkpoints", type=Path, default=Path("checkpoints/selfplay"))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--max-generations", type=int)
    args = parser.parse_args(argv)
    config = load_config(args.config)
    if args.seed is not None:
        if args.seed not in config["seeds"]:
            parser.error(f"seed {args.seed} is absent from {args.config}")
        config["seeds"] = [args.seed]
    for path in run_selfplay(
        config,
        results_root=args.results,
        checkpoint_root=args.checkpoints,
        resume=args.resume,
        allow_dirty=args.allow_dirty,
        max_generations=args.max_generations,
    ):
        print(path)


if __name__ == "__main__":
    main()
