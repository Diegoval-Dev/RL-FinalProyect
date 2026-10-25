"""F3-T03/F3-T04: DQN and its ablation switches (Double, Dueling, PER, observation mask)."""

import numpy as np
import pytest
import torch

from wafarena.agents import load_checkpoint, save_checkpoint
from wafarena.agents.base import Transition
from wafarena.agents.dqn import DQNAgent, QNetwork, ReplayBuffer, SumTree

OBS_DIM, N_ACTIONS = 4, 3


def agent(**params) -> DQNAgent:
    defaults = {"hidden": [16], "learning_starts": 8, "batch_size": 8, "buffer_size": 64}
    return DQNAgent("dqn", 0, obs_dim=OBS_DIM, n_actions=N_ACTIONS, **{**defaults, **params})


def feed(a: DQNAgent, n: int, *, reward=1.0, action=None, seed=0) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        obs = rng.random(OBS_DIM).astype(np.float32)
        act = a.act(obs, {}, explore=True) if action is None else action
        out.append(a.observe(Transition(obs, act, reward, obs, False, False, {})))
    return out


# --- sum tree and replay buffer ----------------------------------------------------------------


def test_sum_tree_keeps_totals_and_finds_by_cumulative_mass():
    tree = SumTree(4)
    for i, p in enumerate([1.0, 2.0, 3.0, 4.0]):
        tree.update(i, p)
    assert tree.total() == pytest.approx(10.0)
    assert [tree.find(m) for m in (0.5, 1.5, 3.5, 9.9)] == [0, 1, 2, 3]
    tree.update(3, 0.0)
    assert tree.total() == pytest.approx(6.0)


def test_uniform_buffer_has_unit_weights_and_wraps_around():
    buffer = ReplayBuffer(4, OBS_DIM, np.random.default_rng(0), per=False)
    for i in range(6):
        buffer.add(np.full(OBS_DIM, i), i % N_ACTIONS, float(i), np.zeros(OBS_DIM), False)
    assert buffer.size == 4 and set(buffer.rewards) == {2.0, 3.0, 4.0, 5.0}
    indices, weights = buffer.sample(16, beta=0.4)
    assert (weights == 1).all() and indices.max() < 4


def test_per_samples_high_priority_transitions_more_and_corrects_with_weights():
    buffer = ReplayBuffer(8, OBS_DIM, np.random.default_rng(0), per=True)
    for _ in range(8):
        buffer.add(np.zeros(OBS_DIM), 0, 0.0, np.zeros(OBS_DIM), False)
    buffer.update_priorities(np.arange(8), np.array([10.0] + [0.1] * 7))
    indices, weights = buffer.sample(64, beta=1.0)
    assert (indices == 0).mean() > 0.5
    assert weights[indices == 0].max() < weights[indices != 0].min()  # IS correction
    assert weights.max() == pytest.approx(1.0)


def test_new_transitions_get_the_max_priority_seen_so_far():
    buffer = ReplayBuffer(4, OBS_DIM, np.random.default_rng(0), per=True)
    buffer.add(np.zeros(OBS_DIM), 0, 0.0, np.zeros(OBS_DIM), False)
    buffer.update_priorities(np.array([0]), np.array([5.0]))
    buffer.add(np.zeros(OBS_DIM), 0, 0.0, np.zeros(OBS_DIM), False)
    assert buffer.tree.priority(1) == pytest.approx(5.0)


# --- networks ----------------------------------------------------------------------------------


def test_dueling_head_has_zero_mean_advantage_decomposition():
    torch.manual_seed(0)
    net = QNetwork(OBS_DIM, N_ACTIONS, [8], dueling=True)
    x = torch.rand(5, OBS_DIM)
    q = net(x)
    value = net.value(net.body(x))
    torch.testing.assert_close(q.mean(dim=1, keepdim=True), value)


# --- agent -------------------------------------------------------------------------------------


