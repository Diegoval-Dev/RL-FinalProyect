"""DQN in one readable file, CleanRL style (ADR-0006), adapted to the callback `Agent` protocol.

Base algorithm (Mnih et al., 2015): an MLP Q-network, an experience replay buffer, a target
network copied every `target_update` steps, epsilon-greedy exploration on a linear schedule and the
TD target r + gamma * (1 - terminated) * max_a' Q_target(s', a'). A time-limit truncation still
bootstraps (only `terminated` cuts it), unlike the tabular agents.

The three improvements of the EXP-F1..F4 ablation are switches of the YAML, one at a time:

- `double: true` — Double DQN (van Hasselt et al., 2016): the online network picks a' and the
  target network evaluates it, which removes the max operator's overestimation bias.
- `dueling: true` — Dueling head (Wang et al., 2016): Q(s, a) = V(s) + A(s, a) - mean_a A(s, a).
- `per: true` — proportional prioritized replay (Schaul et al., 2016): transitions are sampled with
  probability p_i^alpha / sum p^alpha, p_i = |delta_i| + eps, and the loss is weighted by the
  importance-sampling weights (N * P(i))^-beta / max, with beta annealed towards 1.

Also from the YAML: `obs_mask` (index ranges set to zero before the network sees them; ABL-1 and
ABL-2 use it, so the observation contract of the env does not change and the checkpoint carries
the mask), `reward_scale` (rewards are multiplied by it before learning: the env's rewards span
-10..+6), `max_grad_norm` (gradient clipping) and `loss` (huber or mse).

`observe` returns training metrics for train.csv: loss, mean Q of the batch, epsilon and, for
the defender, `missed_attack_frac`: the fraction of the sampled batch made of attacks that the
defender let through with effect. It is read off the transition itself, without ground truth:
in Defender-v0 the only negative reward for ALLOW is an attack with effect (env-defensor.md).
"""

from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from torch import nn

from wafarena.agents.base import META_FILE, Transition, register_agent
from wafarena.agents.schedules import linear_schedule

WEIGHTS_FILE = "dqn.pt"
ALLOW = 0
LOSSES = ("huber", "mse")


class QNetwork(nn.Module):
    def __init__(self, obs_dim: int, n_actions: int, hidden: list[int], dueling: bool):
        super().__init__()
        layers: list[nn.Module] = []
        width = obs_dim
        for size in hidden:
            layers += [nn.Linear(width, size), nn.ReLU()]
            width = size
        self.body = nn.Sequential(*layers)
        self.dueling = dueling
        if dueling:
            self.value = nn.Linear(width, 1)
            self.advantage = nn.Linear(width, n_actions)
        else:
            self.head = nn.Linear(width, n_actions)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.body(x)
        if not self.dueling:
            return self.head(h)
        advantage = self.advantage(h)
        return self.value(h) + advantage - advantage.mean(dim=1, keepdim=True)


