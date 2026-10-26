"""Semi-gradient TD control with a linear action-value function (EXP-E1, EXP-E2).

Q(s, a) = w_a · x(s), with x(s) = [obs, 1] (the 37 defender features plus a bias). The update is
the semi-gradient one of Sutton & Barto, ch. 10: w_a += alpha * delta * x(s), where delta uses
`max_a' Q(s', a')` (Q-learning) or `Q(s', a')` for the action actually taken next (SARSA).

As in `td.py`, the SARSA backup needs a' and the callback-style `Agent` protocol only learns it
when `act` is called for s', so SARSA's backup is deferred to that call. A terminal or truncated
transition bootstraps 0 (the same declared simplification as `td.py`).

`behavior: uniform` (EXP-E2) makes the agent act uniformly at random while training instead of
epsilon-greedily on its own Q: with Q-learning that is the off-policy corner of the deadly triad
(function approximation + bootstrapping + off-policy data). Weights are never clipped, so a
divergence shows up as it is in `m_weight_norm` of train.csv.
"""

from pathlib import Path
from typing import Any

import numpy as np
import yaml

from wafarena.agents.base import META_FILE, Transition, register_agent
from wafarena.agents.schedules import linear_schedule

METHODS = ("qlearning", "sarsa")
BEHAVIORS = ("egreedy", "uniform")
WEIGHTS_FILE = "linear.npz"


@register_agent("linear")
class LinearAgent:
    role = "defender"

    def __init__(
        self,
        agent_id: str,
        seed: int,
        *,
        obs_dim: int,
        n_actions: int,
        method: str = "qlearning",
        alpha: float = 0.01,
        gamma: float = 0.9,
        epsilon: Any = 0.1,
        behavior: str = "egreedy",
    ):
        if method not in METHODS:
            raise ValueError(f"unknown linear TD method {method!r}, expected one of {METHODS}")
        if behavior not in BEHAVIORS:
            raise ValueError(f"unknown behavior {behavior!r}, expected one of {BEHAVIORS}")
        self.agent_id = agent_id
        self._rng = np.random.default_rng(seed)
        self._method, self._alpha, self._gamma, self._behavior = method, alpha, gamma, behavior
        self._epsilon = linear_schedule(epsilon)
        self._n_actions = n_actions
        self.weights = np.zeros((n_actions, obs_dim + 1))
        self._steps = 0
        self._pending: tuple[np.ndarray, int, float, np.ndarray] | None = None  # awaiting a'
        self._current: tuple[np.ndarray, int] | None = None  # (x, a) of the in-flight step
        self._last_delta = 0.0  # TD error of the latest backup applied (SARSA's lands in act)

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id) -> "LinearAgent":
        return cls(agent_id, seed, obs_dim=obs_dim, n_actions=n_actions, **params)

    @staticmethod
    def _features(obs: np.ndarray) -> np.ndarray:
        return np.append(np.asarray(obs, dtype=float), 1.0)

    def q_values(self, obs: np.ndarray) -> np.ndarray:
        with np.errstate(over="ignore", invalid="ignore"):
            return self.weights @ self._features(obs)

    def _greedy(self, q: np.ndarray) -> int:
        if not np.isfinite(q).any():
            return 0
        return int(self._rng.choice(np.flatnonzero(q == np.nanmax(q))))

    def act(self, obs: np.ndarray, info, *, explore: bool) -> int:
        x = self._features(obs)
        q = self.q_values(obs)
        if not explore:
            return self._greedy(q)
        if self._behavior == "uniform" or self._rng.random() < self._epsilon(self._steps):
            action = int(self._rng.integers(self._n_actions))
        else:
            action = self._greedy(q)
        if self._pending is not None:
            p_x, p_action, p_reward, _ = self._pending
            self._last_delta = self._backup(
                p_x, p_action, p_reward, bootstrap=self._value(x, action)
            )
            self._pending = None
        self._current = (x, action)
        return action

    def _value(self, x: np.ndarray, action: int) -> float:
        with np.errstate(over="ignore", invalid="ignore"):
            return float(self.weights[action] @ x)

    def observe(self, t: Transition) -> dict[str, float]:
        x, action = self._current
        self._steps += 1
        done = t.terminated or t.truncated
        next_x = self._features(t.next_obs)
        if done:
            self._last_delta = self._backup(x, action, t.reward, bootstrap=0.0)
            self._pending = None
        elif self._method == "qlearning":
            with np.errstate(over="ignore", invalid="ignore"):
                bootstrap = float(np.max(self.weights @ next_x))
            self._last_delta = self._backup(x, action, t.reward, bootstrap=bootstrap)
        else:
            self._pending = (x, action, t.reward, next_x)
        with np.errstate(over="ignore", invalid="ignore"):
            norm = float(np.linalg.norm(self.weights))
        return {"td_error": abs(self._last_delta), "weight_norm": norm}

    def _backup(self, x: np.ndarray, action: int, reward: float, *, bootstrap: float) -> float:
        with np.errstate(over="ignore", invalid="ignore"):
            delta = reward + self._gamma * bootstrap - float(self.weights[action] @ x)
            self.weights[action] += self._alpha * delta * x
        return delta

    def save(self, path: Path) -> None:
        np.savez(path / WEIGHTS_FILE, weights=self.weights)

    @classmethod
    def load(cls, path: Path) -> "LinearAgent":
        meta = yaml.safe_load((path / META_FILE).read_text())
        params = meta.get("train", {}).get("agent_params", {})
        agent = cls(
            meta["agent_id"],
            seed=0,
            obs_dim=meta["obs_dim"],
            n_actions=meta["n_actions"],
            **params,
        )
        agent.weights = np.load(path / WEIGHTS_FILE)["weights"]
        return agent
