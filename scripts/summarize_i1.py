"""Summarize EXP-I1 fixed and historical self-play comparisons on val."""

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt

from wafarena.selfplay.config import load_config
from wafarena.selfplay.report import aggregate_fixed, collect_fixed, evaluate_history, write_csv

CONFIGS = {name: Path(f"configs/selfplay/exp_i1_{name}.yaml") for name in ("naive", "pool")}


def plot_tpr(curve: list[dict], path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, reference in zip(axes, ("ATK-REF-0", "ATK-REF-1"), strict=True):
        for condition, label in (("naive", "Latest only"), ("pool", "Historical pool")):
            rows = sorted(
                (
                    row
                    for row in curve
                    if row["role"] == "defender"
                    and row["reference"] == reference
                    and row["metric"] == "tpr"
                    and row["condition"] == condition
                ),
                key=lambda row: row["generation"],
            )
            if len(rows) != 8:
                raise ValueError(f"missing EXP-I1 TPR generations for {condition}/{reference}")
            x = [row["generation"] for row in rows]
            y = [row["mean"] if row["mean"] is not None else math.nan for row in rows]
            color = ax.plot(x, y, marker="o", label=label)[0].get_color()
            ax.fill_between(
                x,
                [row["ci_low"] if row["ci_low"] is not None else math.nan for row in rows],
                [row["ci_high"] if row["ci_high"] is not None else math.nan for row in rows],
                color=color,
                alpha=0.15,
            )
            for row in rows:
                if row["n_defined"] < 3:
                    ax.annotate(
                        f"n={row['n_defined']}",
                        (row["generation"], row["mean"] if row["mean"] is not None else 0.02),
                        xytext=(0, 7),
                        textcoords="offset points",
                        ha="center",
                        fontsize=7,
                        color=color,
                    )
        ax.set_title(reference)
        ax.set_xlabel("Defender generation")
        ax.set_xticks(range(1, 9))
        ax.set_ylim(0, 1.02)
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("TPR on val")
    axes[1].legend(loc="lower left")
    fig.suptitle("EXP-I1: latest opponent versus historical pool")
    fig.text(
        0.5,
        0.01,
        "Three paired runs; seed means and 95% bootstrap CIs. Labels show n when <3.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--checkpoints", type=Path, default=Path("checkpoints/selfplay"))
    parser.add_argument("--summary-dir", type=Path, default=Path("results/summary"))
    parser.add_argument("--figure", type=Path, default=Path("report/figuras/EXP-I1_tpr.png"))
    args = parser.parse_args()
    configs = {name: load_config(path) for name, path in CONFIGS.items()}
    fixed, runs, sha = collect_fixed(args.results, args.checkpoints, configs)
    historical = evaluate_history(runs, args.results)
    curve = aggregate_fixed(fixed)
    write_csv(args.summary_dir / "EXP-I1_runs.csv", fixed)
    write_csv(args.summary_dir / "EXP-I1_curve.csv", curve)
    write_csv(args.summary_dir / "EXP-I1_history.csv", historical)
    plot_tpr(curve, args.figure)
    print(f"EXP-I1 {sha}: {len(runs)} runs, {len(historical)} historical comparisons")
    print(f"Wrote {args.summary_dir / 'EXP-I1_curve.csv'} and {args.figure}")


if __name__ == "__main__":
    main()
