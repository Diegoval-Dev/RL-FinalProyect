"""CorpusReplayAttacker: sends the base payload unmutated once, then abandons (env-defensor.md)."""

import numpy as np

from wafarena.mutations.payload import Payload


class CorpusReplayAttacker:
    def __init__(self) -> None:
        self._base: Payload | None = None
        self._sent = False

    def reset(self, base: Payload, endpoint: str, rng: np.random.Generator) -> None:
        self._base = base
        self._sent = False

    def next_request(self, last_response: int) -> Payload | None:
        if self._sent:
            return None
        self._sent = True
        return self._base
