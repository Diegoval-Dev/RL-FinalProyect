"""Write EXP-H2 query-aligned curves, recovery rows, and the validation figure."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from wafarena.agents.dyna.h2_report import METHODS, summarize_h2, write_csv

LABELS = {
    "dyna-20-switch": "Dyna-Q (n=20)",
    "dyna-plus-1e-3-switch": "Dyna-Q+ (κ=0.001)",
    "dyna-plus-1e-2-switch": "Dyna-Q+ (κ=0.01)",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results/_h2_final"))
    parser.add_argument("--curve", type=Path, default=Path("results/summary/EXP-H2.csv"))
    parser.add_argument(
        "--recovery", type=Path, default=Path("results/summary/EXP-H2_recovery.csv")
    )
    parser.add_argument("--figure", type=Path, default=Path("report/figuras/EXP-H2_recovery.png"))
    args = parser.parse_args()
    curve, recovery = summarize_h2(args.results)
    write_csv(args.curve, curve)
    write_csv(args.recovery, recovery)

    fig, ax = plt.subplots(figsize=(10, 6))
    for method in METHODS:
        color = None
        for phase in ("pre", "post"):
            series = [row for row in curve if row["method"] == method and row["phase"] == phase]
            x = [row["relative_queries"] for row in series]
            line = ax.plot(
                x,
                [row["er_mean"] for row in series],
                label=LABELS[method] if phase == "pre" else None,
                color=color,
            )[0]
            color = line.get_color()
            ax.fill_between(
                x,
                [row["er_ci_low"] for row in series],
                [row["er_ci_high"] for row in series],
                color=color,
                alpha=0.12,
            )
    ax.axvline(0, color="black", linestyle="--", label="Defender switch")
    ax.set_xlabel("Real SEND queries relative to defender switch")
    ax.set_ylabel("Validation evasion rate")
    ax.set_title("EXP-H2: PL1 before switch, DEF-REF-1 after switch")
    ax.legend()
    fig.text(
        0.5,
        0.01,
        "Curves: 10 seeds, 95% bootstrap CI. Recovery is undefined when pre-switch ER is zero.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    args.figure.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.figure, dpi=160)
    plt.close(fig)
    print(f"wrote {args.curve}, {args.recovery}, and {args.figure}")


if __name__ == "__main__":
    main()
