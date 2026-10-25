"""Figure of EXP-G4 (F3-T09, catalogo.md): PPO against DEF-REF-1 with entropy coefficient
0, 0.01 and 0.05; diversity of the successful payloads (DIV) against evasion rate (ER).

DIV needs two distinct successful payloads in a run; when no seed has them it is undefined (nan)
and the figure says so instead of drawing a value. To still show whether the bonus made the
attacker more stochastic, it also reports the policy's entropy at the end of training: the mean of
`m_entropy` (train.csv) over the last `LATE_FRACTION` of the steps, per seed, with its bootstrap CI.
ER, DIV and UNQ come from results/summary/EXP-G4.csv (attacker-eval-v1 against DEF-REF-1).
Writes results/summary/EXP-G4_entropy.csv and report/figuras/EXP-G4_div_er.png.

Usage: uv run python report/figuras/make_EXP-G4.py [--results DIR] [--out DIR]
"""

import argparse
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from wafarena.eval.stats import bootstrap_ci

REPORT_ROOT = Path(__file__).parent
RESULTS_ROOT = REPORT_ROOT.parents[1] / "results"
EXP_ID = "EXP-G4"
RUNS = {"ppo-ent-0": 0.0, "ppo-ent-001": 0.01, "ppo-ent-005": 0.05}
TOTAL_STEPS = 200_000
LATE_FRACTION = 0.1


def late_entropy(train_csv: Path) -> float:
    with train_csv.open() as handle:
        rows = [r for r in csv.DictReader(handle) if r.get("m_entropy")]
    start = TOTAL_STEPS * (1 - LATE_FRACTION)
    return float(np.mean([float(r["m_entropy"]) for r in rows if int(r["step"]) > start]))


def build(results: Path) -> list[dict]:
    with (results / "summary" / f"{EXP_ID}.csv").open() as handle:
        summary = {r["run_name"]: r for r in csv.DictReader(handle)}
    rows = []
    for run_name, coef in RUNS.items():
        s = summary[run_name]
        seeds = sorted((results / EXP_ID / run_name).glob("s*/train.csv"))
        entropy = bootstrap_ci([late_entropy(p) for p in seeds])
        rows.append(
            {
                "run_name": run_name,
                "ent_coef": coef,
                "n_seeds": s["n_seeds"],
                "er_mean": s["evasion_rate_mean"],
                "er_low": s["evasion_rate_low"],
                "er_high": s["evasion_rate_high"],
                "div_mean": s["diversity_mean"] or "nan",
                "unq_mean": s["uniqueness_mean"] or "nan",
                "policy_entropy_late_mean": f"{entropy.mean:.6f}",
                "policy_entropy_late_low": f"{entropy.low:.6f}",
                "policy_entropy_late_high": f"{entropy.high:.6f}",
            }
        )
    return rows


def plot(table_csv: Path, out: Path) -> None:
    with table_csv.open() as handle:
        rows = list(csv.DictReader(handle))
    fig, (ax_div, ax_ent) = plt.subplots(1, 2, figsize=(11, 4.2))
    defined = [r for r in rows if not math.isnan(float(r["div_mean"]))]
    if defined:
        for r in defined:
            er = float(r["er_mean"])
            err = [[er - float(r["er_low"])], [float(r["er_high"]) - er]]
            ax_div.errorbar(
                [er],
                [float(r["div_mean"])],
                xerr=err,
                fmt="o",
                capsize=3,
                label=f"coef = {r['ent_coef']}",
            )
        ax_div.set_xlabel("ER contra DEF-REF-1 (attacker-eval-v1)")
        ax_div.set_ylabel("DIV (payloads exitosos)")
        ax_div.legend(fontsize=8)
    else:  # no point to draw: show ER per coefficient and say why DIV is missing
        coefs = [float(r["ent_coef"]) for r in rows]
        er = np.array([float(r["er_mean"]) for r in rows])
        low = np.array([float(r["er_low"]) for r in rows])
        high = np.array([float(r["er_high"]) for r in rows])
        ax_div.errorbar(coefs, er, yerr=[er - low, high - er], fmt="o", capsize=3)
        ax_div.set_xlabel("coeficiente de entropía")
        ax_div.set_ylabel("ER contra DEF-REF-1 (attacker-eval-v1)")
        ax_div.text(
            0.5,
            0.85,
            "DIV indefinida en las tres configuraciones:\n"
            "ninguna semilla tiene dos payloads exitosos distintos",
            transform=ax_div.transAxes,
            ha="center",
            fontsize=8,
            bbox={"facecolor": "white", "edgecolor": "#999999"},
        )
    ax_div.set_title("DIV contra ER", fontsize=9)
    coef = [float(r["ent_coef"]) for r in rows]
    ent = np.array([float(r["policy_entropy_late_mean"]) for r in rows])
    low = np.array([float(r["policy_entropy_late_low"]) for r in rows])
    high = np.array([float(r["policy_entropy_late_high"]) for r in rows])
    ax_ent.errorbar(coef, ent, yerr=[ent - low, high - ent], fmt="o-", capsize=3)
    ax_ent.set_xlabel("coeficiente de entropía")
    ax_ent.set_ylabel("entropía de la política al final del entrenamiento")
    ax_ent.set_title("¿El bono hace más estocástico al atacante? (media e IC 95 %)", fontsize=9)
    fig.suptitle("EXP-G4: PPO contra DEF-REF-1, 5 semillas por coeficiente")
    fig.tight_layout()
    fig.savefig(out / f"{EXP_ID}_div_er.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=REPORT_ROOT)
    args = parser.parse_args()
    table_csv = args.results / "summary" / f"{EXP_ID}_entropy.csv"
    if (args.results / EXP_ID).is_dir():
        rows = build(args.results)
        with table_csv.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    plot(table_csv, args.out)
    print(f"wrote {table_csv} and {EXP_ID}_div_er.png in {args.out}")


if __name__ == "__main__":
    main()
