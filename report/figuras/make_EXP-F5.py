"""Pareto figure of EXP-F5 (F3-T05, catalogo.md): the DQN defender's (FPR, TPR) for each alpha of
the sweep next to ModSecurity PL1-PL4, on defender-eval-v1.

Reads only versioned summaries: results/summary/EXP-F5.csv (mean and 95 % CI over 5 seeds per
alpha) and results/summary/modsec_defender_suites.csv (ModSecurity is deterministic: one point per
PL). Writes report/figuras/EXP-F5_pareto.png and results/summary/EXP-F5_dominance.csv.

Dominance is decided conservatively, with the CIs: alpha dominates a PL when its whole TPR interval
is at or above the PL's TPR, its whole FPR interval is at or below the PL's FPR, and at least one of
the two holds strictly. Overlapping intervals are reported as "not dominated", never as a win.

Usage: uv run python report/figuras/make_EXP-F5.py [--results DIR] [--out DIR]
"""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt

REPORT_ROOT = Path(__file__).parent
RESULTS_ROOT = REPORT_ROOT.parents[1] / "results"
SUITE = "defender-eval-v1"


def load(results: Path) -> tuple[list[dict], list[dict]]:
    with (results / "summary" / "EXP-F5.csv").open() as handle:
        dqn = [r for r in csv.DictReader(handle) if r["suite"] == SUITE]
    dqn.sort(key=lambda r: float(r["run_name"].split("-")[1]))
    with (results / "summary" / "modsec_defender_suites.csv").open() as handle:
        modsec = [r for r in csv.DictReader(handle) if r["suite"] == SUITE]
    return dqn, modsec


def dominance(dqn: list[dict], modsec: list[dict]) -> list[dict]:
    rows = []
    for pl in modsec:
        pl_tpr, pl_fpr = float(pl["tpr"]), float(pl["fpr"])
        winners = []
        for d in dqn:
            tpr_low, fpr_high = float(d["tpr_low"]), float(d["fpr_high"])
            at_least = tpr_low >= pl_tpr and fpr_high <= pl_fpr
            strictly = tpr_low > pl_tpr or fpr_high < pl_fpr
            if at_least and strictly:
                winners.append(d["run_name"])
        rows.append(
            {
                "modsec": pl["defender"],
                "modsec_tpr": f"{pl_tpr:.6f}",
                "modsec_fpr": f"{pl_fpr:.6f}",
                "dominated": int(bool(winners)),
                "dominated_by": " ".join(winners),
            }
        )
    return rows


def _draw(ax, dqn: list[dict], modsec: list[dict], *, labels: bool) -> None:
    fpr = [float(d["fpr_mean"]) for d in dqn]
    tpr = [float(d["tpr_mean"]) for d in dqn]
    xerr = [
        [f - float(d["fpr_low"]) for f, d in zip(fpr, dqn, strict=True)],
        [float(d["fpr_high"]) - f for f, d in zip(fpr, dqn, strict=True)],
    ]
    yerr = [
        [t - float(d["tpr_low"]) for t, d in zip(tpr, dqn, strict=True)],
        [float(d["tpr_high"]) - t for t, d in zip(tpr, dqn, strict=True)],
    ]
    ax.errorbar(fpr, tpr, xerr=xerr, yerr=yerr, fmt="o-", capsize=3, label="DQN (Double + Dueling)")
    if labels:
        for d, x, y in zip(dqn, fpr, tpr, strict=True):
            ax.annotate(
                f"α={d['run_name'].split('-')[1]}",
                (x, y),
                textcoords="offset points",
                xytext=(7, -3),
                fontsize=8,
            )
    ax.scatter(
        [float(m["fpr"]) for m in modsec],
        [float(m["tpr"]) for m in modsec],
        marker="s",
        color="#C44E52",
        zorder=3,
        label="ModSecurity",
    )
    for m in modsec:
        ax.annotate(
            m["defender"].replace("modsec-", "").upper(),
            (float(m["fpr"]), float(m["tpr"])),
            textcoords="offset points",
            xytext=(6, 4),
            fontsize=8,
            color="#C44E52",
        )
    ax.set_xlabel("FPR (requests benignos)")
    ax.set_ylabel("TPR (requests de ataque)")
    ax.grid(alpha=0.3)


def plot(dqn: list[dict], modsec: list[dict], out: Path) -> None:
    fig, (ax_all, ax_zoom) = plt.subplots(1, 2, figsize=(12, 5))
    _draw(ax_all, dqn, modsec, labels=False)
    ax_all.set_title("Plano completo", fontsize=10)
    ax_all.legend(loc="lower right", fontsize=8)
    _draw(ax_zoom, dqn, modsec, labels=True)
    ax_zoom.set_xlim(-0.0005, 0.0025)
    ax_zoom.set_ylim(0.965, 1.002)
    ax_zoom.set_title("Detalle: FPR ≤ 0,0025 (PL3 y PL4 quedan fuera)", fontsize=10)
    fig.suptitle(
        "EXP-F5: frontera detección / falsos positivos en defender-eval-v1 "
        "(media e IC 95 % sobre 5 semillas; ModSecurity es determinista)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(out / "EXP-F5_pareto.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=REPORT_ROOT)
    args = parser.parse_args()
    dqn, modsec = load(args.results)
    rows = dominance(dqn, modsec)
    out_csv = args.results / "summary" / "EXP-F5_dominance.csv"
    with out_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    plot(dqn, modsec, args.out)
    print(f"wrote {out_csv} and EXP-F5_pareto.png in {args.out}")


if __name__ == "__main__":
    main()
