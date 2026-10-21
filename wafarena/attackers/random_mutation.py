"""RandomMutationAttacker: applies random mutations then sends, within a fixed budget."""

import numpy as np

from wafarena.mutations.payload import Payload
from wafarena.mutations.registry import REGISTRY

DEFAULT_MAX_MUTATIONS = 5


class RandomMutationAttacker:
    def __init__(self, max_mutations: int = DEFAULT_MAX_MUTATIONS) -> None:
        self._max_mutations = max_mutations
        self._payload: Payload | None = None
        self._rng: np.random.Generator | None = None
        self._budget = 0

    def reset(self, base: Payload, endpoint: str, rng: np.random.Generator) -> None:
        self._payload = base
        self._rng = rng
        self._budget = int(rng.integers(self._max_mutations + 1))

    def next_request(self, last_response: int) -> Payload | None:
        if self._budget <= 0:
            return None
        self._budget -= 1
        operator = REGISTRY[int(self._rng.integers(len(REGISTRY)))]
        mutated = operator.apply(self._payload, self._rng)
        if mutated is not None:
            self._payload = mutated
        return self._payload
