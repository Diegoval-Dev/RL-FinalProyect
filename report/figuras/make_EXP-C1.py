"""Figure for EXP-C1 (catalogo.md): ER on val against training steps, first/every-visit MC.

Reads the raw results/EXP-C1/<run>/s<seed>/eval.csv (mean ± 1 SD across seeds; see
make_EXP-A1.py's docstring for why this isn't a per-step bootstrap CI).

Usage: uv run python report/figuras/make_EXP-C1.py [--results DIR] [--out DIR]
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from wafarena.summarize import load_val_curves

REPORT_ROOT = Path(__file__).parent
RESULTS_ROOT = REPORT_ROOT.parents[1] / "results"
EXP_ID = "EXP-C1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=REPORT_ROOT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    curves = load_val_curves(EXP_ID, args.results)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for run_name in sorted(curves):
        per_seed = curves[run_name]
        steps = next(iter(per_seed.values()))["step"]
        stacked = np.vstack([s["evasion_rate"] for s in per_seed.values()])
        mean, std = stacked.mean(axis=0), stacked.std(axis=0)
        ax.plot(steps, mean, label=run_name)
        ax.fill_between(steps, mean - std, mean + std, alpha=0.15)
    ax.set_xlabel("pasos de entrenamiento")
    ax.set_ylabel("ER en val (attacker-val-v1)")
    ax.set_title("EXP-C1: ER en val por método (media ± 1 DE sobre semillas)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(args.out / f"{EXP_ID}_er_vs_steps.png", dpi=150)
    plt.close(fig)
    print(f"wrote {EXP_ID}_er_vs_steps.png in {args.out}")


if __name__ == "__main__":
    main()
