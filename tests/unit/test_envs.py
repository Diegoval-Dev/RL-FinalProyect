"""F1-T12: both environments pass the Gymnasium checker and are deterministic."""

import gymnasium as gym
import pytest
from gymnasium.utils.env_checker import check_env

import wafarena.envs  # noqa: F401  (registers the envs)
from wafarena.envs.attacker_env import AttackerEnv
from wafarena.envs.backends.fake import FakeBackend
from wafarena.envs.defender_env import DefenderEnv


def attacker_env() -> AttackerEnv:
    return AttackerEnv(backend=FakeBackend(), split="train")


def defender_env() -> DefenderEnv:
    return DefenderEnv(backend=FakeBackend(), split="train", attack_ratio=0.5)


def test_attacker_env_passes_gymnasium_checker():
    check_env(attacker_env(), skip_render_check=True)


def test_defender_env_passes_gymnasium_checker():
    check_env(defender_env(), skip_render_check=True)


def test_attacker_observation_and_action_spaces():
    env = attacker_env()
    assert env.observation_space.shape == (288,)
    assert env.action_space.n == 17


def test_defender_observation_and_action_spaces():
    env = defender_env()
    assert env.observation_space.shape == (37,)
    assert env.action_space.n == 5


def _rollout(env_factory, seed: int, actions: list[int]) -> list[float]:
    env = env_factory()
    env.reset(seed=seed)
    rewards = []
    for action in actions:
        _obs, reward, terminated, truncated, _info = env.step(action)
        rewards.append(reward)
        if terminated or truncated:
            break
    return rewards


def test_attacker_env_is_deterministic_given_seed():
    actions = [0, 1, 2, 16]
    assert _rollout(attacker_env, 7, actions) == _rollout(attacker_env, 7, actions)


def test_defender_env_is_deterministic_given_seed():
    actions = [0, 1, 0, 1]
    assert _rollout(defender_env, 11, actions) == _rollout(defender_env, 11, actions)


def test_make_via_gymnasium_registry():
    env = gym.make("WafArena/Attacker-v0", backend=FakeBackend())
    env.reset(seed=0)
    assert env.observation_space.shape == (288,)


def first_reward(attack_ratio: float, action: int, seed: int = 0) -> float:
    env = DefenderEnv(backend=FakeBackend(), split="train", attack_ratio=attack_ratio)
    env.reset(seed=seed)
    _obs, reward, _term, _trunc, info = env.step(action)
    return reward, info["gt_label"], info["gt_effect"]


@pytest.mark.parametrize(
    ("action", "expected"),
    [(0, 0.0), (1, -4.0), (2, -1.0), (3, -0.5), (4, -4.0)],
    ids=["allow", "block", "captcha", "rate_limit", "honeypot"],
)
def test_defender_reward_table_for_benign(action, expected):
    reward, label, effect = first_reward(attack_ratio=0.0, action=action)
    assert label == "benign"
    assert reward == expected


@pytest.mark.parametrize(
    ("action", "expected"),
    [(0, -10.0), (1, 5.0), (2, 3.0), (3, 2.0), (4, 6.0)],
    ids=["allow", "block", "captcha", "rate_limit", "honeypot"],
)
def test_defender_reward_table_for_attack_with_effect(action, expected):
    reward, label, effect = first_reward(attack_ratio=1.0, action=action)
    assert label == "attack"
    assert effect is True
    assert reward == expected


class _BreakingBackend(FakeBackend):
    """Every mutation breaks the payload (functional=False), to exercise the revert path."""

    def check_functional(self, payload, endpoint, param):
        from wafarena.oracle import OracleResult

        return OracleResult(False, False, "syntax_error", "forced break")


def test_attacker_broken_mutation_reverts_and_penalizes():
    env = AttackerEnv(backend=_BreakingBackend(), split="train")
    env.reset(seed=3, options={"base_id": env._bases[0].base_id})
    before = env._payload.text

    _obs, reward, _term, _trunc, info = env.step(0)  # an operator that applies

    if info["broken"]:
        assert reward == pytest.approx(-5.1)
        assert env._payload.text == before


def test_attacker_info_hides_nothing_required_and_marks_ground_truth():
    env = AttackerEnv(backend=FakeBackend(), split="train")
    _obs, info = env.reset(seed=1)
    assert "abstract_state" in info and 0 <= info["abstract_state"] < 120
    _obs, _r, _t, _tr, info = env.step(16)  # SEND
    assert "gt_defender_action" in info and "gt_oracle" in info
