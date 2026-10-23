"""F2-T05: results/summary/EXP-A1.csv and EXP-A2.csv from finished bandit runs."""

import csv
import json
from pathlib import Path

import pytest
import yaml

from wafarena import bandit_summarize


def fake_run(root: Path, run_name: str, seed: int, er: float, **meta):
    directory = root / "EXP-A1" / run_name / f"s{seed}"
    directory.mkdir(parents=True)
    suite = {"episodes": 200, "evasion_rate": er, "break_rate": 0.2}
    (directory / "final_eval.json").write_text(json.dumps({"suites": {"attacker-eval-v1": suite}}))
    rows = [{"step": s, "regret_cumulative": float(s)} for s in (1, 2, 3)]
    with (directory / "pulls.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (directory / "meta.yaml").write_text(
        yaml.safe_dump({"git_sha": "abc1234", "allow_dirty": False, **meta})
    )


def rows(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def test_summary_has_one_row_per_run_name_with_mean_ci(tmp_path):
    for seed, er in enumerate([0.0, 0.0, 0.0]):
        fake_run(tmp_path, "greedy-pl1", seed, er)
    out = bandit_summarize.summarize_experiment("EXP-A1", tmp_path, tmp_path / "summary")
    table = rows(out)
    assert out == tmp_path / "summary" / "EXP-A1.csv"
    assert table[0]["run_name"] == "greedy-pl1"
    assert int(table[0]["n_seeds"]) == 3
    assert float(table[0]["evasion_rate_mean"]) == pytest.approx(0.0)


def test_unknown_experiment_without_runs_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="EXP-A1"):
        bandit_summarize.summarize_experiment("EXP-A1", tmp_path, tmp_path)


def test_regret_curves_collects_the_final_cumulative_regret_per_seed(tmp_path):
    for seed in (0, 1, 2):
        fake_run(tmp_path, "greedy-pl1", seed, 0.0)
    curves = bandit_summarize.load_regret_curves("EXP-A1", tmp_path)
    assert set(curves["greedy-pl1"]) == {0, 1, 2}
    assert curves["greedy-pl1"][0]["step"].tolist() == [1, 2, 3]
    assert curves["greedy-pl1"][0]["regret_cumulative"].tolist() == [1.0, 2.0, 3.0]
