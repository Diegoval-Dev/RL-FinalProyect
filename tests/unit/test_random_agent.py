"""F2-T03: the untrained random attacker baseline (used by the runner and by RQ1's comparison)."""

import numpy as np

from wafarena.agents import build_agent, load_checkpoint, save_checkpoint
from wafarena.envs.attacker_env import N_ACTIONS


def make(seed: int = 0):
    return build_agent("random", {}, obs_dim=288, n_actions=N_ACTIONS, seed=seed, agent_id="rnd")


def actions(agent, n=50):
    return [agent.act(np.zeros(288), {}, explore=False) for _ in range(n)]


def test_random_agent_acts_uniformly_over_valid_actions():
    taken = actions(make(), n=2000)
    assert set(taken) == set(range(N_ACTIONS))


def test_random_agent_is_deterministic_given_seed():
    assert actions(make(1)) == actions(make(1))
    assert actions(make(1)) != actions(make(2))


def test_random_agent_does_not_learn():
    agent = make()
    assert agent.observe(None) == {}


def test_random_agent_checkpoint_round_trip(tmp_path):
    save_checkpoint(make(3), tmp_path / "ck", algo="random", obs_dim=288, n_actions=N_ACTIONS)
    loaded = load_checkpoint(tmp_path / "ck")
    assert loaded.agent_id == "rnd" and loaded.role == "attacker"
    assert set(actions(loaded, n=2000)) == set(range(N_ACTIONS))
