"""F2-T07: on-policy Monte Carlo control, epsilon-soft, first-visit and every-visit (EXP-C1).

Drives the agent through hand-constructed episodes (not a real env): state 0 is visited twice in
one episode, with actions 1 and 2 giving rewards 4 and 1 respectively, then state 0/action 1 is
visited again later in the SAME episode with reward 0, before the episode ends. With gamma=1:
  - first-visit must use only the EARLIEST return for (0, 1): G = 4 + 1 + 0 = 5.
  - every-visit must average both occurrences of (0, 1): G_first = 5, G_second = 0 -> mean 2.5.
"""

import numpy as np
import pytest

from wafarena.agents.base import Transition
from wafarena.agents.mc import MCAgent

OBS = np.zeros(288)


def make(variant: str, epsilon: float = 0.0, gamma: float = 1.0) -> MCAgent:
    return MCAgent.from_config(
        params={"variant": variant, "epsilon": epsilon, "gamma": gamma},
        obs_dim=288,
        n_actions=17,
        seed=0,
        agent_id="t",
    )


def step(agent: MCAgent, state: int, action: int, reward: float, *, done: bool) -> None:
    agent.act(OBS, {"abstract_state": state}, explore=True)  # records the pre-step state
    agent.observe(Transition(OBS, action, reward, OBS, done, False, {"abstract_state": state}))


EPISODE = [(0, 1, 4.0), (0, 2, 1.0), (0, 1, 0.0)]


def run_episode(agent: MCAgent) -> None:
    for index, (state, action, reward) in enumerate(EPISODE):
        step(agent, state, action, reward, done=index == len(EPISODE) - 1)


def test_first_visit_uses_only_the_earliest_return():
    agent = make("first_visit")
    run_episode(agent)
    assert agent.q[0, 1] == pytest.approx(5.0)
    assert agent.q[0, 2] == pytest.approx(1.0)
    assert agent.counts[0, 1] == 1  # the second (0, 1) visit contributed nothing


def test_every_visit_averages_every_occurrence():
    agent = make("every_visit")
    run_episode(agent)
    assert agent.q[0, 1] == pytest.approx(2.5)
    assert agent.q[0, 2] == pytest.approx(1.0)
    assert agent.counts[0, 1] == 2


def test_discounting_applies_within_the_return():
    agent = make("first_visit", gamma=0.5)
    run_episode(agent)
    # G(0,1 first) = 4 + 0.5*1 + 0.25*0 = 4.5
    assert agent.q[0, 1] == pytest.approx(4.5)


def test_incremental_average_matches_a_second_episode_by_hand():
    agent = make("first_visit")
    run_episode(agent)  # Q[0,1] = 5.0, count 1
    step(agent, 0, 1, 10.0, done=True)  # a lone-step episode: G = 10
    assert agent.counts[0, 1] == 2
    assert agent.q[0, 1] == pytest.approx((5.0 + 10.0) / 2)


def test_epsilon_zero_is_pure_greedy_during_training():
    agent = make("first_visit", epsilon=0.0)
    agent.q[3] = np.array([0.0] * 17)
    agent.q[3, 9] = 1.0
    actions = {agent.act(OBS, {"abstract_state": 3}, explore=True) for _ in range(50)}
    assert actions == {9}


def test_epsilon_soft_explores_but_mostly_exploits():
    agent = make("first_visit", epsilon=0.2)
    agent.q[3, 9] = 1.0
    actions = [agent.act(OBS, {"abstract_state": 3}, explore=True) for _ in range(500)]
    assert actions.count(9) > 400
    assert len(set(actions)) > 1


def test_deployment_is_greedy_regardless_of_epsilon():
    agent = make("first_visit", epsilon=1.0)
    agent.q[3, 9] = 1.0
    assert all(agent.act(OBS, {"abstract_state": 3}, explore=False) == 9 for _ in range(20))


def test_unknown_variant_is_rejected():
    with pytest.raises(ValueError, match="no-such-variant"):
        make("no-such-variant")


def test_checkpoint_round_trip(tmp_path):
    from wafarena.agents.base import load_checkpoint, save_checkpoint

    agent = make("every_visit", epsilon=0.1)
    run_episode(agent)
    save_checkpoint(agent, tmp_path / "ck", algo="mc", obs_dim=288, n_actions=17)
    loaded = load_checkpoint(tmp_path / "ck")
    assert np.array_equal(loaded.q, agent.q)
    assert np.array_equal(loaded.counts, agent.counts)
    assert loaded.act(OBS, {"abstract_state": 0}, explore=False) == 1
