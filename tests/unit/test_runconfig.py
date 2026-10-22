"""F2-T03: experiment YAML validation (experimentos.md, Configuración YAML)."""

import copy
from pathlib import Path

import pytest
import yaml

from wafarena.runconfig import ConfigError, catalog_ids, load_config, resolve_config

VALID = {
    "exp_id": "EXP-D1",
    "run_name": "qlearning-pl1",
    "owner": "daniel",
    "rq": ["RQ1"],
    "seeds": [0, 1, 2],
    "env": {
        "id": "WafArena/Attacker-v0",
        "backend": "fast",
        "split": "train",
        "defender": {"type": "modsec", "paranoia_level": 1},
        "query_budget": 50,
    },
    "agent": {"algo": "qlearning", "params": {"alpha": 0.1, "gamma": 0.99}},
    "train": {"total_steps": 200000},
    "eval": {"suites": ["attacker-eval-v1"], "every_steps": 10000, "final": True},
    "logging": {"tensorboard": True, "wandb": False},
    "checkpoint": {"save_best_on": "val"},
}


def config(**overrides):
    raw = copy.deepcopy(VALID)
    for dotted, value in overrides.items():
        *parents, leaf = dotted.split("__")
        node = raw
        for key in parents:
            node = node[key]
        if value is KeyError:
            del node[leaf]
        else:
            node[leaf] = value
    return raw


def test_catalog_ids_lists_experiments_and_ablations():
    ids = catalog_ids()
    assert {"EXP-A1", "EXP-D1", "EXP-G3", "EXP-R1", "ABL-1", "ABL-2"} <= ids


def test_valid_config_resolves_unchanged_fields():
    resolved = resolve_config(VALID)
    assert resolved["exp_id"] == "EXP-D1" and resolved["seeds"] == [0, 1, 2]
    assert resolved["agent"]["params"]["alpha"] == 0.1


def test_defaults_are_expanded():
    minimal = {
        "exp_id": "EXP-D1",
        "run_name": "q",
        "seeds": [0],
        "env": {"id": "WafArena/Attacker-v0"},
        "agent": {"algo": "qlearning"},
        "train": {"total_steps": 100},
    }
    resolved = resolve_config(minimal)
    assert resolved["env"]["backend"] == "fast"
    assert resolved["env"]["split"] == "train"
    assert resolved["env"]["defender"] == {"type": "modsec", "paranoia_level": 1}
    assert resolved["env"]["query_budget"] == 50
    assert resolved["agent"]["params"] == {}
    assert resolved["eval"] == {"suites": ["attacker-eval-v1"], "every_steps": 10000, "final": True}
    assert resolved["logging"] == {"tensorboard": True, "wandb": False}
    assert resolved["checkpoint"] == {"save_best_on": "val"}


def test_resolve_does_not_mutate_the_input():
    raw = copy.deepcopy(VALID)
    resolve_config(raw)
    assert raw == VALID


@pytest.mark.parametrize("split", ["test", "test-family", "test-hard"])
def test_test_splits_are_rejected_for_training(split):
    with pytest.raises(ConfigError, match="train"):
        resolve_config(config(env__split=split))


def test_validation_split_is_rejected_for_training():
    with pytest.raises(ConfigError, match="train"):
        resolve_config(config(env__split="val"))


def test_unknown_exp_id_is_rejected():
    with pytest.raises(ConfigError, match="EXP-ZZ"):
        resolve_config(config(exp_id="EXP-ZZ"))


@pytest.mark.parametrize("key", ["exp_id", "run_name", "seeds", "env", "agent", "train"])
def test_missing_required_sections_are_rejected(key):
    with pytest.raises(ConfigError, match=key):
        resolve_config(config(**{key: KeyError}))


def test_unknown_keys_are_rejected_to_catch_typos():
    with pytest.raises(ConfigError, match="sedes"):
        resolve_config({**VALID, "sedes": [1]})
    with pytest.raises(ConfigError, match="alfa"):
        resolve_config(config(train__alfa=1))


@pytest.mark.parametrize("seeds", [[], [1, 1], ["a"], [1.5], "0"])
def test_seeds_must_be_a_nonempty_list_of_distinct_ints(seeds):
    with pytest.raises(ConfigError, match="seeds"):
        resolve_config(config(seeds=seeds))


@pytest.mark.parametrize("name", ["", "has space", "../escape", "a/b"])
def test_run_name_must_be_a_safe_slug(name):
    with pytest.raises(ConfigError, match="run_name"):
        resolve_config(config(run_name=name))


def test_total_steps_must_be_positive():
    with pytest.raises(ConfigError, match="total_steps"):
        resolve_config(config(train__total_steps=0))


def test_unknown_environment_and_backend_are_rejected():
    with pytest.raises(ConfigError, match="env.id"):
        resolve_config(config(env__id="WafArena/Other-v0"))
    with pytest.raises(ConfigError, match="backend"):
        resolve_config(config(env__backend="turbo"))


def test_checkpoint_selection_must_use_validation():
    with pytest.raises(ConfigError, match="save_best_on"):
        resolve_config(config(checkpoint__save_best_on="test"))


def test_unknown_eval_suite_is_rejected():
    with pytest.raises(ConfigError, match="no-such-suite"):
        resolve_config(config(eval__suites=["no-such-suite"]))


def test_wandb_is_not_supported_yet():
    with pytest.raises(ConfigError, match="wandb"):
        resolve_config(config(logging__wandb=True))


def test_load_config_reads_yaml(tmp_path: Path):
    path = tmp_path / "exp.yaml"
    path.write_text(yaml.safe_dump(VALID))
    assert load_config(path)["run_name"] == "qlearning-pl1"


def test_load_config_rejects_non_mapping(tmp_path: Path):
    path = tmp_path / "exp.yaml"
    path.write_text("- just\n- a list\n")
    with pytest.raises(ConfigError):
        load_config(path)


def test_every_committed_experiment_config_is_valid():
    root = Path(__file__).parents[2] / "configs" / "exp"
    for path in sorted(root.rglob("*.yaml")):
        assert load_config(path)["exp_id"] in catalog_ids(), path
