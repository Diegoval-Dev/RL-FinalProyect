"""Table and figure of the DQN ablation EXP-F1..F4 (F3-T04, catalogo.md).

Reads the four versioned summaries (`results/summary/EXP-F1.csv` .. `EXP-F4.csv`, suite
`defender-eval-v1`) and, from each run's train.csv, `m_missed_attack_frac`: the fraction of the
sampled replay batch made of attacks the defender let through with effect (the quantity PER is
expected to raise). Its per-seed mean over training gets a bootstrap CI like every other metric.
Writes results/summary/EXP-F_ablation.csv, results/summary/EXP-F_ablation_diffs.csv (bootstrap CI
of the difference between each variant and the one before it, per metricas.md: a CI containing 0
means no detectable difference) and report/figuras/EXP-F_ablation.png; without raw runs the CSVs
are replotted as they are.

Usage: uv run python report/figuras/make_EXP-F_ablation.py [--results DIR] [--out DIR]
"""

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from wafarena.eval.stats import bootstrap_ci, bootstrap_diff_ci

REPORT_ROOT = Path(__file__).parent
RESULTS_ROOT = REPORT_ROOT.parents[1] / "results"
EXPERIMENTS = ("EXP-F1", "EXP-F2", "EXP-F3", "EXP-F4")
SUITE = "defender-eval-v1"
METRICS = ("tpr", "fpr", "fpr_h", "f1", "q_allow_attack")


def build_table(results: Path) -> list[dict]:
    table = []
    for exp_id in EXPERIMENTS:
        with (results / "summary" / f"{exp_id}.csv").open() as handle:
            summary = next(r for r in csv.DictReader(handle) if r["suite"] == SUITE)
        row = {"exp_id": exp_id, "run_name": summary["run_name"], "n_seeds": summary["n_seeds"]}
        for metric in METRICS:
            for part in ("mean", "low", "high"):
                row[f"{metric}_{part}"] = summary[f"{metric}_{part}"]
        per_seed = []
        for train_csv in sorted((results / exp_id).glob("*/s*/train.csv")):
            with train_csv.open() as handle:
                values = [
                    float(r["m_missed_attack_frac"])
                    for r in csv.DictReader(handle)
                    if r.get("m_missed_attack_frac")
                ]
            per_seed.append(float(np.mean(values)))
        ci = bootstrap_ci(per_seed)
        row.update(
            {
                "missed_attack_frac_mean": f"{ci.mean:.6f}",
                "missed_attack_frac_low": f"{ci.low:.6f}",
                "missed_attack_frac_high": f"{ci.high:.6f}",
            }
        )
        table.append(row)
    return table


def per_seed_final(results: Path, exp_id: str, metric: str) -> list[float]:
    values = []
    for final in sorted((results / exp_id).glob("*/s*/final_eval.json")):
        values.append(float(json.loads(final.read_text())["suites"][SUITE][metric]))
    return values


def build_diffs(results: Path) -> list[dict]:
    rows = []
    for before, after in zip(EXPERIMENTS, EXPERIMENTS[1:], strict=False):
        for metric in METRICS:
            ci = bootstrap_diff_ci(
                per_seed_final(results, after, metric), per_seed_final(results, before, metric)
            )
            rows.append(
                {
                    "comparison": f"{after} - {before}",
                    "metric": metric,
                    "diff_mean": f"{ci.mean:.6f}",
                    "diff_low": f"{ci.low:.6f}",
                    "diff_high": f"{ci.high:.6f}",
                    "contains_zero": int(ci.contains_zero),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(table_csv: Path, out: Path) -> None:
    with table_csv.open() as handle:
        rows = list(csv.DictReader(handle))
    labels = [r["run_name"].replace("dqn-", "") for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, metric, title in (
        (axes[0], "tpr", "TPR (defender-eval-v1)"),
        (axes[1], "q_allow_attack", "Q-ALLOW en ataques"),
        (axes[2], "missed_attack_frac", "Fracción del batch: ataques que pasaron"),
    ):
        mean = np.array([float(r[f"{metric}_mean"]) for r in rows])
        low = np.array([float(r[f"{metric}_low"]) for r in rows])
        high = np.array([float(r[f"{metric}_high"]) for r in rows])
        ax.bar(labels, mean, yerr=[mean - low, high - mean], capsize=4, color="#4C72B0")
        ax.set_title(title, fontsize=9)
        ax.tick_params(axis="x", labelrotation=20, labelsize=8)
    axes[0].set_ylim(0.95, 1.0)
    fig.suptitle("EXP-F1..F4: ablación incremental de DQN (media e IC 95 %, 5 semillas)")
    fig.tight_layout()
    fig.savefig(out / "EXP-F_ablation.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=REPORT_ROOT)
    args = parser.parse_args()
    table_csv = args.results / "summary" / "EXP-F_ablation.csv"
    if (args.results / EXPERIMENTS[0]).is_dir():
        write_csv(table_csv, build_table(args.results))
        write_csv(args.results / "summary" / "EXP-F_ablation_diffs.csv", build_diffs(args.results))
    plot(table_csv, args.out)
    print(f"wrote {table_csv} and EXP-F_ablation.png in {args.out}")


if __name__ == "__main__":
    main()
