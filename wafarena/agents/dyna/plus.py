"""Dyna-Q+ with a real-visit exploration bonus on planning backups."""

import math

from wafarena.agents.base import Transition, register_agent
from wafarena.agents.dyna.agent import DynaAgent, _ModelStep
from wafarena.envs.attacker_env import N_ACTIONS


@register_agent("dyna_plus")
class DynaPlusAgent(DynaAgent):
    """Plan over tried and untried actions, rewarding stale real visits by κ√τ."""

    def __init__(self, agent_id: str, seed: int, *, kappa: float, **kwargs) -> None:
        if kappa < 0:
            raise ValueError("kappa must be nonnegative")
        super().__init__(agent_id, seed, **kwargs)
        self.kappa = kappa
        self.real_steps = 0
        self._last_real_visit: dict[tuple[int, int], int] = {}
        self._observed_keys: set[tuple[int, int]] = set()

    def observe(self, t: Transition) -> dict[str, float]:
        state, action = self._current
        self.real_steps += 1
        if (state, action) not in self._last_real_visit:
            for other_action in range(N_ACTIONS):
                key = (state, other_action)
                if key not in self._last_real_visit:
                    self._last_real_visit[key] = self.real_steps
                    self._model_keys.append(key)
                    self._model[key] = _ModelStep(
                        next_state=state,
                        reward=0.0,
                        done=False,
                        truncated=False,
                        banned=False,
                        obs=t.obs.copy(),
                        mutations=int(t.info["mutations"]),
                    )
        key = (state, action)
        self._last_real_visit[key] = self.real_steps
        self._observed_keys.add(key)
        return super().observe(t)

    def _planning_backup(self) -> None:
        state, action = self._model_keys[int(self._planning_rng.integers(len(self._model_keys)))]
        key = (state, action)
        if key in self._observed_keys:
            next_state, reward, done = self._sample_model_transition(
                state, action, self._model[key]
            )
        else:
            next_state, reward, done = state, 0.0, False
        age = self.real_steps - self._last_real_visit[key]
        reward += self.kappa * math.sqrt(age)
        self._backup(state, action, reward, next_state=next_state, next_action=None, done=done)
        self.simulated_updates += 1
