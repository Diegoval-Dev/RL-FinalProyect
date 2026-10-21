"""F1-T12: both environments run a short rollout against the real FastBackend."""

import numpy as np
import pytest

import wafarena.envs  # noqa: F401
from wafarena.envs.attacker_env import AttackerEnv
from wafarena.envs.backends import FastBackend
from wafarena.envs.defender_env import DefenderEnv

pytestmark = pytest.mark.lab

ROLLOUT_STEPS = 15


def test_attacker_env_runs_against_real_backend():
    env = AttackerEnv(backend=FastBackend(), split="train")
    rng = np.random.default_rng(0)
    obs, info = env.reset(seed=0)
    assert obs.shape == (288,)
    for _ in range(ROLLOUT_STEPS):
        obs, reward, terminated, truncated, info = env.step(int(rng.integers(17)))
        assert 0 <= info["abstract_state"] < 120
        if terminated or truncated:
            break


def test_defender_env_runs_against_real_backend():
    env = DefenderEnv(backend=FastBackend(), split="train", attack_ratio=0.5)
    rng = np.random.default_rng(1)
    obs, info = env.reset(seed=1)
    assert obs.shape == (37,)
    assert info["gt_label"] in ("attack", "benign")
    for _ in range(ROLLOUT_STEPS):
        obs, reward, terminated, truncated, info = env.step(int(rng.integers(5)))
        if terminated or truncated:
            break
