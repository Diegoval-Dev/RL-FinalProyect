"""F2-T04: DefenderEnv can draw attacks from another split and pin its session on reset."""

import json

import pytest

from wafarena.envs.backends.fake import FakeBackend
from wafarena.envs.defender_env import DefenderEnv
from wafarena.splits.builder import SPLITS_PATH

SPLITS = json.loads(SPLITS_PATH.read_text())


def make_env(**kwargs) -> DefenderEnv:
    return DefenderEnv(backend=FakeBackend(), attack_ratio=0.5, **kwargs)


def attack_base_ids(env: DefenderEnv) -> set[str]:
    return {base.base_id for base in env._bases}


def test_attack_split_defaults_to_split():
    assert attack_base_ids(make_env(split="test")) == set(SPLITS["payloads"]["test"])


def test_attack_split_draws_attacks_from_another_split():
    env = make_env(split="test", attack_split="test-family")
    assert attack_base_ids(env) == set(SPLITS["payloads"]["test-family"])


def test_hard_benign_split_can_be_combined_with_test_attacks():
    env = make_env(split="test-hard", attack_split="test")
    assert attack_base_ids(env) == set(SPLITS["payloads"]["test"])
    assert {s["session_id"] for s in env._benign} == set(SPLITS["benign"]["test-hard"])


def test_reset_with_base_id_forces_that_attack_session():
    base_id = sorted(SPLITS["payloads"]["test"])[3]
    env = make_env(split="test")
    _obs, info = env.reset(seed=0, options={"base_id": base_id})
    assert info["session_id"] == f"atk-{base_id}"
    assert info["gt_label"] == "attack"


def test_reset_with_session_id_forces_that_benign_session():
    session_id = sorted(SPLITS["benign"]["test"])[5]
    env = make_env(split="test")
    _obs, info = env.reset(seed=0, options={"session_id": session_id})
    assert info["session_id"] == session_id
    assert info["gt_label"] == "benign"


def test_reset_rejects_unknown_or_conflicting_options():
    env = make_env(split="test")
    with pytest.raises(ValueError, match="no-such"):
        env.reset(seed=0, options={"base_id": "no-such"})
    with pytest.raises(ValueError, match="no-such"):
        env.reset(seed=0, options={"session_id": "no-such"})
    with pytest.raises(ValueError, match="both"):
        env.reset(seed=0, options={"base_id": "x", "session_id": "y"})


def test_pinned_reset_is_deterministic():
    base_id = sorted(SPLITS["payloads"]["test"])[0]

    def rollout() -> list[float]:
        env = make_env(split="test", attacker="random_mutation")
        env.reset(seed=4, options={"base_id": base_id})
        rewards, done = [], False
        while not done:
            _o, reward, terminated, truncated, _i = env.step(1)
            rewards.append(reward)
            done = terminated or truncated
        return rewards

    assert rollout() == rollout()
