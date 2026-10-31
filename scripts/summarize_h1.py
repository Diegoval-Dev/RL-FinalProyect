"""Aggregate and plot EXP-H1 from complete, clean validation runs."""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt

from wafarena.agents.dyna.report import DEFENDERS, METHODS, summarize_h1, write_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--summary", type=Path, default=Path("results/summary/EXP-H1.csv"))
    parser.add_argument(
        "--figure", type=Path, default=Path("report/figuras/EXP-H1_er_vs_queries.png")
    )
    parser.add_argument(
        "--reference", type=Path, default=Path("results/summary/EXP-H1_ATK-REF-1.csv")
    )
    args = parser.parse_args()
    rows = summarize_h1(args.results)
    with args.reference.open(newline="") as handle:
        references = {row["defender"]: row for row in csv.DictReader(handle)}
    if set(references) != set(DEFENDERS) or any(
        row["checkpoint"] != "ATK-REF-1" or row["suite"] != "attacker-val-v1"
        for row in references.values()
    ):
        raise ValueError("invalid ATK-REF-1 validation reference")
    write_summary(args.summary, rows)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex="col")
    for column, defender in enumerate(DEFENDERS):
        for method in METHODS:
            series = [
                row for row in rows if row["defender"] == defender and row["method"] == method
            ]
            x = [row["real_queries"] for row in series]
            axes[0, column].plot(x, [row["er_mean"] for row in series], label=method)
            axes[0, column].fill_between(
                x,
                [row["er_ci_low"] for row in series],
                [row["er_ci_high"] for row in series],
                alpha=0.12,
            )
            if method != "ppo":
                axes[1, column].plot(
                    x, [row["surrogate_accuracy_mean"] for row in series], label=method
                )
                axes[1, column].plot(
                    x,
                    [row["surrogate_minority_recall_mean"] for row in series],
                    linestyle="--",
                    alpha=0.6,
                )
        axes[0, column].set_title(defender)
        axes[0, column].axhline(
            float(references[defender]["evasion_rate"]),
            color="black",
            linestyle=":",
            label="ATK-REF-1 (fixed PPO, one seed)",
        )
        axes[0, column].set_ylabel("ER on val")
        axes[1, column].set_ylabel("Surrogate accuracy / minority recall on val")
        axes[1, column].set_xlabel("Cumulative real SEND queries")
        axes[0, column].legend(fontsize=8)
    fig.text(
        0.5,
        0.01,
        "Dashed lines: minority recall. Class counts and calibration: EXP-H1 eval.csv. "
        "Fixed reference training queries are outside the H1 axis.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    args.figure.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.figure, dpi=160)
    plt.close(fig)
    print(f"wrote {args.summary} and {args.figure}")


if __name__ == "__main__":
    main()
