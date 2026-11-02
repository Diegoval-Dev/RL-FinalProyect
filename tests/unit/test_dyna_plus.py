"""F4-T04: Dyna-Q+ exploration bonuses under a changing defender."""

import numpy as np
import pytest

from wafarena.agents import Transition, load_checkpoint, save_checkpoint
from wafarena.agents.dyna.plus import DynaPlusAgent
from wafarena.envs.attacker_env import N_ACTIONS
from wafarena.envs.attacker_obs import OBS_SIZE


def _observe_mutation(agent: DynaPlusAgent, action: int = 0) -> None:
    obs = np.zeros(OBS_SIZE, dtype=np.float32)
    agent.q[0, action] = 10.0
    assert agent.act(obs, {"abstract_state": 0}, explore=True) == action
    agent.observe(
        Transition(
            obs=obs,
            action=action,
            reward=-1.0,
            next_obs=obs,
            terminated=False,
            truncated=False,
            info={"abstract_state": 0, "response": 0, "mutations": 0},
        )
    )


def test_real_q_backup_has_no_exploration_bonus():
    agent = DynaPlusAgent("plus", 3, planning_steps=0, kappa=1.0, alpha=1.0, gamma=0.0, epsilon=0.0)
    _observe_mutation(agent)
    assert agent.q[0, 0] == pytest.approx(-1.0)
    assert agent.real_steps == 1
    assert agent.simulated_updates == 0


def test_planning_bonus_grows_with_real_steps_since_last_visit():
    agent = DynaPlusAgent("plus", 3, planning_steps=0, kappa=1.0, alpha=1.0, gamma=0.0, epsilon=0.0)
    _observe_mutation(agent, 0)
    for _ in range(4):
        _observe_mutation(agent, 1)
    agent._model_keys = [(0, 0)]
    agent._planning_backup()
    assert agent.q[0, 0] == pytest.approx(1.0)  # observed reward -1 + sqrt(4)
    assert agent.real_steps == 5
    assert agent.real_queries == 0
    assert agent.simulated_updates == 1


def test_untried_action_uses_zero_reward_self_loop_until_observed():
    agent = DynaPlusAgent("plus", 3, planning_steps=0, kappa=1.0, alpha=1.0, gamma=0.5, epsilon=0.0)
    _observe_mutation(agent, 0)
    _observe_mutation(agent, 0)
    agent.q[0, 2] = 4.0
    agent._model_keys = [(0, 1)]
    agent._planning_backup()
    assert agent.q[0, 1] == pytest.approx(3.0)  # sqrt(1) + 0.5 * max Q(self)
    assert agent.real_queries == 0


def test_checkpoint_restores_dyna_plus_policy(tmp_path):
    agent = DynaPlusAgent("plus", 3, planning_steps=20, kappa=0.001)
    agent.q[0, 2] = 2.0
    save_checkpoint(
        agent,
        tmp_path,
        algo="dyna_plus",
        obs_dim=OBS_SIZE,
        n_actions=N_ACTIONS,
        train={"agent_params": {"planning_steps": 20, "kappa": 0.001}},
    )
    restored = load_checkpoint(tmp_path)
    assert isinstance(restored, DynaPlusAgent)
    np.testing.assert_array_equal(restored.q, agent.q)
    assert restored.act(np.zeros(OBS_SIZE), {"abstract_state": 0}, explore=False) == 2


def test_planning_is_reproducible_for_the_same_seed():
    first = DynaPlusAgent("first", 7, planning_steps=20, kappa=0.01, epsilon=0.0)
    second = DynaPlusAgent("second", 7, planning_steps=20, kappa=0.01, epsilon=0.0)
    for action in (0, 1, 0):
        _observe_mutation(first, action)
        _observe_mutation(second, action)
    np.testing.assert_array_equal(first.q, second.q)
    assert first.simulated_updates == second.simulated_updates == 60
