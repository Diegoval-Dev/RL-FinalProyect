import csv
from pathlib import Path

import pytest

from dashboard.data import load_results

HEADERS = {
    "EXP-I1_curve.csv": [
        "condition",
        "generation",
        "role",
        "reference",
        "metric",
        "mean",
        "git_sha",
    ],
    "EXP-H1.csv": ["defender", "method", "real_queries", "er_mean", "git_shas"],
    "EXP-I2_matrix.csv": [
        "defender_generation",
        "attacker_generation",
        "mean_er",
        "source_git_sha",
        "eval_git_sha",
    ],
    "RQ5_final.csv": ["exp_id", "attacker", "defender", "tpr", "fpr", "er_d", "eval_run_ids"],
    "EXP-R1_gap.csv": [
        "role",
        "agent",
        "metric",
        "gap_mean",
        "n_defined",
        "fast_run_ids",
        "real_run_ids",
    ],
}


def _write(path, fields, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_loader_rejects_missing_source_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="EXP-I1_curve"):
        load_results(tmp_path)


def test_loader_rejects_wrong_source_sha(tmp_path):
    for name, fields in HEADERS.items():
        row = dict.fromkeys(fields, "1")
        if name == "EXP-I1_curve.csv":
            row.update(
                condition="pool",
                generation="1",
                role="defender",
                reference="ATK-REF-1",
                metric="tpr",
                mean="0.8",
                git_sha="wrong",
            )
        if name == "EXP-I2_matrix.csv":
            row.update(
                defender_generation="1",
                attacker_generation="1",
                mean_er="0.0",
                source_git_sha="eea6f78",
                eval_git_sha="85524f0",
            )
        _write(tmp_path / name, fields, [row])
    with pytest.raises(ValueError, match="EXP-I1.*source"):
        load_results(tmp_path)


def test_loader_rejects_incomplete_crossplay_matrix(tmp_path):
    for name, fields in HEADERS.items():
        row = dict.fromkeys(fields, "1")
        if name == "EXP-I1_curve.csv":
            row.update(
                condition="pool",
                generation="1",
                role="defender",
                reference="ATK-REF-1",
                metric="tpr",
                mean="0.8",
                git_sha="eea6f78",
            )
        if name == "EXP-I2_matrix.csv":
            row.update(
                defender_generation="1",
                attacker_generation="1",
                mean_er="0.0",
                source_git_sha="eea6f78",
                eval_git_sha="85524f0",
            )
        _write(tmp_path / name, fields, [row])
    with pytest.raises(ValueError, match="64 cells"):
        load_results(tmp_path)


def test_loader_accepts_published_summary_files():
    results = load_results(Path("results/summary"))
    assert len(results["EXP-I2_matrix.csv"]) == 64
