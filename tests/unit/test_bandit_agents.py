"""F2-T05: bandit agents (catalogo.md EXP-A1/A2) — selection rules and the save/load round trip."""

import numpy as np
import pytest

from wafarena.agents import Transition, load_checkpoint, save_checkpoint
from wafarena.agents.bandits import BanditAgent
from wafarena.envs.attacker_env import SEND_ACTION
from wafarena.envs.bandit_env import N_ARMS

OBS = np.zeros(288)


def make(policy="greedy", **params):
    return BanditAgent.from_config(
        params={"policy": policy, **params}, obs_dim=288, n_actions=17, seed=0, agent_id="t"
    )


def pull(agent, arm: int, reward: float, info_extra=None):
    info = {"abstract_state": 0, **(info_extra or {})}
    agent.observe(Transition(OBS, arm, reward, OBS, False, False, info))


def test_random_policy_samples_every_arm_given_enough_pulls():
    agent = make("random")
    arms = {agent.act(OBS, {}, explore=True) for _ in range(500)}
    assert arms == set(range(N_ARMS))


def test_greedy_converges_to_the_best_observed_arm():
    agent = make("greedy")
    pull(agent, 3, 1.0)
    pull(agent, 5, 0.0)
    assert agent.act(OBS, {}, explore=True) == 3


def test_eps_greedy_is_mostly_greedy_and_sometimes_explores():
    agent = make("eps_greedy", epsilon=0.1)
    pull(agent, 2, 1.0)
    actions = [agent.act(OBS, {}, explore=True) for _ in range(500)]
    assert actions.count(2) > 400
    assert len(set(actions)) > 1


def test_eps_greedy_epsilon_zero_is_pure_greedy():
    agent = make("eps_greedy", epsilon=0.0)
    pull(agent, 4, 1.0)
    assert all(agent.act(OBS, {}, explore=True) == 4 for _ in range(50))


def test_optimistic_initial_values_drive_early_exploration():
    agent = make("greedy", q0=1.0)
    seen = set()
    for _ in range(N_ARMS):
        arm = agent.act(OBS, {}, explore=True)
        seen.add(arm)
        pull(agent, arm, 0.0)  # every pull disappoints, so optimism keeps moving to a new arm
    assert seen == set(range(N_ARMS))


def test_ucb_tries_every_arm_once_before_repeating():
    agent = make("ucb", c=2.0)
    seen = []
    for _ in range(N_ARMS):
        arm = agent.act(OBS, {}, explore=True)
        seen.append(arm)
        pull(agent, arm, 0.0)
    assert sorted(seen) == list(range(N_ARMS))


def test_ucb_prefers_the_arm_with_higher_mean_once_all_are_tried():
    agent = make("ucb", c=0.1)
    for arm in range(N_ARMS):
        pull(agent, arm, 1.0 if arm == 6 else 0.0)
    assert agent.act(OBS, {}, explore=True) == 6


def test_sample_average_step_shrinks_with_more_pulls():
    agent = make("greedy", step="sample_average")
    pull(agent, 0, 1.0)
    pull(agent, 0, 0.0)
    assert agent.q[0] == pytest.approx(0.5)  # average of 1.0 and 0.0


def test_constant_step_weighs_recent_pulls_more(monkeypatch):
    agent = make("greedy", step="constant", alpha=0.5)
    pull(agent, 0, 1.0)
    pull(agent, 0, 0.0)
    assert agent.q[0] == pytest.approx(0.25)  # 0.5*(0 - 0.5) + 0.5 = 0.25, not the plain average


def test_deployment_alternates_mutation_then_send():
    agent = make("greedy")
    pull(agent, 9, 1.0)
    first = agent.act(OBS, {"queries_used": 0}, explore=False)
    second = agent.act(OBS, {"queries_used": 1}, explore=False)
    assert first == 9 and second == SEND_ACTION


def test_deployment_resets_to_mutation_at_the_start_of_every_episode():
    agent = make("greedy")
    pull(agent, 1, 1.0)
    agent.act(OBS, {"queries_used": 0}, explore=False)  # mutate
    agent.act(OBS, {"queries_used": 0}, explore=False)  # a new episode started before SEND fired
    assert agent.act(OBS, {"queries_used": 0}, explore=False) == 1


def test_checkpoint_round_trip_preserves_q_values_and_behaviour(tmp_path):
    agent = make("ucb", c=2.0)
    pull(agent, 4, 1.0)
    pull(agent, 4, 1.0)
    pull(agent, 7, 0.0)
    save_checkpoint(agent, tmp_path / "ck", algo="bandit", obs_dim=288, n_actions=17)
    loaded = load_checkpoint(tmp_path / "ck")
    assert np.array_equal(loaded.q, agent.q)
    assert np.array_equal(loaded.counts, agent.counts)
    assert loaded.act(OBS, {"queries_used": 5}, explore=False) == 4  # loaded agent starts fresh
    assert loaded.act(OBS, {"queries_used": 5}, explore=False) == SEND_ACTION
    assert loaded.q.argmax() == 4


def test_unknown_policy_is_rejected():
    with pytest.raises(ValueError, match="no-such-policy"):
        make("no-such-policy")
