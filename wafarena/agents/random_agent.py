"""RandomAgent: uniform random attacker, the untrained reference for the learning curves."""

from pathlib import Path
from typing import Any

import numpy as np
import yaml

from wafarena.agents.base import META_FILE, register_agent

SEED_FILE = "seed.yaml"


@register_agent("random")
class RandomAgent:
    role = "attacker"

    def __init__(self, agent_id: str, n_actions: int, seed: int):
        self.agent_id = agent_id
        self._n_actions = n_actions
        self._seed = seed
        self._rng = np.random.default_rng(seed)

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id) -> "RandomAgent":
        return cls(agent_id, n_actions, seed)

    def act(self, obs: np.ndarray, info: Any, *, explore: bool) -> int:
        return int(self._rng.integers(self._n_actions))

    def observe(self, t: Any) -> dict[str, float]:
        return {}

    def save(self, path: Path) -> None:
        (path / SEED_FILE).write_text(yaml.safe_dump({"seed": self._seed}))

    @classmethod
    def load(cls, path: Path) -> "RandomAgent":
        meta = yaml.safe_load((path / META_FILE).read_text())
        seed = yaml.safe_load((path / SEED_FILE).read_text())["seed"]
        return cls(meta["agent_id"], meta["n_actions"], seed)
