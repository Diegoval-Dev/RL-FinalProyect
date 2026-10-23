"""Agent wrappers over the F1 scripted reference attackers, for the RQ1 table (F2-T09).

`CorpusReplayAttacker` and `RandomMutationAttacker` (agentes-y-checkpoints.md) speak a different
protocol (`next_request` returns a whole `Payload` to send next) than `Attacker-v0`'s discrete
mutate/SEND actions. `ScriptedAgent` reimplements their exact decision rule directly in terms of
those actions, so `corpus-replay` and `random-mutation` can run through the same
`attacker-eval-v1` harness as every learned method, for a fair side-by-side comparison.
"""

from pathlib import Path
from typing import Any

import numpy as np

from wafarena.agents.base import Transition
from wafarena.attackers.random_mutation import DEFAULT_MAX_MUTATIONS
from wafarena.envs.attacker_env import SEND_ACTION

VARIANTS = ("corpus_replay", "random_mutation")


class ScriptedAgent:
    role = "attacker"

    def __init__(
        self, agent_id: str, seed: int, *, variant: str, max_mutations: int = DEFAULT_MAX_MUTATIONS
    ):
        if variant not in VARIANTS:
            raise ValueError(f"unknown scripted variant {variant!r}, expected one of {VARIANTS}")
        self.agent_id = agent_id
        self._variant, self._max_mutations = variant, max_mutations
        self._rng = np.random.default_rng(seed)
        self._budget: int | None = None

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id) -> "ScriptedAgent":
        return cls(agent_id, seed, **params)

    def act(self, obs: np.ndarray, info: dict[str, Any], *, explore: bool) -> int:
        if self._variant == "corpus_replay":
            return SEND_ACTION
        mutations = int(info.get("mutations", 0))
        if mutations == 0:  # a fresh episode: resample the budget, like reset() does
            self._budget = 1 + int(self._rng.integers(self._max_mutations))
        if mutations < self._budget:
            return int(self._rng.integers(SEND_ACTION))
        return SEND_ACTION

    def observe(self, t: Transition) -> dict[str, float]:
        return {}

    def save(self, path: Path) -> None:
        return None

    @classmethod
    def load(cls, path: Path) -> "ScriptedAgent":
        raise NotImplementedError("ScriptedAgent has nothing learned to checkpoint")
