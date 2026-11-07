"""Optional learning-state sidecar for self-play generation checkpoints.

The regular checkpoint contract still loads a policy from its weights. This sidecar lets the
self-play trainer continue replay, rollout, optimizer, and exploration state after a generation
boundary or restart. Only the PPO attacker and DQN defender used in F4-T05 are supported.
"""

from pathlib import Path

import numpy as np
import torch

from wafarena.agents.dqn import DQNAgent
from wafarena.agents.pg import PolicyGradientAgent, RolloutBuffer

STATE_FILE = "training_state.pt"


def save_training_state(agent, path: Path) -> None:
    path = Path(path)
    if isinstance(agent, DQNAgent):
        buffer = agent._buffer
        state = {
            "kind": "dqn",
            "target_net": agent.target_net.state_dict(),
            "optimizer": agent._optimizer.state_dict(),
            "steps": agent._steps,
            "rng": agent._rng.bit_generator.state,
            "last_metrics": agent._last_metrics,
            "buffer": {
                "obs": torch.from_numpy(buffer.obs.copy()),
                "next_obs": torch.from_numpy(buffer.next_obs.copy()),
                "actions": torch.from_numpy(buffer.actions.copy()),
                "rewards": torch.from_numpy(buffer.rewards.copy()),
                "terminated": torch.from_numpy(buffer.terminated.copy()),
                "size": buffer.size,
                "cursor": buffer.cursor,
                "max_priority": buffer.max_priority,
                "tree": torch.from_numpy(buffer.tree.tree.copy()) if buffer.tree else None,
            },
        }
    elif isinstance(agent, PolicyGradientAgent):
        buffer = agent._buffer
        if buffer.done:
            buffer.done[-1] = True  # a new generation resets the environment and opponent
        state = {
            "kind": "pg",
            "optimizer": agent._optimizer.state_dict(),
            "train_rng": agent._train_gen.get_state(),
            "eval_rng": agent._eval_gen.get_state(),
            "last_metrics": agent._last_metrics,
            "buffer": {
                "obs": [torch.as_tensor(value) for value in buffer.obs],
                "next_obs": [torch.as_tensor(value) for value in buffer.next_obs],
                "actions": buffer.actions,
                "logprobs": buffer.logprobs,
                "rewards": buffer.rewards,
                "terminated": buffer.terminated,
                "done": buffer.done,
            },
        }
    else:
        raise TypeError(f"self-play training state does not support {type(agent).__name__}")
    torch.save(state, path / STATE_FILE)


def load_training_state(agent, path: Path) -> None:
    state = torch.load(Path(path) / STATE_FILE, weights_only=True)
    if isinstance(agent, DQNAgent) and state["kind"] == "dqn":
        agent.target_net.load_state_dict(state["target_net"])
        agent._optimizer.load_state_dict(state["optimizer"])
        agent._steps = state["steps"]
        agent._rng.bit_generator.state = state["rng"]
        agent._last_metrics = state["last_metrics"]
        buffer, saved = agent._buffer, state["buffer"]
        for name in ("obs", "next_obs", "actions", "rewards", "terminated"):
            target = getattr(buffer, name)
            value = saved[name].numpy()
            if target.shape != value.shape:
                raise ValueError(f"self-play DQN replay shape changed for {name}")
            target[:] = value
        buffer.size, buffer.cursor = saved["size"], saved["cursor"]
        buffer.max_priority = saved["max_priority"]
        if buffer.tree is not None:
            if saved["tree"] is None or buffer.tree.tree.shape != saved["tree"].shape:
                raise ValueError("self-play DQN priority tree shape changed")
            buffer.tree.tree[:] = saved["tree"].numpy()
    elif isinstance(agent, PolicyGradientAgent) and state["kind"] == "pg":
        agent._optimizer.load_state_dict(state["optimizer"])
        agent._train_gen.set_state(state["train_rng"])
        agent._eval_gen.set_state(state["eval_rng"])
        agent._last_metrics = state["last_metrics"]
        saved = state["buffer"]
        buffer = RolloutBuffer()
        buffer.obs = [np.asarray(value.numpy(), dtype=np.float32) for value in saved["obs"]]
        buffer.next_obs = [
            np.asarray(value.numpy(), dtype=np.float32) for value in saved["next_obs"]
        ]
        for name in ("actions", "logprobs", "rewards", "terminated", "done"):
            setattr(buffer, name, list(saved[name]))
        agent._buffer = buffer
    else:
        raise TypeError("self-play training state does not match the loaded agent")
