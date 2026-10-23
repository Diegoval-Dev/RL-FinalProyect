"""F2-T03: results/summary/<exp_id>.csv, one row per run_name and suite, mean with 95 % CI."""

import csv
import json
import math
from pathlib import Path

import pytest
import yaml

from wafarena import summarize


def fake_run(root: Path, run_name: str, seed: int, er: float, qfe: float = math.nan, **meta):
    directory = root / "EXP-D1" / run_name / f"s{seed}"
    directory.mkdir(parents=True)
    suite = {"episodes": 200, "evasion_rate": er, "qfe": qfe, "qfe_c": 40.0, "break_rate": 0.25}
    (directory / "final_eval.json").write_text(
        json.dumps({"best_step": 1, "val": suite, "suites": {"attacker-eval-v1": suite}})
    )
    meta = {"git_sha": "abc1234", "allow_dirty": False, **meta}
    (directory / "meta.yaml").write_text(yaml.safe_dump(meta))


def rows(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def test_summary_has_one_row_per_run_name_and_suite(tmp_path):
    for seed, er in enumerate([0.1, 0.2, 0.3]):
        fake_run(tmp_path, "qlearning", seed, er)
        fake_run(tmp_path, "sarsa", seed, 0.5)
    out = summarize.summarize_experiment("EXP-D1", tmp_path, tmp_path / "summary")
    table = rows(out)
    assert out == tmp_path / "summary" / "EXP-D1.csv"
    assert [(r["run_name"], r["suite"]) for r in table] == [
        ("qlearning", "attacker-eval-v1"),
        ("sarsa", "attacker-eval-v1"),
    ]


def test_mean_and_ci_come_from_the_seeds(tmp_path):
    for seed, er in enumerate([0.1, 0.2, 0.3]):
        fake_run(tmp_path, "qlearning", seed, er)
        fake_run(tmp_path, "sarsa", seed, 0.5)
    table = {
        r["run_name"]: r for r in rows(summarize.summarize_experiment("EXP-D1", tmp_path, tmp_path))
    }
    q = table["qlearning"]
    assert int(q["n_seeds"]) == 3
    assert float(q["evasion_rate_mean"]) == pytest.approx(0.2)
    assert 0.1 <= float(q["evasion_rate_low"]) < 0.2 < float(q["evasion_rate_high"]) <= 0.3
    s = table["sarsa"]
    assert float(s["evasion_rate_low"]) == float(s["evasion_rate_high"]) == pytest.approx(0.5)


def test_nan_seeds_are_skipped_and_all_nan_leaves_blank(tmp_path):
    fake_run(tmp_path, "m", 0, 0.1, qfe=4.0)
    fake_run(tmp_path, "m", 1, 0.0, qfe=math.nan)
    fake_run(tmp_path, "none", 0, 0.0)
    table = {
        r["run_name"]: r for r in rows(summarize.summarize_experiment("EXP-D1", tmp_path, tmp_path))
    }
    assert float(table["m"]["qfe_mean"]) == pytest.approx(4.0)
    assert table["none"]["qfe_mean"] == "" and table["none"]["qfe_low"] == ""


def test_summary_records_provenance(tmp_path):
    fake_run(tmp_path, "m", 0, 0.1, git_sha="aaa1111")
    fake_run(tmp_path, "m", 1, 0.2, git_sha="bbb2222", allow_dirty=True)
    row = rows(summarize.summarize_experiment("EXP-D1", tmp_path, tmp_path))[0]
    assert row["git_shas"] == "aaa1111+bbb2222"
    assert int(row["dirty_runs"]) == 1


def test_summary_is_deterministic(tmp_path):
    for seed, er in enumerate([0.1, 0.4, 0.2]):
        fake_run(tmp_path, "m", seed, er)
    first = summarize.summarize_experiment("EXP-D1", tmp_path, tmp_path / "a").read_text()
    second = summarize.summarize_experiment("EXP-D1", tmp_path, tmp_path / "b").read_text()
    assert first == second


def test_unknown_experiment_without_runs_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="EXP-D1"):
        summarize.summarize_experiment("EXP-D1", tmp_path, tmp_path)


def fake_eval_csv(
    root: Path, run_name: str, seed: int, steps_and_er: list[tuple[int, float]]
) -> None:
    directory = root / "EXP-C1" / run_name / f"s{seed}"
    directory.mkdir(parents=True)
    with (directory / "eval.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["step", "suite", "evasion_rate"])
        for step, er in steps_and_er:
            writer.writerow([step, "attacker-val-v1", er])


def test_load_val_curves_reads_step_and_evasion_rate_per_seed(tmp_path):
    fake_eval_csv(tmp_path, "mc", 0, [(10000, 0.0), (20000, 0.1)])
    fake_eval_csv(tmp_path, "mc", 1, [(10000, 0.05), (20000, 0.2)])
    curves = summarize.load_val_curves("EXP-C1", tmp_path)
    assert set(curves["mc"]) == {0, 1}
    assert curves["mc"][0]["step"].tolist() == [10000, 20000]
    assert curves["mc"][1]["evasion_rate"].tolist() == [0.05, 0.2]
