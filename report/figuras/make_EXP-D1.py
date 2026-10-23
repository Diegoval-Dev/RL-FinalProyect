"""Figure for EXP-D1 (catalogo.md): SARSA vs Q-learning, ER on val and BRK during training.

Two panels sharing the step axis: ER (from eval.csv, like EXP-C1's figure) and BRK (from
train.csv, binned into the same step grid). The hypothesis is the *cliff walking* effect:
Q-learning (off-policy) takes the riskier path and breaks the payload more often than SARSA
(on-policy) while training, even if both end up at a similar ER.

Usage: uv run python report/figuras/make_EXP-D1.py [--results DIR] [--out DIR]
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from wafarena.summarize import load_train_brk_curve, load_val_curves

REPORT_ROOT = Path(__file__).parent
RESULTS_ROOT = REPORT_ROOT.parents[1] / "results"
EXP_ID = "EXP-D1"
EVAL_STEPS = list(range(10000, 200001, 10000))


def _plot(ax, curves: dict, ylabel: str) -> None:
    for run_name in sorted(curves):
        per_seed = curves[run_name]
        steps = next(iter(per_seed.values()))["step"]
        key = "evasion_rate" if ylabel.startswith("ER") else "brk"
        stacked = np.vstack([s[key] for s in per_seed.values()])
        mean = np.nanmean(stacked, axis=0)
        std = np.nanstd(stacked, axis=0)
        ax.plot(steps, mean, label=run_name)
        ax.fill_between(steps, mean - std, mean + std, alpha=0.15)
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=REPORT_ROOT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    er_curves = load_val_curves(EXP_ID, args.results)
    brk_curves = load_train_brk_curve(EXP_ID, args.results, step_grid=EVAL_STEPS)

    fig, (ax_er, ax_brk) = plt.subplots(2, 1, figsize=(7, 7), sharex=True)
    _plot(ax_er, er_curves, "ER en val (attacker-val-v1)")
    _plot(ax_brk, brk_curves, "BRK durante entrenamiento")
    ax_brk.set_xlabel("pasos de entrenamiento")
    fig.suptitle("EXP-D1: SARSA vs Q-learning (media ± 1 DE sobre semillas)")
    fig.tight_layout()
    fig.savefig(args.out / f"{EXP_ID}_sarsa_vs_qlearning.png", dpi=150)
    plt.close(fig)
    print(f"wrote {EXP_ID}_sarsa_vs_qlearning.png in {args.out}")


if __name__ == "__main__":
    main()
