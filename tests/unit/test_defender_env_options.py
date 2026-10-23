"""F2-T04: DefenderEnv can draw attacks from another split and pin its session on reset."""

import json

import numpy as np
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


def test_checkpoint_attacker_drives_attacks_via_attacker_driver(tmp_path):
    from wafarena.agents.base import save_checkpoint
    from wafarena.agents.dp import DPPolicyAgent
    from wafarena.envs.abstract_state import N_STATES
    from wafarena.envs.attacker_env import N_ACTIONS, SEND_ACTION
    from wafarena.envs.attacker_obs import OBS_SIZE

    policy = np.full(N_STATES, SEND_ACTION, dtype=int)  # always send unmutated
    save_checkpoint(
        DPPolicyAgent("ATK-TEST", policy),
        tmp_path / "ck",
        algo="dp",
        obs_dim=OBS_SIZE,
        n_actions=N_ACTIONS,
    )
    env = DefenderEnv(
        backend=FakeBackend(),
        attacker={"type": "checkpoint", "path": str(tmp_path / "ck")},
        split="test",
        attack_ratio=1.0,
    )
    base_id = sorted(SPLITS["payloads"]["test"])[0]
    obs, info = env.reset(seed=0, options={"base_id": base_id})
    assert info["gt_label"] == "attack"
    env.step(0)  # must not raise: the checkpoint-driven attacker answered a real request


def test_checkpoint_attacker_is_reused_across_episodes(tmp_path):
    """The same loaded checkpoint must drive a fresh episode each reset, not error out the
    second time (AttackerDriver.reset() must fully clear the previous episode's state)."""
    from wafarena.agents.base import save_checkpoint
    from wafarena.agents.dp import DPPolicyAgent
    from wafarena.envs.abstract_state import N_STATES
    from wafarena.envs.attacker_env import N_ACTIONS, SEND_ACTION
    from wafarena.envs.attacker_obs import OBS_SIZE

    policy = np.full(N_STATES, SEND_ACTION, dtype=int)
    save_checkpoint(
        DPPolicyAgent("ATK-TEST", policy),
        tmp_path / "ck",
        algo="dp",
        obs_dim=OBS_SIZE,
        n_actions=N_ACTIONS,
    )
    env = DefenderEnv(
        backend=FakeBackend(),
        attacker={"type": "checkpoint", "path": str(tmp_path / "ck")},
        split="test",
        attack_ratio=1.0,
    )
    for base_id in sorted(SPLITS["payloads"]["test"])[:3]:
        env.reset(seed=0, options={"base_id": base_id})
        env.step(0)