class SumTree:
    """Binary tree whose leaves hold priorities and whose inner nodes hold sums of their children:
    sampling proportionally to priority and updating one priority are both O(log n)."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity)

    def total(self) -> float:
        return float(self.tree[1])

    def update(self, index: int, priority: float) -> None:
        node = index + self.capacity
        self.tree[node] = priority
        node //= 2
        while node >= 1:
            self.tree[node] = self.tree[2 * node] + self.tree[2 * node + 1]
            node //= 2

    def find(self, mass: float) -> int:
        """Leaf index whose cumulative priority interval contains `mass`."""
        node = 1
        while node < self.capacity:
            left = 2 * node
            if mass <= self.tree[left]:
                node = left
            else:
                mass -= self.tree[left]
                node = left + 1
        return node - self.capacity

    def priority(self, index: int) -> float:
        return float(self.tree[index + self.capacity])


class ReplayBuffer:
    """Circular buffer of transitions; uniform sampling, or proportional to priority (PER)."""

    def __init__(self, capacity: int, obs_dim: int, rng: np.random.Generator, per: bool):
        self.capacity, self.rng, self.per = capacity, rng, per
        self.obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.next_obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.actions = np.zeros(capacity, dtype=np.int64)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.terminated = np.zeros(capacity, dtype=np.float32)
        self.size = self.cursor = 0
        self.tree = SumTree(capacity) if per else None
        self.max_priority = 1.0

    def add(self, obs, action: int, reward: float, next_obs, terminated: bool) -> None:
        i = self.cursor
        self.obs[i], self.next_obs[i] = obs, next_obs
        self.actions[i], self.rewards[i], self.terminated[i] = action, reward, float(terminated)
        if self.tree is not None:
            self.tree.update(i, self.max_priority)  # new transitions are replayed at least once
        self.cursor = (i + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int, beta: float) -> tuple[np.ndarray, np.ndarray]:
        """(indices, importance-sampling weights); the weights are all 1 without PER."""
        if self.tree is None:
            return self.rng.integers(self.size, size=batch_size), np.ones(batch_size)
        total = self.tree.total()
        # stratified: one draw in each of `batch_size` equal slices of the total priority mass
        edges = np.linspace(0.0, total, batch_size + 1)
        masses = self.rng.uniform(edges[:-1], edges[1:])
        indices = np.array([min(self.tree.find(m), self.size - 1) for m in masses])
        probabilities = np.array([self.tree.priority(i) for i in indices]) / total
        weights = (self.size * probabilities) ** -beta
        return indices, weights / weights.max()

    def update_priorities(self, indices: np.ndarray, priorities: np.ndarray) -> None:
        for i, p in zip(indices, priorities, strict=True):
            self.tree.update(int(i), float(p))
        self.max_priority = max(self.max_priority, float(priorities.max()))


@register_agent("dqn")
class DQNAgent:
    def __init__(
        self,
        agent_id: str,
        seed: int,
        *,
        obs_dim: int,
        n_actions: int,
        role: str = "defender",
        hidden: list[int] | None = None,
        lr: float = 2.5e-4,
        gamma: float = 0.9,
        buffer_size: int = 50_000,
        batch_size: int = 128,
        learning_starts: int = 1_000,
        train_freq: int = 1,
        target_update: int = 1_000,
        epsilon: Any = None,
        max_grad_norm: float = 10.0,
        loss: str = "huber",
        reward_scale: float = 1.0,
        double: bool = False,
        dueling: bool = False,
        per: bool = False,
        per_alpha: float = 0.6,
        per_beta: Any = None,
        per_eps: float = 1e-6,
        obs_mask: list[list[int]] | None = None,
    ):
        if loss not in LOSSES:
            raise ValueError(f"unknown loss {loss!r}, expected one of {LOSSES}")
        self.agent_id, self.role = agent_id, role
        self._rng = np.random.default_rng(seed)
        torch.manual_seed(seed)
        self._n_actions, self._gamma, self._batch_size = n_actions, gamma, batch_size
        self._learning_starts, self._train_freq = learning_starts, train_freq
        self._target_update, self._max_grad_norm = target_update, max_grad_norm
        self._loss, self._reward_scale = loss, reward_scale
        self._double, self._per = double, per
        self._per_alpha, self._per_eps = per_alpha, per_eps
        self._epsilon = linear_schedule(
            epsilon if epsilon is not None else {"start": 1.0, "end": 0.05, "decay_steps": 10_000}
        )
        self._per_beta = linear_schedule(
            per_beta if per_beta is not None else {"start": 0.4, "end": 1.0, "decay_steps": 100_000}
        )
        self._mask = np.ones(obs_dim, dtype=np.float32)
        for start, end in obs_mask or []:
            self._mask[start:end] = 0.0
        hidden = list(hidden or [128, 128])
        self.q_net = QNetwork(obs_dim, n_actions, hidden, dueling)
        self.target_net = QNetwork(obs_dim, n_actions, hidden, dueling)
        self.target_net.load_state_dict(self.q_net.state_dict())
        self._optimizer = torch.optim.Adam(self.q_net.parameters(), lr=lr)
        self._buffer = ReplayBuffer(buffer_size, obs_dim, self._rng, per)
        self._steps = 0
        self._last_metrics: dict[str, float] = {}

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id) -> "DQNAgent":
        torch.set_num_threads(int(params.get("threads", 1)))
        params = {k: v for k, v in params.items() if k != "threads"}
        return cls(agent_id, seed, obs_dim=obs_dim, n_actions=n_actions, **params)

    def _prepare(self, obs) -> np.ndarray:
        return np.asarray(obs, dtype=np.float32) * self._mask

    def q_values(self, obs: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            x = torch.as_tensor(self._prepare(obs)).unsqueeze(0)
            return self.q_net(x).squeeze(0).numpy()

    def act(self, obs: np.ndarray, info, *, explore: bool) -> int:
        if explore and self._rng.random() < self._epsilon(self._steps):
            return int(self._rng.integers(self._n_actions))
        return int(np.argmax(self.q_values(obs)))

    def observe(self, t: Transition) -> dict[str, float]:
        self._buffer.add(
            self._prepare(t.obs),
            t.action,
            t.reward * self._reward_scale,
            self._prepare(t.next_obs),
            t.terminated,
        )
        self._steps += 1
        ready = self._buffer.size >= max(self._learning_starts, self._batch_size)
        if ready and self._steps % self._train_freq == 0:
            self._last_metrics = self._update()
        if self._steps % self._target_update == 0:
            self.target_net.load_state_dict(self.q_net.state_dict())
        return {**self._last_metrics, "epsilon": self._epsilon(self._steps)}

    def _update(self) -> dict[str, float]:
        beta = self._per_beta(self._steps)
        indices, weights = self._buffer.sample(self._batch_size, beta)
        b = self._buffer
        obs = torch.as_tensor(b.obs[indices])
        next_obs = torch.as_tensor(b.next_obs[indices])
        actions = torch.as_tensor(b.actions[indices])
        rewards = torch.as_tensor(b.rewards[indices])
        terminated = torch.as_tensor(b.terminated[indices])
        with torch.no_grad():
            if self._double:
                next_actions = self.q_net(next_obs).argmax(dim=1, keepdim=True)
                next_q = self.target_net(next_obs).gather(1, next_actions).squeeze(1)
            else:
                next_q = self.target_net(next_obs).max(dim=1).values
            target = rewards + self._gamma * (1.0 - terminated) * next_q
        q = self.q_net(obs).gather(1, actions.unsqueeze(1)).squeeze(1)
        td = target - q
        if self._loss == "huber":
            per_sample = nn.functional.smooth_l1_loss(q, target, reduction="none")
        else:
            per_sample = td.pow(2)
        loss = (torch.as_tensor(weights, dtype=torch.float32) * per_sample).mean()
        self._optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.q_net.parameters(), self._max_grad_norm)
        self._optimizer.step()
        if self._per:
            priorities = (td.detach().abs().numpy() + self._per_eps) ** self._per_alpha
            self._buffer.update_priorities(indices, priorities)
        metrics = {"loss": float(loss.detach()), "q_mean": float(q.detach().mean())}
        if self.role == "defender":
            missed = (b.actions[indices] == ALLOW) & (b.rewards[indices] < 0)
            metrics["missed_attack_frac"] = float(missed.mean())
        return metrics

    def save(self, path: Path) -> None:
        torch.save(self.q_net.state_dict(), Path(path) / WEIGHTS_FILE)

    @classmethod
    def load(cls, path: Path) -> "DQNAgent":
        path = Path(path)
        meta = yaml.safe_load((path / META_FILE).read_text())
        params = dict(meta.get("train", {}).get("agent_params", {}))
        params.pop("threads", None)
        agent = cls(
            meta["agent_id"],
            seed=0,
            obs_dim=meta["obs_dim"],
            n_actions=meta["n_actions"],
            **{"role": meta["role"], **params},
        )
        agent.q_net.load_state_dict(torch.load(path / WEIGHTS_FILE, weights_only=True))
        agent.target_net.load_state_dict(agent.q_net.state_dict())
        return agent