def test_no_learning_before_learning_starts():
    a = agent(learning_starts=20)
    before = [p.clone() for p in a.q_net.parameters()]
    metrics = feed(a, 10)
    assert "loss" not in metrics[-1]
    assert all(torch.equal(b, p) for b, p in zip(before, a.q_net.parameters(), strict=True))


def test_learning_moves_q_towards_the_reward():
    a = agent(gamma=0.0, lr=1e-2, epsilon=0.0)
    feed(a, 300, reward=5.0, action=1)
    q = a.q_values(np.full(OBS_DIM, 0.5, dtype=np.float32))
    assert q[1] == pytest.approx(5.0, abs=1.0)


def test_target_network_is_copied_every_target_update_steps():
    a = agent(target_update=10)
    feed(a, 9)
    assert not all(
        torch.equal(t, q)
        for t, q in zip(a.target_net.parameters(), a.q_net.parameters(), strict=True)
    )
    feed(a, 1)
    assert all(
        torch.equal(t, q)
        for t, q in zip(a.target_net.parameters(), a.q_net.parameters(), strict=True)
    )


def test_obs_mask_hides_the_masked_features_from_the_network():
    a = agent(obs_mask=[[1, 3]])
    obs = np.array([0.1, 0.9, 0.9, 0.2], dtype=np.float32)
    other = np.array([0.1, 0.0, 0.0, 0.2], dtype=np.float32)
    np.testing.assert_array_equal(a.q_values(obs), a.q_values(other))


def test_missed_attack_fraction_counts_allowed_negative_rewards():
    a = agent(role="defender", epsilon=0.0)
    metrics = feed(a, 40, reward=-10.0, action=0)
    assert metrics[-1]["missed_attack_frac"] == 1.0
    b = agent(role="defender")
    assert feed(b, 40, reward=-4.0, action=1)[-1]["missed_attack_frac"] == 0.0


def test_reward_scale_is_applied_before_storage():
    a = agent(reward_scale=0.1)
    feed(a, 1, reward=-10.0, action=0)
    assert a._buffer.rewards[0] == pytest.approx(-1.0)


@pytest.mark.parametrize("variant", [{}, {"double": True}, {"dueling": True}, {"per": True}])
def test_every_variant_trains_and_is_deterministic(variant):
    first, second = agent(**variant), agent(**variant)
    m1, m2 = feed(first, 60, seed=3), feed(second, 60, seed=3)
    assert m1[-1]["loss"] == m2[-1]["loss"]
    obs = np.full(OBS_DIM, 0.3, dtype=np.float32)
    np.testing.assert_array_equal(first.q_values(obs), second.q_values(obs))


def test_greedy_act_is_argmax_and_ignores_epsilon():
    a = agent(epsilon=1.0)
    obs = np.full(OBS_DIM, 0.4, dtype=np.float32)
    assert {a.act(obs, {}, explore=False) for _ in range(20)} == {int(np.argmax(a.q_values(obs)))}


def test_checkpoint_round_trip_keeps_weights_mask_and_variant(tmp_path):
    params = {"hidden": [16], "dueling": True, "obs_mask": [[0, 2]]}
    a = agent(**params)
    feed(a, 30)
    save_checkpoint(
        a,
        tmp_path,
        algo="dqn",
        obs_dim=OBS_DIM,
        n_actions=N_ACTIONS,
        train={"agent_params": {**params, "threads": 1}},
    )
    loaded = load_checkpoint(tmp_path)
    obs = np.array([0.9, 0.9, 0.1, 0.2], dtype=np.float32)
    np.testing.assert_allclose(loaded.q_values(obs), a.q_values(obs), rtol=1e-6)
    np.testing.assert_allclose(
        loaded.q_values(obs), loaded.q_values(np.array([0, 0, 0.1, 0.2], dtype=np.float32))
    )
    assert loaded.role == "defender"


def test_rejects_unknown_loss():
    with pytest.raises(ValueError, match="loss"):
        agent(loss="nope")
