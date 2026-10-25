"""Figure for EXP-E2 (catalogo.md): weight norm and TD error against training steps.

The deadly triad (Sutton & Barto 11.3) predicts that linear Q-learning fed off-policy data can
diverge where the on-policy counterpart does not. Each run's train.csv has one row per session with
`m_weight_norm` and `m_td_error` (the agent's per-step values averaged over the session). This
script bins them on a fixed step grid, writes the versioned curve to
results/summary/EXP-E2_weight_norm.csv and plots it from that CSV, so the figure can be rebuilt
without the raw runs.

Usage: uv run python report/figuras/make_EXP-E2.py [--results DIR] [--out DIR]
"""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPORT_ROOT = Path(__file__).parent
RESULTS_ROOT = REPORT_ROOT.parents[1] / "results"
EXP_ID = "EXP-E2"
STEP_GRID = list(range(5000, 100001, 5000))
CURVE_COLUMNS = ["run_name", "seed", "step", "weight_norm", "td_error"]


def binned_curves(results_root: Path) -> list[dict]:
    rows_out = []
    bounds = [0, *STEP_GRID]
    for train_csv in sorted((results_root / EXP_ID).glob("*/s*/train.csv")):
        run_name, seed = train_csv.parent.parent.name, int(train_csv.parent.name[1:])
        with train_csv.open() as handle:
            rows = list(csv.DictReader(handle))
        for low, high in zip(bounds, bounds[1:], strict=False):
            in_bin = [r for r in rows if low < int(r["step"]) <= high]
            norm = [float(r["m_weight_norm"]) for r in in_bin]
            td = [float(r["m_td_error"]) for r in in_bin]
            rows_out.append(
                {
                    "run_name": run_name,
                    "seed": seed,
                    "step": high,
                    "weight_norm": f"{np.mean(norm):.6g}" if norm else "nan",
                    "td_error": f"{np.mean(td):.6g}" if td else "nan",
                }
            )
    return rows_out


def plot(curve_csv: Path, out: Path) -> None:
    with curve_csv.open() as handle:
        rows = list(csv.DictReader(handle))
    fig, (ax_norm, ax_td) = plt.subplots(2, 1, figsize=(7, 7), sharex=True)
    for run_name in sorted({r["run_name"] for r in rows}):
        for ax, key in ((ax_norm, "weight_norm"), (ax_td, "td_error")):
            per_seed = {}
            for r in rows:
                if r["run_name"] == run_name:
                    per_seed.setdefault(r["seed"], []).append(float(r[key]))
            stacked = np.vstack(list(per_seed.values()))
            finite = np.where(np.isfinite(stacked), stacked, np.nan)
            mean = np.nanmean(finite, axis=0) if np.isfinite(finite).any() else finite[0]
            ax.plot(STEP_GRID, mean, label=f"{run_name} (media de {len(per_seed)} semillas)")
            for curve in finite:
                ax.plot(STEP_GRID, curve, alpha=0.25, linewidth=0.8, color=ax.lines[-1].get_color())
    ax_norm.set_yscale("log")
    ax_norm.set_ylabel("‖w‖ (norma de los pesos)")
    ax_td.set_yscale("log")
    ax_td.set_ylabel("|δ| (error TD medio)")
    ax_td.set_xlabel("pasos de entrenamiento")
    ax_norm.legend(fontsize=8)
    fig.suptitle("EXP-E2: triada mortal — off-policy contra on-policy")
    fig.tight_layout()
    fig.savefig(out / f"{EXP_ID}_weight_norm.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=REPORT_ROOT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    curve_csv = args.results / "summary" / f"{EXP_ID}_weight_norm.csv"
    rows = binned_curves(args.results)
    if rows:  # without raw runs, replot the versioned curve as it is
        curve_csv.parent.mkdir(parents=True, exist_ok=True)
        with curve_csv.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CURVE_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
    plot(curve_csv, args.out)
    print(f"wrote {curve_csv} and {EXP_ID}_weight_norm.png in {args.out}")


if __name__ == "__main__":
    main()
