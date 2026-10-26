"""F3-T02: semi-gradient linear TD control (EXP-E1, EXP-E2)."""

import numpy as np
import pytest

from wafarena.agents import load_checkpoint, save_checkpoint
from wafarena.agents.base import Transition
from wafarena.agents.linear import LinearAgent
from wafarena.agents.schedules import linear_schedule

OBS_DIM, N_ACTIONS = 3, 2


def agent(**params) -> LinearAgent:
    return LinearAgent("lin", 0, obs_dim=OBS_DIM, n_actions=N_ACTIONS, **params)


def step(a: LinearAgent, obs, reward, next_obs, *, done=False, explore=True):
    action = a.act(np.asarray(obs, dtype=float), {}, explore=explore)
    metrics = a.observe(
        Transition(np.asarray(obs), action, reward, np.asarray(next_obs), done, False, {})
    )
    return action, metrics


def test_qlearning_update_is_the_semi_gradient_rule():
    a = agent(method="qlearning", alpha=0.5, gamma=0.9, epsilon=0.0)
    a.weights[:] = [[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 2.0]]  # Q(·, 0) = 1, Q(·, 1) = 2
    obs = [1.0, 0.0, 0.0]
    action, metrics = step(a, obs, reward=1.0, next_obs=[0.0, 1.0, 0.0])
    assert action == 1
    # delta = 1 + 0.9 * max(1, 2) - 2 = 0.8; w_1 += 0.5 * 0.8 * [1, 0, 0, 1]
    np.testing.assert_allclose(a.weights[1], [0.4, 0.0, 0.0, 2.4])
    np.testing.assert_allclose(a.weights[0], [0.0, 0.0, 0.0, 1.0])
    assert metrics["td_error"] == pytest.approx(0.8)


def test_terminal_transition_bootstraps_zero():
    a = agent(method="qlearning", alpha=1.0, gamma=0.9, epsilon=0.0)
    step(a, [0.0, 0.0, 0.0], reward=3.0, next_obs=[0.0, 0.0, 0.0], done=True)
    assert a.weights[:, -1].max() == pytest.approx(3.0)


def test_sarsa_defers_the_backup_until_the_next_action_is_known():
    a = agent(method="sarsa", alpha=1.0, gamma=0.5, epsilon=0.0)
    obs = [0.0, 0.0, 0.0]
    step(a, obs, reward=1.0, next_obs=obs)
    assert not a.weights.any()  # nothing learned yet: a' is still unknown
    a.act(np.asarray(obs), {}, explore=True)
    assert a.weights.any()


def test_greedy_evaluation_does_not_learn_or_flush_pending_backups():
    a = agent(method="sarsa", alpha=1.0, epsilon=0.0)
    step(a, [1.0, 0.0, 0.0], reward=1.0, next_obs=[1.0, 0.0, 0.0])
    before = a.weights.copy()
    a.act(np.asarray([0.0, 1.0, 0.0]), {}, explore=False)
    np.testing.assert_array_equal(a.weights, before)


def test_uniform_behavior_ignores_q_while_training():
    a = agent(behavior="uniform")
    a.weights[1, -1] = 100.0  # action 1 is clearly greedy
    actions = {a.act(np.zeros(OBS_DIM), {}, explore=True) for _ in range(50)}
    assert actions == {0, 1}
    assert a.act(np.zeros(OBS_DIM), {}, explore=False) == 1


def test_divergent_weights_do_not_crash_acting():
    a = agent()
    a.weights[:] = np.inf
    a.weights[0, 0] = -np.inf
    assert a.act(np.ones(OBS_DIM), {}, explore=False) in (0, 1)


def test_checkpoint_round_trip(tmp_path):
    a = agent(method="sarsa", alpha=0.2)
    a.weights[:] = np.arange(8).reshape(2, 4)
    save_checkpoint(
        a,
        tmp_path,
        algo="linear",
        obs_dim=OBS_DIM,
        n_actions=N_ACTIONS,
        train={"agent_params": {"method": "sarsa", "alpha": 0.2}},
    )
    loaded = load_checkpoint(tmp_path)
    np.testing.assert_array_equal(loaded.weights, a.weights)
    assert loaded.role == "defender"


@pytest.mark.parametrize("bad", [{"method": "nope"}, {"behavior": "nope"}])
def test_rejects_unknown_options(bad):
    with pytest.raises(ValueError):
        agent(**bad)


def test_linear_schedule_constant_and_decay():
    assert linear_schedule(0.1)(10_000) == 0.1
    decay = linear_schedule({"start": 1.0, "end": 0.0, "decay_steps": 10})
    assert decay(0) == 1.0 and decay(5) == pytest.approx(0.5) and decay(50) == 0.0
