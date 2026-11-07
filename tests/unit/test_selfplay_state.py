"""F4-T05: generation checkpoints preserve learning, not only model weights."""

import numpy as np
import torch

from wafarena.agents import load_checkpoint, save_checkpoint
from wafarena.agents.base import Transition
from wafarena.agents.dqn import DQNAgent
from wafarena.agents.pg import PolicyGradientAgent
from wafarena.selfplay.state import load_training_state, save_training_state


def test_dqn_resumes_replay_schedule_and_optimizer(tmp_path):
    params = {
        "hidden": [8],
        "buffer_size": 8,
        "batch_size": 2,
        "learning_starts": 2,
        "train_freq": 1,
        "target_update": 9,
    }
    agent = DQNAgent.from_config(params=params, obs_dim=3, n_actions=2, seed=7, agent_id="def-test")
    obs = np.ones(3, dtype=np.float32)
    transition = Transition(obs, 0, 1.0, obs, False, False, {})
    for _ in range(3):
        agent.observe(transition)
    save_checkpoint(
        agent,
        tmp_path,
        algo="dqn",
        obs_dim=3,
        n_actions=2,
        train={"seed": 7, "agent_params": params},
    )
    save_training_state(agent, tmp_path)
    resumed = load_checkpoint(tmp_path)
    load_training_state(resumed, tmp_path)
    assert resumed._steps == 3
    assert resumed._buffer.size == 3
    assert resumed._optimizer.state_dict()["state"]
    agent.observe(transition)
    resumed.observe(transition)
    assert all(
        torch.allclose(a, b)
        for a, b in zip(agent.q_net.parameters(), resumed.q_net.parameters(), strict=True)
    )


def test_ppo_resumes_partial_rollout_and_rng(tmp_path):
    params = {
        "hidden": [8],
        "method": "ppo",
        "n_steps": 4,
        "minibatch_size": 4,
        "update_epochs": 1,
    }
    agent = PolicyGradientAgent.from_config(
        params=params, obs_dim=3, n_actions=2, seed=7, agent_id="atk-test"
    )
    obs = np.ones(3, dtype=np.float32)

    def step(policy):
        action = policy.act(obs, {}, explore=True)
        policy.observe(Transition(obs, action, 1.0, obs, False, False, {}))

    for _ in range(2):
        step(agent)
    save_checkpoint(
        agent,
        tmp_path,
        algo="pg",
        obs_dim=3,
        n_actions=2,
        train={"seed": 7, "agent_params": params},
    )
    save_training_state(agent, tmp_path)
    resumed = load_checkpoint(tmp_path)
    load_training_state(resumed, tmp_path)
    assert len(resumed._buffer) == 2
    for _ in range(2):
        step(agent)
        step(resumed)
    assert all(
        torch.allclose(a, b)
        for a, b in zip(agent.actor.parameters(), resumed.actor.parameters(), strict=True)
    )
