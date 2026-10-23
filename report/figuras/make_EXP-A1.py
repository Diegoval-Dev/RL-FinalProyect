"""Figures for EXP-A1 (catalogo.md): regret per method and final mean reward in attacker-eval-v1.

Reads results/summary/EXP-A1.csv (bootstrap CI of the final metrics, per run_name) for the mean
reward bars, and the raw results/EXP-A1/<run>/s<seed>/pulls.csv for the regret curves (mean ± 1 SD
across seeds; a per-step bootstrap CI over 20 000 points would be prohibitively slow and isn't
needed for an illustrative curve — only the final numbers plotted here come from a registered run).

Usage: uv run python report/figuras/make_EXP-A1.py [--results DIR] [--out DIR]
"""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from wafarena.bandit_summarize import load_regret_curves

REPORT_ROOT = Path(__file__).parent
RESULTS_ROOT = REPORT_ROOT.parents[1] / "results"
EXP_ID = "EXP-A1"


def read_summary(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def plot_regret(results_root: Path, out: Path) -> None:
    curves = load_regret_curves(EXP_ID, results_root)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for run_name in sorted(curves):
        per_seed = curves[run_name]
        steps = next(iter(per_seed.values()))["step"]
        stacked = np.vstack([s["regret_cumulative"] for s in per_seed.values()])
        mean, std = stacked.mean(axis=0), stacked.std(axis=0)
        ax.plot(steps, mean, label=run_name)
        ax.fill_between(steps, mean - std, mean + std, alpha=0.15)
    ax.set_xlabel("tiradas")
    ax.set_ylabel("regret acumulado R(t)")
    ax.set_title("EXP-A1: regret acumulado por método (media ± 1 DE sobre semillas)")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out / "EXP-A1_regret.png", dpi=150)
    plt.close(fig)


def plot_mean_reward(summary_path: Path, out: Path) -> None:
    rows = read_summary(summary_path)
    rows = [r for r in rows if r["suite"] == "attacker-eval-v1"]
    names = [r["run_name"] for r in rows]
    mean = [float(r["evasion_rate_mean"]) for r in rows]
    low = [float(r["evasion_rate_low"]) for r in rows]
    high = [float(r["evasion_rate_high"]) for r in rows]
    err = [
        [m - lo for m, lo in zip(mean, low, strict=True)],
        [hi - m for hi, m in zip(high, mean, strict=True)],
    ]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(names, mean, yerr=err, capsize=4)
    ax.set_ylabel("tasa de evasión final (attacker-eval-v1)")
    ax.set_title("EXP-A1: ER final por método, IC 95 % (bootstrap sobre semillas)")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(out / "EXP-A1_mean_reward.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=REPORT_ROOT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    plot_regret(args.results, args.out)
    plot_mean_reward(args.results / "summary" / f"{EXP_ID}.csv", args.out)
    print(f"wrote {EXP_ID}_regret.png and {EXP_ID}_mean_reward.png in {args.out}")


if __name__ == "__main__":
    main()
