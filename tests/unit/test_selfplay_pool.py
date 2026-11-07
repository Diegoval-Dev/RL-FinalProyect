"""F4-T05: opponent choices remain seeded and fixed within each attack episode."""

from collections import Counter

import numpy as np
import pytest

from wafarena.envs.backends.fake import FakeBackend
from wafarena.selfplay.pool import PoolAttackerEnv, choose_opponent


def test_choose_opponent_uses_half_current_and_uniform_history():
    rng = np.random.default_rng(17)
    choices = Counter(
        choose_opponent(rng, "current", ["old-1", "old-2"], current_probability=0.5)
        for _ in range(10_000)
    )
    assert 0.47 < choices["current"] / 10_000 < 0.53
    assert 0.22 < choices["old-1"] / 10_000 < 0.28
    assert 0.22 < choices["old-2"] / 10_000 < 0.28


def test_first_generation_always_uses_current_and_rejects_bad_probability():
    rng = np.random.default_rng(3)
    assert {choose_opponent(rng, "current", [], current_probability=0.5) for _ in range(30)} == {
        "current"
    }
    with pytest.raises(ValueError, match="probability"):
        choose_opponent(rng, "current", ["old"], current_probability=1.5)


def test_attacker_env_selects_once_per_episode(monkeypatch):
    selected = []
    monkeypatch.setattr(
        "wafarena.selfplay.pool.resolve_defender",
        lambda spec: selected.append(spec["path"]) or object(),
    )
    env = PoolAttackerEnv(
        FakeBackend(),
        current_defender="current",
        historical_defenders=["old"],
        current_probability=0.5,
        split="train",
    )
    env.reset(seed=11)
    assert len(selected) == 1
    assert env.selected_defender == selected[0]
    env.reset(seed=11)
    assert env.selected_defender == selected[0]
    assert selected == [env.selected_defender]  # reuses the loaded DQN policy
