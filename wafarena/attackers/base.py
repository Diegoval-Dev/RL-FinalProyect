"""AttackerPolicy protocol and the observable response classes (env-atacante.md)."""

from enum import IntEnum
from typing import Protocol

import numpy as np

from wafarena.mutations.payload import Payload


class Response(IntEnum):
    NONE = 0
    PASS_EFFECT = 1
    PASS_NO_EFFECT = 2
    BLOCKED = 3
    CAPTCHA = 4
    RATE_LIMITED = 5


class AttackerPolicy(Protocol):
    def reset(self, base: Payload, endpoint: str, rng: np.random.Generator) -> None: ...
    def next_request(self, last_response: int) -> Payload | None: ...
