"""Comparison table of the observation ablations ABL-1 and ABL-2 (F3-T06, catalogo.md).

DEF-REF-1's configuration (EXP-F5 alpha-4, the full 37-feature observation) against the same
configuration with the ModSecurity scores masked (ABL-1, indices 12-15) and with the session and
window features masked (ABL-2, indices 16-36), 5 seeds each, on defender-eval-v1. Reports TPR,
FPR, FPR-h and F1 with their bootstrap CI and the CI of each ablation's difference with the full
configuration (metricas.md: a CI containing 0 means no detectable difference). Writes
results/summary/ABL_comparison.csv from the per-seed final_eval.json files.

Usage: uv run python report/figuras/make_ABL.py [--results DIR]
"""

import argparse
import csv
import json
from pathlib import Path

from wafarena.eval.stats import bootstrap_ci, bootstrap_diff_ci

RESULTS_ROOT = Path(__file__).parents[2] / "results"
SUITE = "defender-eval-v1"
CONFIGS = {
    "full (EXP-F5 alpha-4)": ("EXP-F5", "alpha-4"),
    "ABL-1 no ModSecurity scores": ("ABL-1", "no-modsec-scores"),
    "ABL-2 no session/window": ("ABL-2", "no-session-window"),
}
METRICS = ("tpr", "fpr", "fpr_h", "f1")


def per_seed(results: Path, exp_id: str, run_name: str, metric: str) -> list[float]:
    return [
        float(json.loads(p.read_text())["suites"][SUITE][metric])
        for p in sorted((results / exp_id / run_name).glob("s*/final_eval.json"))
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    args = parser.parse_args()
    out = args.results / "summary" / "ABL_comparison.csv"
    full = CONFIGS["full (EXP-F5 alpha-4)"]
    rows = []
    for label, (exp_id, run_name) in CONFIGS.items():
        row = {"config": label, "exp_id": exp_id, "run_name": run_name}
        for metric in METRICS:
            values = per_seed(args.results, exp_id, run_name, metric)
            ci = bootstrap_ci(values)
            row["n_seeds"] = len(values)
            row.update({f"{metric}_mean": f"{ci.mean:.6f}", f"{metric}_low": f"{ci.low:.6f}"})
            row[f"{metric}_high"] = f"{ci.high:.6f}"
            if (exp_id, run_name) != full:
                diff = bootstrap_diff_ci(values, per_seed(args.results, *full, metric))
                row[f"{metric}_diff_vs_full"] = f"{diff.mean:.6f}"
                row[f"{metric}_diff_low"] = f"{diff.low:.6f}"
                row[f"{metric}_diff_high"] = f"{diff.high:.6f}"
        rows.append(row)
    columns = list(dict.fromkeys(k for r in rows for k in r))
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, restval="")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
