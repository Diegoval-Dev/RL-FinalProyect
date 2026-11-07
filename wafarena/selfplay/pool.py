"""Episode-level sampling of current and historical defenders."""

from collections.abc import Sequence

import numpy as np

from wafarena.envs.attacker_env import AttackerEnv
from wafarena.envs.resolve import resolve_defender


def choose_opponent(
    rng: np.random.Generator,
    current: str,
    history: Sequence[str],
    *,
    current_probability: float,
) -> str:
    if not 0 <= current_probability <= 1:
        raise ValueError("current_probability must be a probability in [0, 1]")
    if not history or rng.random() < current_probability:
        return current
    return history[int(rng.integers(len(history)))]


class PoolAttackerEnv(AttackerEnv):
    """Choose one frozen defender checkpoint per training episode."""

    def __init__(
        self,
        backend,
        *,
        current_defender: str,
        historical_defenders: Sequence[str],
        current_probability: float,
        **kwargs,
    ) -> None:
        super().__init__(backend, **kwargs)
        self.current_defender = current_defender
        self.historical_defenders = tuple(historical_defenders)
        self.current_probability = current_probability
        self.selected_defender = None
        self._policies = {}

    def reset(self, *, seed=None, options=None):
        obs, info = super().reset(seed=seed, options=options)
        self.selected_defender = choose_opponent(
            self.np_random,
            self.current_defender,
            self.historical_defenders,
            current_probability=self.current_probability,
        )
        if self.selected_defender not in self._policies:
            self._policies[self.selected_defender] = resolve_defender(
                {"type": "checkpoint", "path": self.selected_defender}
            )
        self._defender = self._policies[self.selected_defender]
        return obs, info
