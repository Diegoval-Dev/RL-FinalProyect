"""F2-T06: results/summary/EXP-B1.csv and the convergence table from finished DP runs."""

import csv
import json
from pathlib import Path

import pytest
import yaml

from wafarena import dp_summarize


def fake_run(root: Path, seed: int, er: float, vi_it: int, pi_it: int, agree: bool) -> None:
    directory = root / "EXP-B1" / "toy" / f"s{seed}"
    directory.mkdir(parents=True)
    suite = {"episodes": 200, "evasion_rate": er, "break_rate": 0.1}
    (directory / "final_eval.json").write_text(json.dumps({"suites": {"attacker-eval-v1": suite}}))
    summary = {
        "n_transitions": 200000,
        "value_iteration": {"iterations": vi_it, "seconds": 0.2},
        "policy_iteration": {"iterations": pi_it, "seconds": 0.1},
        "policies_agree": agree,
        "max_value_diff": 0.0 if agree else 1e-4,
    }
    (directory / "model_summary.json").write_text(json.dumps(summary))
    (directory / "meta.yaml").write_text(
        yaml.safe_dump({"git_sha": "abc1234", "allow_dirty": False})
    )


def rows(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def test_summarize_reports_mean_ci_and_convergence(tmp_path):
    for seed, (er, vi, pi, agree) in enumerate(
        [(0.0, 10, 3, True), (0.0, 12, 4, True), (0.0, 9, 3, False)]
    ):
        fake_run(tmp_path, seed, er, vi, pi, agree)
    out = dp_summarize.summarize_experiment("EXP-B1", tmp_path, tmp_path / "summary")
    table = rows(out)
    assert out == tmp_path / "summary" / "EXP-B1.csv"
    assert len(table) == 1
    row = table[0]
    assert int(row["n_seeds"]) == 3
    assert float(row["evasion_rate_mean"]) == pytest.approx(0.0)
    assert float(row["vi_iterations_mean"]) == pytest.approx((10 + 12 + 9) / 3)
    assert float(row["pi_iterations_mean"]) == pytest.approx((3 + 4 + 3) / 3)
    assert int(row["seeds_policies_agree"]) == 2
    assert int(row["n_seeds"]) - int(row["seeds_policies_agree"]) == 1


def test_unknown_experiment_without_runs_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="EXP-B1"):
        dp_summarize.summarize_experiment("EXP-B1", tmp_path, tmp_path)
