"""Summary of finished EXP-B1 runs: results/summary/EXP-B1.csv (convergence and final ER)."""

import argparse
import json
from pathlib import Path

import numpy as np
import yaml

from wafarena.eval.stats import bootstrap_ci

RESULTS_ROOT = Path(__file__).parents[1] / "results"
SUMMARY_DIR = RESULTS_ROOT / "summary"


def _load_runs(exp_dir: Path) -> list[dict]:
    runs = []
    for final in sorted(exp_dir.glob("*/s*/final_eval.json")):
        run = final.parent
        runs.append(
            {
                "final": json.loads(final.read_text())["suites"]["attacker-eval-v1"],
                "model": json.loads((run / "model_summary.json").read_text()),
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
    """One row: mean +/- 95% bootstrap CI of ER and of VI/PI iterations over seeds, and how many
    seeds had VI and PI agree on the final policy."""
    runs = _load_runs(Path(results_root) / exp_id)
    if not runs:
        raise FileNotFoundError(f"no finished runs for {exp_id} under {results_root}")
    er_mean, er_low, er_high = _interval([r["final"]["evasion_rate"] for r in runs])
    vi_mean, vi_low, vi_high = _interval(
        [r["model"]["value_iteration"]["iterations"] for r in runs]
    )
    pi_mean, pi_low, pi_high = _interval(
        [r["model"]["policy_iteration"]["iterations"] for r in runs]
    )
    row = {
        "n_seeds": len(runs),
        "git_shas": "+".join(sorted({r["meta"]["git_sha"] for r in runs})),
        "dirty_runs": sum(bool(r["meta"].get("allow_dirty")) for r in runs),
        "evasion_rate_mean": er_mean,
        "evasion_rate_low": er_low,
        "evasion_rate_high": er_high,
        "vi_iterations_mean": vi_mean,
        "vi_iterations_low": vi_low,
        "vi_iterations_high": vi_high,
        "pi_iterations_mean": pi_mean,
        "pi_iterations_low": pi_low,
        "pi_iterations_high": pi_high,
        "seeds_policies_agree": sum(r["model"]["policies_agree"] for r in runs),
        "max_value_diff_max": max(r["model"]["max_value_diff"] for r in runs),
    }
    out = Path(out_dir) / f"{exp_id}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Summarize the runs of EXP-B1")
    parser.add_argument("--exp", default="EXP-B1")
    parser.add_argument("--results", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--out", type=Path, default=SUMMARY_DIR)
    args = parser.parse_args(argv)
    print(f"wrote {summarize_experiment(args.exp, args.results, args.out)}")


if __name__ == "__main__":
    main()
