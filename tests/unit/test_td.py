"""F2-T08: SARSA, Q-learning and SARSA(lambda) with eligibility traces (EXP-D1, EXP-D2).

Drives the agent through hand-constructed transitions (not a real env), via the same act()/
observe() protocol the trainer uses, so timing matches what actually happens online: SARSA's
backup for step t needs the action chosen at step t+1, which it only learns when act() is called
again (the trainer always calls act() for s' before observe() can report what happened next).
"""

import numpy as np
import pytest

from wafarena.agents.base import Transition
from wafarena.agents.td import TDAgent

OBS = np.zeros(288)


def make(method: str, **params) -> TDAgent:
    defaults = {"alpha": 0.5, "gamma": 0.9, "epsilon": 0.0}
    return TDAgent.from_config(
        params={"method": method, **defaults, **params},
        obs_dim=288,
        n_actions=17,
        seed=0,
        agent_id="t",
    )


def act(agent: TDAgent, state: int) -> int:
    return int(agent.act(OBS, {"abstract_state": state}, explore=True))


def observe(agent: TDAgent, action: int, reward: float, next_state: int, *, done: bool) -> None:
    agent.observe(Transition(OBS, action, reward, OBS, done, False, {"abstract_state": next_state}))


def test_q_learning_bootstraps_from_the_max_next_action():
    agent = make("qlearning")
    agent.q[1] = np.array([3.0, 9.0, *([0.0] * 15)])  # max at action 1 -> 9.0
    a0 = act(agent, 0)
    observe(agent, a0, reward=2.0, next_state=1, done=False)
    # target = 2 + 0.9*9.0 = 10.1; Q[0, a0] = 0 + 0.5*(10.1 - 0) = 5.05
    assert agent.q[0, a0] == pytest.approx(5.05)


def test_q_learning_bootstraps_zero_at_a_terminal_transition():
    agent = make("qlearning")
    agent.q[1, 5] = 100.0  # must be ignored: the episode ends here
    a0 = act(agent, 0)
    observe(agent, a0, reward=2.0, next_state=1, done=True)
    assert agent.q[0, a0] == pytest.approx(0.5 * 2.0)


def test_sarsa_bootstraps_from_the_action_actually_taken_next_not_the_max():
    """epsilon=1 makes the next action pure exploration; whichever one it is, SARSA's target
    must use exactly that action's Q value, not the row's max (which is action 1's Q=9.0)."""
    agent = make("sarsa", epsilon=1.0)
    agent.q[1] = np.array([3.0, 9.0, *([0.0] * 15)])
    a0 = act(agent, 0)
    observe(agent, a0, reward=2.0, next_state=1, done=False)
    a1 = act(agent, 1)  # this both picks a' and triggers the deferred SARSA backup for (0, a0)
    target = 2.0 + 0.9 * agent.q[1, a1]
    assert agent.q[0, a0] == pytest.approx(0.5 * target)


def test_sarsa_bootstraps_zero_at_a_terminal_transition():
    agent = make("sarsa")
    a0 = act(agent, 0)
    observe(agent, a0, reward=2.0, next_state=1, done=True)
    assert agent.q[0, a0] == pytest.approx(0.5 * 2.0)


def test_sarsa_lambda_zero_matches_plain_sarsa_on_one_step():
    plain = make("sarsa")
    traced = make("sarsa_lambda", lambda_=0.0)
    a0 = act(plain, 0)
    observe(plain, a0, reward=2.0, next_state=1, done=True)
    a0t = act(traced, 0)
    observe(traced, a0t, reward=2.0, next_state=1, done=True)
    assert traced.q[0, a0t] == pytest.approx(plain.q[0, a0])


def test_sarsa_lambda_propagates_credit_to_an_earlier_pair():
    """lambda > 0 must also nudge an EARLIER (s, a) toward the later TD error, not just the
    pair visited this step; lambda = 0 must not."""
    for lam, expect_earlier_update in [(0.0, False), (0.9, True)]:
        agent = make("sarsa_lambda", lambda_=lam, epsilon=0.0)
        a0 = act(agent, 0)
        observe(agent, a0, reward=0.0, next_state=1, done=False)
        a1 = act(agent, 1)  # backs up (0, a0); e-trace for (0, a0) now decays instead of vanishing
        observe(agent, a1, reward=5.0, next_state=2, done=True)
        act(agent, 2)  # final backup for (1, a1), with (0, a0) still in the trace if lambda > 0
        changed = agent.q[0, a0] != 0.0
        assert changed == expect_earlier_update, lam


def test_replacing_trace_resets_on_terminal_and_does_not_leak_into_the_next_episode():
    agent = make("sarsa_lambda", lambda_=0.9, epsilon=0.0)
    a0 = act(agent, 0)
    observe(agent, a0, reward=1.0, next_state=5, done=True)  # episode 1 ends
    q_after_first_episode = agent.q.copy()
    a0b = act(agent, 3)  # a fresh, unrelated episode 2 starts at a different state
    observe(agent, a0b, reward=0.0, next_state=5, done=True)
    assert agent.q[0].tolist() == q_after_first_episode[0].tolist()  # state 0 untouched by ep. 2


def test_epsilon_zero_is_pure_greedy_during_training():
    agent = make("qlearning", epsilon=0.0)
    agent.q[3, 9] = 1.0
    assert all(act(agent, 3) == 9 for _ in range(30))


def test_deployment_is_greedy_regardless_of_epsilon():
    agent = make("qlearning", epsilon=1.0)
    agent.q[3, 9] = 1.0
    assert all(agent.act(OBS, {"abstract_state": 3}, explore=False) == 9 for _ in range(20))


def test_unknown_method_is_rejected():
    with pytest.raises(ValueError, match="no-such-method"):
        make("no-such-method")


def test_checkpoint_round_trip(tmp_path):
    from wafarena.agents.base import load_checkpoint, save_checkpoint

    agent = make("sarsa_lambda", lambda_=0.5, epsilon=0.1)
    a0 = act(agent, 0)
    observe(agent, a0, reward=1.0, next_state=1, done=True)
    save_checkpoint(agent, tmp_path / "ck", algo="td", obs_dim=288, n_actions=17)
    loaded = load_checkpoint(tmp_path / "ck")
    assert np.array_equal(loaded.q, agent.q)
    assert loaded.act(OBS, {"abstract_state": 0}, explore=False) == a0
