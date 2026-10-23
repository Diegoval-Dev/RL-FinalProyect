"""On-policy Monte Carlo control, epsilon-soft, first-visit and every-visit (EXP-C1).

Behaves and learns under the same epsilon-soft policy (no separate greedy target): the standard
on-policy MC control of Sutton & Barto §5.4. `explore=False` (deployment) is greedy over the
learned Q, like every other tabular agent here.
"""

from pathlib import Path
from typing import Any

import numpy as np

from wafarena.agents.base import META_FILE, Transition, register_agent
from wafarena.envs.abstract_state import N_STATES
from wafarena.envs.attacker_env import N_ACTIONS

VARIANTS = ("first_visit", "every_visit")
WEIGHTS_FILE = "mc.npz"


@register_agent("mc")
class MCAgent:
    role = "attacker"

    def __init__(
        self,
        agent_id: str,
        seed: int,
        *,
        variant: str = "first_visit",
        epsilon: float = 0.1,
        gamma: float = 0.99,
    ):
        if variant not in VARIANTS:
            raise ValueError(f"unknown MC variant {variant!r}, expected one of {VARIANTS}")
        self.agent_id = agent_id
        self._rng = np.random.default_rng(seed)
        self._variant, self._epsilon, self._gamma = variant, epsilon, gamma
        self.q = np.zeros((N_STATES, N_ACTIONS))
        self.counts = np.zeros((N_STATES, N_ACTIONS), dtype=int)
        self._episode: list[tuple[int, int, float]] = []
        self._last_state: int | None = None

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id) -> "MCAgent":
        return cls(agent_id, seed, **params)

    def _epsilon_soft_action(self, state: int) -> int:
        if self._rng.random() < self._epsilon:
            return int(self._rng.integers(N_ACTIONS))
        return self._greedy_action(state)

    def _greedy_action(self, state: int) -> int:
        row = self.q[state]
        return int(self._rng.choice(np.flatnonzero(row == row.max())))

    def act(self, obs: np.ndarray, info: dict[str, Any], *, explore: bool) -> int:
        state = int(info["abstract_state"])
        if not explore:
            return self._greedy_action(state)
        self._last_state = state  # observe() pairs this with the action it's about to receive
        return self._epsilon_soft_action(state)

    def observe(self, t: Transition) -> dict[str, float]:
        self._episode.append((self._last_state, t.action, t.reward))
        if not (t.terminated or t.truncated):
            return {}
        episode_return = self._update_from_episode()
        self._episode.clear()
        return {"episode_return": episode_return, "q_mean": float(self.q.mean())}

    def _update_from_episode(self) -> float:
        returns = [0.0] * len(self._episode)
        g = 0.0
        for index in reversed(range(len(self._episode))):
            g = self._episode[index][2] + self._gamma * g
            returns[index] = g
        seen: set[tuple[int, int]] = set()
        for index, (state, action, _reward) in enumerate(self._episode):
            pair = (state, action)
            if self._variant == "first_visit" and pair in seen:
                continue
            seen.add(pair)
            self.counts[state, action] += 1
            self.q[state, action] += (returns[index] - self.q[state, action]) / self.counts[
                state, action
            ]
        return returns[0] if returns else 0.0

    def save(self, path: Path) -> None:
        np.savez(path / WEIGHTS_FILE, q=self.q, counts=self.counts)

    @classmethod
    def load(cls, path: Path) -> "MCAgent":
        import yaml

        meta = yaml.safe_load((path / META_FILE).read_text())
        params = meta.get("train", {}).get("agent_params", {})
        agent = cls(meta["agent_id"], seed=0, **params)
        data = np.load(path / WEIGHTS_FILE)
        agent.q, agent.counts = data["q"], data["counts"]
        return agent
