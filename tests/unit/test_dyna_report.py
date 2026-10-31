"""F4-T03: EXP-H1 query-axis summary from complete clean runs."""

import csv

import pytest
import yaml

from wafarena.agents.dyna.report import DEFENDERS, METHODS, summarize_h1


@pytest.fixture
def complete_runs(tmp_path):
    for defender in DEFENDERS:
        for method in METHODS:
            run_name = f"{method}-{defender}"
            for seed in range(5 if method == "ppo" else 10):
                path = tmp_path / "EXP-H1" / run_name / f"s{seed}"
                path.mkdir(parents=True)
                (path / "meta.yaml").write_text(
                    yaml.safe_dump(
                        {
                            "exp_id": "EXP-H1",
                            "run_id": f"EXP-H1__{run_name}__s{seed}__abc1234",
                            "git_sha": "abc1234",
                            "seed": seed,
                            "dirty": False,
                        }
                    )
                )
                with (path / "eval.csv").open("w", newline="") as handle:
                    writer = csv.DictWriter(
                        handle,
                        fieldnames=[
                            "suite",
                            "real_queries",
                            "evasion_rate",
                            "surrogate_accuracy",
                            "surrogate_minority_recall",
                        ],
                    )
                    writer.writeheader()
                    for queries, er in ((10 + seed, 0.0), (20 + seed, 0.1)):
                        writer.writerow(
                            {
                                "suite": "attacker-val-v1",
                                "real_queries": queries,
                                "evasion_rate": er,
                                "surrogate_accuracy": 0.8,
                                "surrogate_minority_recall": 0.2,
                            }
                        )
    return tmp_path


def test_f4_t03_report_uses_shared_real_query_range_and_seed_counts(complete_runs):
    """F4-T03: curves interpolate only where all required seeds have observations."""
    rows = summarize_h1(complete_runs)
    assert len(rows) == 2 * 5 * 21
    dyna = [r for r in rows if r["defender"] == "pl1" and r["method"] == "dyna-5"]
    assert dyna[0]["real_queries"] == 19
    assert dyna[-1]["real_queries"] == 20
    assert all(r["seeds"] == 10 for r in dyna)
    assert all(r["surrogate_accuracy_mean"] == pytest.approx(0.8) for r in dyna)
    assert len(dyna[0]["run_ids"].split()) == 10
    ppo = [r for r in rows if r["defender"] == "pl1" and r["method"] == "ppo"]
    assert all(r["seeds"] == 5 for r in ppo)


def test_f4_t03_report_rejects_dirty_source_run(complete_runs):
    """F4-T03: reported curves cannot include dirty experiment runs."""
    path = complete_runs / "EXP-H1" / "qlearning-pl1" / "s0" / "meta.yaml"
    meta = yaml.safe_load(path.read_text())
    meta["dirty"] = True
    path.write_text(yaml.safe_dump(meta))
    with pytest.raises(ValueError, match="provenance"):
        summarize_h1(complete_runs)
