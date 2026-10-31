"""F4-T03: real and simulated Dyna-Q updates."""

import numpy as np

from wafarena.agents import Transition, load_checkpoint, save_checkpoint
from wafarena.agents.dyna.agent import DynaAgent
from wafarena.agents.td import TDAgent
from wafarena.envs.abstract_state import AbstractState
from wafarena.envs.attacker_env import N_ACTIONS, SEND_ACTION
from wafarena.envs.attacker_obs import OBS_SIZE


def _transition(
    action: int, *, response: int = 3, done: bool = False, banned: bool = False
) -> Transition:
    next_state = AbstractState(0, response, 0).encode()
    return Transition(
        obs=np.zeros(OBS_SIZE, dtype=np.float32),
        action=action,
        reward=-1.0,
        next_obs=np.zeros(OBS_SIZE, dtype=np.float32),
        terminated=done,
        truncated=False,
        info={"abstract_state": next_state, "response": response, "mutations": 0, "banned": banned},
    )


def test_f4_t03_zero_planning_matches_qlearning_real_backup():
    """F4-T03: n=0 reproduces the EXP-D1 tabular Q-learning update."""
    dyna = DynaAgent("dyna", 7, planning_steps=0, alpha=0.1, gamma=0.99, epsilon=0.0)
    baseline = TDAgent("baseline", 7, method="qlearning", alpha=0.1, gamma=0.99, epsilon=0.0)
    for agent in (dyna, baseline):
        agent.q[0, SEND_ACTION] = 1.0
        assert agent.act(np.zeros(OBS_SIZE), {"abstract_state": 0}, explore=True) == SEND_ACTION
    dyna.observe(_transition(SEND_ACTION))
    baseline.observe(_transition(SEND_ACTION))
    np.testing.assert_array_equal(dyna.q, baseline.q)
    assert dyna.real_queries == 1
    assert dyna.simulated_updates == 0


def test_f4_t03_planning_updates_do_not_spend_real_queries():
    """F4-T03: simulated SEND backups change Q without calling the environment."""
    agent = DynaAgent("dyna", 3, planning_steps=5, epsilon=0.0)
    agent.q[0, SEND_ACTION] = 1.0
    agent.act(np.zeros(OBS_SIZE), {"abstract_state": 0}, explore=True)
    metrics = agent.observe(_transition(SEND_ACTION))
    assert agent.real_queries == 1
    assert agent.simulated_updates == 5
    assert np.isfinite(metrics["surrogate_loss"])
    assert np.isfinite(agent.q).all()


def test_f4_t03_mutation_planning_does_not_train_send_surrogate():
    """F4-T03: a mutation can be replayed without adding a SEND label."""
    agent = DynaAgent("dyna", 3, planning_steps=3, epsilon=0.0)
    agent.q[0, 0] = 1.0
    agent.act(np.zeros(OBS_SIZE), {"abstract_state": 0}, explore=True)
    metrics = agent.observe(_transition(0, response=0))
    assert agent.real_queries == 0
    assert agent.simulated_updates == 3
    assert "surrogate_loss" not in metrics


def test_f4_t03_greedy_evaluation_does_not_change_training_state():
    """F4-T03: validation actions leave Q, model, and real query count untouched."""
    agent = DynaAgent("dyna", 3, planning_steps=5)
    before = agent.q.copy()
    agent.act(np.zeros(OBS_SIZE), {"abstract_state": 0}, explore=False)
    np.testing.assert_array_equal(agent.q, before)
    assert agent.real_queries == 0
    assert agent.simulated_updates == 0


def test_f4_t03_checkpoint_reloads_greedy_policy(tmp_path):
    """F4-T03: the validation checkpoint retains the learned Q table."""
    agent = DynaAgent("dyna", 3, planning_steps=5)
    agent.q[0, SEND_ACTION] = 2.0
    save_checkpoint(
        agent,
        tmp_path,
        algo="dyna",
        obs_dim=OBS_SIZE,
        n_actions=N_ACTIONS,
        train={"agent_params": {"planning_steps": 5}},
    )
    restored = load_checkpoint(tmp_path)
    np.testing.assert_array_equal(restored.q, agent.q)
    assert restored.act(np.zeros(OBS_SIZE), {"abstract_state": 0}, explore=False) == SEND_ACTION


def test_f4_t03_simulated_nonblocking_response_does_not_inherit_ban(monkeypatch):
    """F4-T03: a simulated PASS_NO_EFFECT may continue after a real BLOCKED ban."""
    agent = DynaAgent("dyna", 3, planning_steps=0, epsilon=0.0)
    agent.q[0, SEND_ACTION] = 1.0
    agent.act(np.zeros(OBS_SIZE), {"abstract_state": 0}, explore=True)
    agent.observe(_transition(SEND_ACTION, response=3, done=True, banned=True))
    pass_state = AbstractState(0, 2, 0).encode()
    agent.q[pass_state, 0] = 10.0
    monkeypatch.setattr(
        agent.surrogate,
        "predict_proba",
        lambda _obs: np.array([0.0, 1.0, 0.0, 0.0, 0.0]),
    )
    before = agent.q[0, SEND_ACTION]
    agent._planning_backup()
    assert agent.q[0, SEND_ACTION] > before
