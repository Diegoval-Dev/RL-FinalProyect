"""DefenderPolicy protocol and the five defender actions.

See env-defensor.md and agentes-y-checkpoints.md.
"""

from enum import IntEnum
from typing import Protocol

import numpy as np


class Action(IntEnum):
    ALLOW = 0
    BLOCK = 1
    CAPTCHA = 2
    RATE_LIMIT = 3
    HONEYPOT = 4


class DefenderPolicy(Protocol):
    def reset_session(self, session_id: str) -> None: ...
    def act(self, obs: np.ndarray) -> int: ...
