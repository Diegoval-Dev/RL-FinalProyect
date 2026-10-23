"""F2-T06: model estimation, value iteration and policy iteration (catalogo.md EXP-B1).

The hand-checked cases use a tiny 2-state, 2-action MDP, not the 120-state attacker abstraction:
state 0 action 0 -> state 1, reward 10; state 0 action 1 -> state 0, reward 0 (loop forever for
0); state 1 is absorbing with 0 further reward under either action. The optimal policy at state 0
is action 0, with V*(0) = 10 and V*(1) = 0, exactly, for any gamma < 1.
"""

import numpy as np
import pytest

from wafarena.agents.dp import estimate_model, policy_iteration, policy_value, value_iteration

TINY_TRANSITIONS = [
    (0, 0, 10.0, 1, True),
    (0, 1, 0.0, 0, False),
    (1, 0, 0.0, 1, True),
    (1, 1, 0.0, 1, True),
]


def tiny_model():
    return estimate_model(TINY_TRANSITIONS, n_states=2, n_actions=2)


def test_estimate_model_reward_is_the_mean_observed_reward():
    P, R = tiny_model()
    assert R[0, 0] == pytest.approx(10.0)
    assert R[0, 1] == pytest.approx(0.0)


def test_estimate_model_transition_probabilities_sum_to_one_and_match_counts():
    P, R = tiny_model()
    assert np.allclose(P.sum(axis=2), 1.0)
    assert P[0, 0, 1] == pytest.approx(1.0)
    assert P[0, 1, 0] == pytest.approx(1.0)


def test_estimate_model_mean_reward_over_several_samples():
    transitions = [(0, 0, 10.0, 1, True), (0, 0, 10.0, 1, True), (0, 0, 0.0, 0, False)]
    P, R = estimate_model(transitions, n_states=2, n_actions=2)
    assert R[0, 0] == pytest.approx(20.0 / 3)
    assert P[0, 0, 1] == pytest.approx(2 / 3)
    assert P[0, 0, 0] == pytest.approx(1 / 3)


def test_estimate_model_unvisited_pair_is_a_zero_reward_self_loop():
    transitions = [(0, 0, 10.0, 1, True)]  # action 1 from state 0 is never observed
    P, R = estimate_model(transitions, n_states=2, n_actions=2)
    assert R[0, 1] == pytest.approx(0.0)
    assert P[0, 1, 0] == pytest.approx(1.0)


def test_value_iteration_matches_the_hand_computed_optimal_value():
    P, R = tiny_model()
    V, policy, iterations = value_iteration(P, R, gamma=0.9, theta=1e-8)
    assert V[0] == pytest.approx(10.0, abs=1e-6)
    assert V[1] == pytest.approx(0.0, abs=1e-6)
    assert policy[0] == 0
    assert iterations > 0


def test_value_iteration_converges_within_a_bounded_number_of_iterations():
    P, R = tiny_model()
    _V, _policy, iterations = value_iteration(P, R, gamma=0.9, theta=1e-8)
    assert iterations < 200  # geometric contraction, not a timeout


def test_policy_iteration_matches_value_iteration_on_this_mdp():
    P, R = tiny_model()
    v_star, v_policy, _ = value_iteration(P, R, gamma=0.9, theta=1e-8)
    p_star, p_policy, iterations = policy_iteration(P, R, gamma=0.9, theta=1e-8)
    assert np.allclose(v_star, p_star, atol=1e-5)
    assert np.array_equal(v_policy, p_policy)
    assert iterations > 0


def test_policy_value_evaluates_a_fixed_policy_exactly():
    P, R = tiny_model()
    always_action_0 = np.array([0, 0])
    v = policy_value(P, R, always_action_0, gamma=0.9)
    assert v[0] == pytest.approx(10.0, abs=1e-6)
    always_action_1 = np.array([1, 1])
    v = policy_value(P, R, always_action_1, gamma=0.9)
    assert v[0] == pytest.approx(0.0, abs=1e-6)  # loops forever for 0 reward


def test_value_iteration_rejects_gamma_at_or_above_one():
    P, R = tiny_model()
    with pytest.raises(ValueError, match="gamma"):
        value_iteration(P, R, gamma=1.0, theta=1e-6)


def test_value_and_policy_iteration_agree_on_a_larger_random_mdp():
    """Not hand-checked, but both methods must still agree with each other (EXP-B1's hypothesis)."""
    rng = np.random.default_rng(0)
    n_states, n_actions = 10, 3
    P = rng.dirichlet(np.ones(n_states), size=(n_states, n_actions))
    R = rng.normal(size=(n_states, n_actions))
    v_star, v_policy, _ = value_iteration(P, R, gamma=0.95, theta=1e-8)
    p_star, p_policy, _ = policy_iteration(P, R, gamma=0.95, theta=1e-8)
    assert np.allclose(v_star, p_star, atol=1e-4)
    assert np.array_equal(v_policy, p_policy)


def test_dp_policy_agent_acts_by_abstract_state():
    from wafarena.agents.dp import DPPolicyAgent

    policy = np.zeros(120, dtype=int)
    policy[5] = 3
    agent = DPPolicyAgent("ATK-DP", policy)
    assert agent.act(None, {"abstract_state": 5}, explore=False) == 3
    assert agent.act(None, {"abstract_state": 0}, explore=True) == 0


def test_dp_policy_agent_does_not_learn():
    from wafarena.agents.dp import DPPolicyAgent

    agent = DPPolicyAgent("ATK-DP", np.zeros(120, dtype=int))
    assert agent.observe(None) == {}


def test_dp_policy_agent_checkpoint_round_trip(tmp_path):
    from wafarena.agents.base import load_checkpoint, save_checkpoint
    from wafarena.agents.dp import DPPolicyAgent

    policy = np.arange(120) % 17
    agent = DPPolicyAgent("ATK-DP", policy)
    save_checkpoint(agent, tmp_path / "ck", algo="dp", obs_dim=288, n_actions=17)
    loaded = load_checkpoint(tmp_path / "ck")
    assert np.array_equal(loaded.policy, policy)
    assert loaded.agent_id == "ATK-DP" and loaded.role == "attacker"
