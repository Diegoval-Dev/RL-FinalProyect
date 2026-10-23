"""Tabular TD control: SARSA, Q-learning and SARSA(lambda) with replacing traces (EXP-D1, EXP-D2).

SARSA's backup for step t needs the action actually taken at t+1, which this online, callback-
style `Agent` protocol only learns when `act` is called again for s' — so the SARSA and
SARSA(lambda) backups are *deferred*: `observe` records `(s, a, r, s')`, and the next call to
`act` both picks a' and immediately applies the backup that needed it. Q-learning needs no
deferral: its target is `max_a' Q(s', a')`, known as soon as `observe` sees s'.

A terminal transition (`terminated` or `truncated`) bootstraps 0 and clears the eligibility trace;
treating a time-limit truncation the same as a true termination is a simplification, declared
here rather than modeled exactly.
"""

from pathlib import Path
from typing import Any

import numpy as np

from wafarena.agents.base import META_FILE, Transition, register_agent
from wafarena.envs.abstract_state import N_STATES
from wafarena.envs.attacker_env import N_ACTIONS

METHODS = ("sarsa", "qlearning", "sarsa_lambda")
WEIGHTS_FILE = "td.npz"


@register_agent("td")
class TDAgent:
    role = "attacker"

    def __init__(
        self,
        agent_id: str,
        seed: int,
        *,
        method: str = "qlearning",
        alpha: float = 0.1,
        gamma: float = 0.99,
        epsilon: float = 0.1,
        lambda_: float = 0.0,
    ):
        if method not in METHODS:
            raise ValueError(f"unknown TD method {method!r}, expected one of {METHODS}")
        self.agent_id = agent_id
        self._rng = np.random.default_rng(seed)
        self._method, self._alpha, self._gamma = method, alpha, gamma
        self._epsilon, self._lambda = epsilon, lambda_
        self.q = np.zeros((N_STATES, N_ACTIONS))
        self._eligibility = np.zeros((N_STATES, N_ACTIONS))
        self._pending: tuple[int, int, float, int] | None = None  # (s, a, r, s') awaiting a'
        self._current: tuple[int, int] | None = None  # (s, a) of the in-flight step

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id) -> "TDAgent":
        return cls(agent_id, seed, **params)

    def _greedy_action(self, state: int) -> int:
        row = self.q[state]
        return int(self._rng.choice(np.flatnonzero(row == row.max())))

    def _epsilon_greedy_action(self, state: int) -> int:
        if self._rng.random() < self._epsilon:
            return int(self._rng.integers(N_ACTIONS))
        return self._greedy_action(state)

    def act(self, obs: np.ndarray, info: dict[str, Any], *, explore: bool) -> int:
        state = int(info["abstract_state"])
        if not explore:
            return self._greedy_action(state)
        action = self._epsilon_greedy_action(state)
        if self._pending is not None:
            p_state, p_action, p_reward, p_next_state = self._pending
            self._backup(
                p_state, p_action, p_reward, next_state=p_next_state, next_action=action, done=False
            )
            self._pending = None
        self._current = (state, action)
        return action

    def observe(self, t: Transition) -> dict[str, float]:
        state, action = self._current
        next_state = int(t.info["abstract_state"])
        done = t.terminated or t.truncated
        if self._method == "qlearning" or done:
            self._backup(
                state, action, t.reward, next_state=next_state, next_action=None, done=done
            )
        else:
            self._pending = (state, action, t.reward, next_state)
        if done:
            self._eligibility.fill(0.0)
            self._pending = None
        return {}

    def _backup(
        self,
        state: int,
        action: int,
        reward: float,
        *,
        next_state: int,
        next_action: int | None,
        done: bool,
    ) -> None:
        if self._method == "qlearning":
            bootstrap = 0.0 if done else self.q[next_state].max()
        else:
            bootstrap = 0.0 if done else self.q[next_state, next_action]
        td_error = reward + self._gamma * bootstrap - self.q[state, action]
        if self._method == "sarsa_lambda":
            self._eligibility[state, action] = 1.0  # replacing trace
            self.q += self._alpha * td_error * self._eligibility
            self._eligibility *= self._gamma * self._lambda
        else:
            self.q[state, action] += self._alpha * td_error

    def save(self, path: Path) -> None:
        np.savez(path / WEIGHTS_FILE, q=self.q)

    @classmethod
    def load(cls, path: Path) -> "TDAgent":
        import yaml

        meta = yaml.safe_load((path / META_FILE).read_text())
        params = meta.get("train", {}).get("agent_params", {})
        agent = cls(meta["agent_id"], seed=0, **params)
        agent.q = np.load(path / WEIGHTS_FILE)["q"]
        return agent
