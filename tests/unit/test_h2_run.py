"""F4-T04: the attacker runner changes defender exactly halfway through EXP-H2."""

import csv
import dataclasses
from pathlib import Path

import pytest

from wafarena import run, runconfig
from wafarena.envs.attacker_env import SEND_ACTION, AttackerEnv
from wafarena.envs.backends.fake import FakeBackend
from wafarena.eval import harness
from wafarena.runconfig import ConfigError, resolve_config


def _config() -> dict:
    return {
        "exp_id": "EXP-H2",
        "run_name": "dyna-switch",
        "seeds": [0],
        "env": {
            "id": "WafArena/Attacker-v0",
            "backend": "fast",
            "defender": {"type": "modsec", "paranoia_level": 1},
            "switch_at": 10,
            "switch_defender": {"type": "checkpoint", "path": "DEF-REF-1"},
            "query_budget": 50,
        },
        "agent": {"algo": "dyna", "params": {"planning_steps": 0}},
        "train": {"total_steps": 20},
        "eval": {"every_steps": 10, "final": False, "surrogate_val_episodes": 2},
        "logging": {"tensorboard": False},
    }


def test_h2_switches_training_defender_after_halfway_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(runconfig, "H2_TOTAL_STEPS", 20)
    monkeypatch.setattr(runconfig, "H2_SWITCH_STEP", 10)
    monkeypatch.setattr(runconfig, "H2_EVAL_STEP", 10)
    suite = harness.VALIDATION_SUITES["attacker-val-v1"]
    monkeypatch.setitem(
        harness.VALIDATION_SUITES,
        "attacker-val-v1",
        dataclasses.replace(suite, seeds=range(2000, 2002)),
    )
    active = []
    actions = []

    def tracking_env(*args, **kwargs):
        env = AttackerEnv(*args, **kwargs)
        real_step = env.step

        def tracked_step(action):
            active.append(type(env._defender).__name__)
            actions.append(action)
            return real_step(action)

        env.step = tracked_step
        return env

    monkeypatch.setattr(run, "AttackerEnv", tracking_env)
    directory = run.run_experiment(
        _config(),
        results_root=tmp_path,
        repo=Path(__file__).parents[2],
        allow_dirty=True,
        backend=FakeBackend(),
    )[0]
    assert active == ["ModSecDefender"] * 10 + ["DefenderDriver"] * 10
    with (directory / "eval.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["defender"] for row in rows] == ["modsec-pl1", "DEF-REF-1"]
    assert [row["phase"] for row in rows] == ["pre", "post"]
    assert [int(row["step"]) for row in rows] == [10, 20]
    assert [int(row["real_queries"]) for row in rows] == [
        sum(action == SEND_ACTION for action in actions[:10]),
        sum(action == SEND_ACTION for action in actions),
    ]


@pytest.mark.parametrize("switch_at", [None, 9, 20])
def test_h2_rejects_missing_or_nonhalfway_switch(switch_at):
    config = _config()
    config["train"]["total_steps"] = 200_000
    config["env"]["switch_at"] = 100_000
    config["eval"]["every_steps"] = 10_000
    if switch_at is None:
        config["env"].pop("switch_at")
        config["env"].pop("switch_defender")
    else:
        config["env"]["switch_at"] = switch_at
    with pytest.raises(ConfigError, match="EXP-H2.*switch"):
        resolve_config(config)


@pytest.mark.parametrize(
    ("steps", "switch", "every"),
    [(20, 10, 10), (200_000, 90_000, 10_000), (200_000, 100_000, 5_000)],
)
def test_h2_requires_exact_experiment_schedule(steps, switch, every):
    config = _config()
    config["train"]["total_steps"] = steps
    config["env"]["switch_at"] = switch
    config["eval"]["every_steps"] = every
    with pytest.raises(ConfigError, match="EXP-H2"):
        resolve_config(config)
