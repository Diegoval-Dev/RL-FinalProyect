"""Tabular Dyna-Q attacker with an incremental model of real SEND responses."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from wafarena.agents.base import META_FILE, Transition, register_agent
from wafarena.agents.dyna.surrogate import SurrogateModel
from wafarena.agents.td import WEIGHTS_FILE, TDAgent
from wafarena.attackers.base import Response
from wafarena.envs.abstract_state import AbstractState, decode
from wafarena.envs.attacker_env import REWARD_BLOCKED, REWARD_EVADED, SEND_ACTION


@dataclass(frozen=True)
class _ModelStep:
    """One real transition retained as a planning starting point."""

    next_state: int
    reward: float
    done: bool
    truncated: bool
    banned: bool
    obs: np.ndarray
    mutations: int


@register_agent("dyna")
class DynaAgent(TDAgent):
    """Q-learning plus simulated backups sampled from observed state-action pairs.

    Mutation actions replay their latest observed transition. For SEND, the model samples a
    public response from the surrogate and constructs its abstract successor and reward.
    """

    def __init__(
        self,
        agent_id: str,
        seed: int,
        *,
        planning_steps: int,
        alpha: float = 0.1,
        gamma: float = 0.99,
        epsilon: float = 0.1,
        surrogate_hidden_dim: int | None = None,
        surrogate_learning_rate: float = 0.1,
    ) -> None:
        if planning_steps < 0:
            raise ValueError("planning_steps must be nonnegative")
        super().__init__(
            agent_id, seed, method="qlearning", alpha=alpha, gamma=gamma, epsilon=epsilon
        )
        self.planning_steps = planning_steps
        self.surrogate = SurrogateModel(
            hidden_dim=surrogate_hidden_dim,
            learning_rate=surrogate_learning_rate,
            seed=seed,
        )
        self._planning_rng = np.random.default_rng(seed + 1_000_000)
        self._model: dict[tuple[int, int], _ModelStep] = {}
        self._model_keys: list[tuple[int, int]] = []
        self.real_queries = 0
        self.simulated_updates = 0

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id) -> "DynaAgent":
        return cls(agent_id, seed, **params)

    def observe(self, t: Transition) -> dict[str, float]:
        state, action = self._current
        metrics = super().observe(t)
        response = int(t.info["response"]) if action == SEND_ACTION else int(Response.NONE)
        key = (state, action)
        if key not in self._model:
            self._model_keys.append(key)
        self._model[key] = _ModelStep(
            next_state=int(t.info["abstract_state"]),
            reward=float(t.reward),
            done=bool(t.terminated or t.truncated),
            truncated=bool(t.truncated),
            banned=bool(t.info.get("banned", False)),
            obs=t.obs.copy(),
            mutations=int(t.info["mutations"]),
        )
        if action == SEND_ACTION:
            self.real_queries += 1
            metrics["surrogate_loss"] = self.surrogate.update(t.obs, response)
        for _ in range(self.planning_steps):
            self._planning_backup()
        return metrics

    def _planning_backup(self) -> None:
        state, action = self._model_keys[int(self._planning_rng.integers(len(self._model_keys)))]
        step = self._model[state, action]
        if action == SEND_ACTION:
            probabilities = self.surrogate.predict_proba(step.obs)
            response = int(self._planning_rng.choice(np.arange(1, 6), p=probabilities))
            family, _, _ = decode(state)
            next_state = AbstractState(family, response, step.mutations).encode()
            reward = REWARD_EVADED if response == Response.PASS_EFFECT else REWARD_BLOCKED
            blocked = response in (Response.BLOCKED, Response.CAPTCHA, Response.RATE_LIMITED)
            done = response == Response.PASS_EFFECT or step.truncated or (step.banned and blocked)
        else:
            next_state, reward, done = step.next_state, step.reward, step.done
        self._backup(state, action, reward, next_state=next_state, next_action=None, done=done)
        self.simulated_updates += 1

    @classmethod
    def load(cls, path: Path) -> "DynaAgent":
        meta: dict[str, Any] = yaml.safe_load((path / META_FILE).read_text())
        params = meta.get("train", {}).get("agent_params", {})
        agent = cls(meta["agent_id"], seed=0, **params)
        agent.q = np.load(path / WEIGHTS_FILE)["q"]
        return agent
