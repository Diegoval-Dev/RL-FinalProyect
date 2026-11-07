"""F4-T05: reject invalid self-play runs before allocating results or checkpoints."""

import copy

import pytest

from wafarena.selfplay.config import SelfPlayConfigError, validate_config

GOOD = {
    "exp_id": "F4-T05",
    "run_name": "smoke",
    "seeds": [0],
    "backend": "fast",
    "generations": 2,
    "attacker": {
        "initial_checkpoint": "checkpoints/refs/ATK-REF-1",
        "iterations_per_generation": 3,
        "steps_per_iteration": 4,
        "env": {"split": "train", "query_budget": 5, "max_steps": 10},
    },
    "defender": {
        "initial_checkpoint": "checkpoints/refs/DEF-REF-1",
        "steps_per_generation": 4,
        "env": {"split": "train", "attack_ratio": 0.5},
    },
    "pool": {"current_probability": 0.5},
    "validation": {
        "attacker_episodes": 2,
        "defender_sessions": 4,
        "attacker_defenders": ["modsec-pl1", "modsec-pl2", "modsec-pl3", "modsec-pl4", "DEF-REF-1"],
        "defender_attackers": ["corpus-replay", "random-mutation", "ATK-REF-0", "ATK-REF-1"],
    },
    "logging": {"tensorboard": False},
}


def test_valid_config_keeps_explicit_training_budget():
    assert validate_config(copy.deepcopy(GOOD))["attacker"]["steps_per_iteration"] == 4


def test_runner_can_be_reused_for_exp_i1():
    raw = copy.deepcopy(GOOD)
    raw["exp_id"] = "EXP-I1"
    assert validate_config(raw)["exp_id"] == "EXP-I1"


def test_rejects_swapped_initial_checkpoint_roles():
    raw = copy.deepcopy(GOOD)
    raw["attacker"]["initial_checkpoint"] = GOOD["defender"]["initial_checkpoint"]
    with pytest.raises(SelfPlayConfigError, match="role"):
        validate_config(raw)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("generations",), 0),
        (("attacker", "iterations_per_generation"), 2),
        (("attacker", "steps_per_iteration"), 0),
        (("pool", "current_probability"), -0.1),
        (("defender", "env", "split"), "test"),
        (("seeds",), [0, 0]),
        (("validation", "attacker_defenders"), []),
        (("validation", "attacker_defenders"), ["modsec-pl1", "DEF-REF-1"]),
        (
            ("validation", "attacker_defenders"),
            [*GOOD["validation"]["attacker_defenders"], "modsec-pl1"],
        ),
    ],
)
def test_invalid_protocol_is_rejected(path, value):
    raw = copy.deepcopy(GOOD)
    parent = raw
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    with pytest.raises(SelfPlayConfigError):
        validate_config(raw)
