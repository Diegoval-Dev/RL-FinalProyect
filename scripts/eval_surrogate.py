"""F4-T02: evaluate incremental SEND-response surrogates on train/val lab episodes."""

import argparse
import shutil
from pathlib import Path

from wafarena.agents.dyna.evaluation import evaluate_surrogate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/surrogate/f4_t02.yaml"))
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument(
        "--summary", type=Path, default=Path("results/summary/F4-T02_surrogate.csv")
    )
    args = parser.parse_args()

    directory = evaluate_surrogate(args.config, results_root=args.results)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(directory / "validation.csv", args.summary)
    print(f"finished {directory}")
    print(f"wrote {args.summary}")


if __name__ == "__main__":
    main()
