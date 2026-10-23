"""Figure for EXP-A2 (catalogo.md): regret around the mid-run defender switch (pl1 -> pl3).

Reads the raw results/EXP-A2/<run>/s<seed>/pulls.csv; the band is mean ± 1 SD across seeds (see
make_EXP-A1.py's docstring for why this isn't a per-step bootstrap CI).

Usage: uv run python report/figuras/make_EXP-A2.py [--results DIR] [--out DIR] [--switch-at N]
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from wafarena.bandit_summarize import load_regret_curves

REPORT_ROOT = Path(__file__).parent
RESULTS_ROOT = REPORT_ROOT.parents[1] / "results"
EXP_ID = "EXP-A2"
DEFAULT_SWITCH_AT = 10000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=REPORT_ROOT)
    parser.add_argument("--switch-at", type=int, default=DEFAULT_SWITCH_AT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    curves = load_regret_curves(EXP_ID, args.results)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for run_name in sorted(curves):
        per_seed = curves[run_name]
        steps = next(iter(per_seed.values()))["step"]
        stacked = np.vstack([s["regret_cumulative"] for s in per_seed.values()])
        mean, std = stacked.mean(axis=0), stacked.std(axis=0)
        ax.plot(steps, mean, label=run_name)
        ax.fill_between(steps, mean - std, mean + std, alpha=0.15)
    ax.axvline(args.switch_at, color="black", linestyle="--", linewidth=1, label="cambio de PL")
    ax.set_xlabel("tiradas")
    ax.set_ylabel("regret acumulado R(t)")
    ax.set_title("EXP-A2: regret con cambio de defensor a mitad de la corrida")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(args.out / f"{EXP_ID}_regret.png", dpi=150)
    plt.close(fig)
    print(f"wrote {EXP_ID}_regret.png in {args.out}")


if __name__ == "__main__":
    main()
