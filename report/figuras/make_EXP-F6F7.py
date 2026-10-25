"""Generalization table of the static defender (F3-T07: EXP-F6 unseen families, EXP-F7 unseen hard
benign traffic), the baseline that Phase 4 compares the self-play defender against.

For DEF-REF-1's configuration (EXP-F5 alpha-4, 5 seeds; seed 0 is DEF-REF-1) it reads the
evaluation-only runs (results/<EXP>/def-ref-1-candidate/s*/final_eval.json), which hold each
checkpoint on the new suite and on defender-eval-v1, and reports TPR, FPR and FPR-h per suite with
their bootstrap CI and the drop with respect to defender-eval-v1 (CI of the difference). ModSecurity
PL1-PL4 come from results/summary/modsec_defender_suites.csv (deterministic, no CI). Writes
results/summary/EXP-F6F7_generalization.csv; without raw runs the CSV is kept as it is.

Usage: uv run python report/figuras/make_EXP-F6F7.py [--results DIR]
"""

import argparse
import csv
import json
from pathlib import Path

from wafarena.eval.stats import bootstrap_ci, bootstrap_diff_ci

RESULTS_ROOT = Path(__file__).parents[2] / "results"
BASE_SUITE = "defender-eval-v1"
EXPERIMENTS = {"EXP-F6": "defender-eval-family-v1", "EXP-F7": "defender-eval-hard-v1"}
METRICS = ("tpr", "fpr", "fpr_h")
RUN_NAME = "def-ref-1-candidate"


def _fmt(value: float) -> str:
    return f"{value:.6f}"


def dqn_rows(results: Path) -> list[dict]:
    rows = []
    for exp_id, suite in EXPERIMENTS.items():
        finals = [
            json.loads(p.read_text())["suites"]
            for p in sorted((results / exp_id / RUN_NAME).glob("s*/final_eval.json"))
        ]
        row = {"defender": "DEF-REF-1 config (EXP-F5 alpha-4)", "exp_id": exp_id, "suite": suite}
        row["n_seeds"] = len(finals)
        for metric in METRICS:
            new = [f[suite][metric] for f in finals]
            base = [f[BASE_SUITE][metric] for f in finals]
            ci, drop = bootstrap_ci(new), bootstrap_diff_ci(new, base)
            row.update(
                {
                    f"{metric}_mean": _fmt(ci.mean),
                    f"{metric}_low": _fmt(ci.low),
                    f"{metric}_high": _fmt(ci.high),
                    f"{metric}_change_vs_eval_v1_mean": _fmt(drop.mean),
                    f"{metric}_change_vs_eval_v1_low": _fmt(drop.low),
                    f"{metric}_change_vs_eval_v1_high": _fmt(drop.high),
                }
            )
        rows.append(row)
    return rows


def modsec_rows(results: Path) -> list[dict]:
    with (results / "summary" / "modsec_defender_suites.csv").open() as handle:
        table = list(csv.DictReader(handle))
    base = {r["defender"]: r for r in table if r["suite"] == BASE_SUITE}
    rows = []
    for exp_id, suite in EXPERIMENTS.items():
        for r in (r for r in table if r["suite"] == suite):
            row = {"defender": r["defender"], "exp_id": exp_id, "suite": suite, "n_seeds": 1}
            for metric in METRICS:
                value, ref = float(r[metric]), float(base[r["defender"]][metric])
                row.update(
                    {
                        f"{metric}_mean": _fmt(value),
                        f"{metric}_low": _fmt(value),
                        f"{metric}_high": _fmt(value),
                        f"{metric}_change_vs_eval_v1_mean": _fmt(value - ref),
                        f"{metric}_change_vs_eval_v1_low": _fmt(value - ref),
                        f"{metric}_change_vs_eval_v1_high": _fmt(value - ref),
                    }
                )
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    args = parser.parse_args()
    out = args.results / "summary" / "EXP-F6F7_generalization.csv"
    if not (args.results / "EXP-F6" / RUN_NAME).is_dir():
        print(f"no raw runs: keeping {out}")
        return
    rows = dqn_rows(args.results) + modsec_rows(args.results)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
