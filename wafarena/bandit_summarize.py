"""Summaries of finished bandit runs: results/summary/<exp_id>.csv and per-seed regret curves."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import yaml

from wafarena.eval.stats import bootstrap_ci

RESULTS_ROOT = Path(__file__).parents[1] / "results"
SUMMARY_DIR = RESULTS_ROOT / "summary"
IDENTITY_COLUMNS = ["run_name", "suite", "n_seeds", "git_shas", "dirty_runs"]


def _load_runs(exp_dir: Path) -> dict[str, list[dict]]:
    runs: dict[str, list[dict]] = {}
    for final in sorted(exp_dir.glob("*/s*/final_eval.json")):
        run = final.parent
        runs.setdefault(run.parent.name, []).append(
            {
                "final": json.loads(final.read_text()),
                "meta": yaml.safe_load((run / "meta.yaml").read_text()),
            }
        )
    return runs


def _interval(values: list[float]) -> tuple[str, str, str]:
    finite = [v for v in values if not np.isnan(v)]
    if not finite:
        return "", "", ""
    ci = bootstrap_ci(finite)
    return f"{ci.mean:.6f}", f"{ci.low:.6f}", f"{ci.high:.6f}"


def summarize_experiment(exp_id: str, results_root: Path, out_dir: Path) -> Path:
    """Mean and 95 % bootstrap CI over seeds of each final metric, per run_name and suite."""
    runs = _load_runs(Path(results_root) / exp_id)
    if not runs:
        raise FileNotFoundError(f"no finished runs for {exp_id} under {results_root}")
    table = []
    for run_name, seeds in sorted(runs.items()):
        for suite in sorted({s for seed in seeds for s in seed["final"]["suites"]}):
            per_seed = [seed["final"]["suites"][suite] for seed in seeds]
            row = {
                "run_name": run_name,
                "suite": suite,
                "n_seeds": len(per_seed),
                "git_shas": "+".join(sorted({seed["meta"]["git_sha"] for seed in seeds})),
                "dirty_runs": sum(bool(seed["meta"].get("allow_dirty")) for seed in seeds),
            }
            for metric in per_seed[0]:
                mean, low, high = _interval([float(m[metric]) for m in per_seed])
                row.update({f"{metric}_mean": mean, f"{metric}_low": low, f"{metric}_high": high})
            table.append(row)
    out = Path(out_dir) / f"{exp_id}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    columns = IDENTITY_COLUMNS + _metric_columns(table)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(table)
    return out


def _metric_columns(table: list[dict]) -> list[str]:
    seen: list[str] = []
    for row in table:
        seen.extend(key for key in row if key not in IDENTITY_COLUMNS and key not in seen)
    return seen


def load_regret_curves(exp_id: str, results_root: Path) -> dict[str, dict[int, dict]]:
    """{run_name: {seed: {"step": array, "regret_cumulative": array}}}, from every pulls.csv."""
    curves: dict[str, dict[int, dict]] = {}
    for pulls in sorted((Path(results_root) / exp_id).glob("*/s*/pulls.csv")):
        run_name, seed = pulls.parent.parent.name, int(pulls.parent.name[1:])
        with pulls.open() as handle:
            rows = list(csv.DictReader(handle))
        curves.setdefault(run_name, {})[seed] = {
            "step": np.array([int(r["step"]) for r in rows]),
            "regret_cumulative": np.array([float(r["regret_cumulative"]) for r in rows]),
        }
    return curves


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Summarize the runs of one bandit experiment")
    parser.add_argument("--exp", required=True, help="exp_id from the catalog, e.g. EXP-A1")
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=SUMMARY_DIR)
    args = parser.parse_args(argv)
    print(f"wrote {summarize_experiment(args.exp, args.results, args.out)}")


if __name__ == "__main__":
    main()
