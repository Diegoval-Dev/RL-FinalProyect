"""F4-T04: EXP-H2 curves and recovery queries require complete provenance."""

import csv
from pathlib import Path

import pytest
import yaml

from wafarena.agents.dyna.h2_report import METHODS, summarize_h2
from wafarena.runconfig import load_config


@pytest.fixture
def complete_runs(tmp_path):
    for method in METHODS:
        for seed in range(10):
            path = tmp_path / "EXP-H2" / method / f"s{seed}"
            path.mkdir(parents=True)
            (path / "meta.yaml").write_text(
                yaml.safe_dump(
                    {
                        "exp_id": "EXP-H2",
                        "run_name": method,
                        "run_id": f"EXP-H2__{method}__s{seed}__abc1234",
                        "seed": seed,
                        "git_sha": "abc1234",
                        "dirty": False,
                        "duration_s": 1.0,
                    }
                )
            )
            (path / "config.resolved.yaml").write_text(
                yaml.safe_dump(
                    {
                        **load_config(
                            Path(__file__).parents[2]
                            / "configs"
                            / "exp"
                            / "EXP-H2"
                            / f"{method}.yaml"
                        ),
                        "seeds": [seed],
                    }
                )
            )
            with (path / "eval.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "step",
                        "suite",
                        "defender",
                        "phase",
                        "real_queries",
                        "evasion_rate",
                    ],
                )
                writer.writeheader()
                for step in range(10000, 200001, 10000):
                    writer.writerow(
                        {
                            "step": step,
                            "suite": "attacker-val-v1",
                            "defender": "modsec-pl1" if step <= 100000 else "DEF-REF-1",
                            "phase": "pre" if step <= 100000 else "post",
                            "real_queries": step // 1000 + seed,
                            "evasion_rate": 0.4 if step <= 100000 or step >= 120000 else 0.1,
                        }
                    )
    return tmp_path


def test_h2_curves_align_switch_at_zero_real_queries(complete_runs):
    curve, recovery = summarize_h2(complete_runs)
    assert len(curve) == 3 * 21
    assert len(recovery) == 30
    dyna = [row for row in curve if row["method"] == "dyna-20-switch"]
    assert dyna[0]["relative_queries"] == pytest.approx(-90)
    assert dyna[10]["relative_queries"] == pytest.approx(0)
    assert dyna[11]["relative_queries"] == pytest.approx(10)
    assert dyna[-1]["relative_queries"] == pytest.approx(100)
    assert dyna[10]["er_mean"] == pytest.approx(0.4)
    assert dyna[11]["er_mean"] == pytest.approx(0.1)
    assert len(dyna[0]["run_ids"].split()) == 10
    assert recovery[0]["status"] == "recovered"
    assert recovery[0]["recovery_queries"] == 20


def test_h2_zero_baseline_is_not_reported_as_instant_recovery(complete_runs):
    path = complete_runs / "EXP-H2" / "dyna-20-switch" / "s0" / "eval.csv"
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[9]["evasion_rate"] = "0.0"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    _, recovery = summarize_h2(complete_runs)
    assert recovery[0]["status"] == "baseline_zero"
    assert recovery[0]["recovery_queries"] == ""


def test_h2_report_rejects_mixed_revisions(complete_runs):
    path = complete_runs / "EXP-H2" / "dyna-20-switch" / "s0" / "meta.yaml"
    meta = yaml.safe_load(path.read_text())
    meta["git_sha"] = "def5678"
    meta["run_id"] = "EXP-H2__dyna-20-switch__s0__def5678"
    path.write_text(yaml.safe_dump(meta))
    with pytest.raises(ValueError, match="different code revisions"):
        summarize_h2(complete_runs)


@pytest.mark.parametrize(
    ("section", "path", "value"),
    [
        ("agent", ("algo",), "dyna_plus"),
        ("agent", ("params", "planning_steps"), 5),
        ("env", ("backend",), "real"),
        ("eval", ("every_steps",), 5_000),
    ],
)
def test_h2_report_rejects_mislabeled_settings(complete_runs, section, path, value):
    config_path = complete_runs / "EXP-H2" / "dyna-20-switch" / "s0" / "config.resolved.yaml"
    config = yaml.safe_load(config_path.read_text())
    target = config[section]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    config_path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="invalid EXP-H2 provenance"):
        summarize_h2(complete_runs)
