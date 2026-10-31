"""F4-T03: validation points use real queries and held-out surrogate diagnostics."""

import csv
import dataclasses
from pathlib import Path

import pytest

from wafarena import run
from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs.attacker_env import SEND_ACTION, AttackerEnv
from wafarena.envs.backends.fake import FakeBackend
from wafarena.eval import harness


def test_f4_t03_environment_counts_real_sends_across_episodes():
    """F4-T03: the query axis survives episode resets and excludes mutations."""
    env = AttackerEnv(FakeBackend(), defender=ModSecDefender(1), split="train")
    env.reset(seed=0)
    env.step(SEND_ACTION)
    env.reset(seed=1)
    env.step(SEND_ACTION)
    assert env.real_queries_total == 2
    env.close()


def test_f4_t03_run_records_real_query_axis_and_surrogate_metrics(tmp_path, monkeypatch):
    """F4-T03: each validation point reports the query axis and model error."""
    suite = harness.VALIDATION_SUITES["attacker-val-v1"]
    monkeypatch.setitem(
        harness.VALIDATION_SUITES,
        "attacker-val-v1",
        dataclasses.replace(suite, seeds=range(2000, 2002)),
    )
    config = {
        "exp_id": "EXP-H1",
        "run_name": "dyna-0-pl1",
        "seeds": [0],
        "env": {
            "id": "WafArena/Attacker-v0",
            "backend": "fast",
            "defender": {"type": "modsec", "paranoia_level": 1},
            "query_budget": 50,
        },
        "agent": {"algo": "dyna", "params": {"planning_steps": 0}},
        "train": {"total_steps": 30},
        "eval": {"every_steps": 15, "final": False, "surrogate_val_episodes": 2},
        "logging": {"tensorboard": False},
    }
    repo = Path(__file__).parents[2]
    directory = run.run_experiment(
        config,
        results_root=tmp_path,
        repo=repo,
        allow_dirty=True,
        backend=FakeBackend(),
    )[0]
    with (directory / "eval.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert [int(row["step"]) for row in rows] == [15, 30]
    assert int(rows[0]["real_queries"]) <= int(rows[1]["real_queries"])
    assert all(row["simulated_updates"] == "0" for row in rows)
    assert all(0 <= float(row["surrogate_accuracy"]) <= 1 for row in rows)
    assert all(row["surrogate_val_class_counts"] for row in rows)
    assert all(row["surrogate_pred_class_counts"] for row in rows)
    with (directory / "train.csv").open(newline="") as handle:
        train_rows = list(csv.DictReader(handle))
    assert int(rows[-1]["real_queries"]) == sum(int(row["queries_used"]) for row in train_rows)


def test_f4_t03_dyna_requires_validation_budget():
    """F4-T03: the surrogate val sample budget is explicit in the config."""
    from wafarena.runconfig import ConfigError, resolve_config

    with pytest.raises(ConfigError, match="surrogate_val_episodes"):
        resolve_config(
            {
                "exp_id": "EXP-H1",
                "run_name": "dyna-0-pl1",
                "seeds": [0],
                "env": {"id": "WafArena/Attacker-v0"},
                "agent": {"algo": "dyna", "params": {"planning_steps": 0}},
                "train": {"total_steps": 30},
            }
        )
