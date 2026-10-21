"""ModSecDefender: a DefenderPolicy that mirrors a ModSecurity paranoia level.

It blocks exactly when CRS at that PL would block. The observation carries the normalized inbound
anomaly score at indices 12-15 (score / 50); CRS blocks at the inbound threshold (default 5), so the
policy blocks when the de-normalized score reaches that threshold.
"""

import numpy as np

from wafarena.defenders.base import Action
from wafarena.features.modsec import MODSEC_SCORE_DIVISOR, modsec_feature_index

CRS_INBOUND_THRESHOLD = 5


class ModSecDefender:
    def __init__(self, paranoia_level: int):
        self._index = modsec_feature_index(paranoia_level)
        self._threshold = CRS_INBOUND_THRESHOLD / MODSEC_SCORE_DIVISOR

    def reset_session(self, session_id: str) -> None:
        return None

    def act(self, obs: np.ndarray) -> int:
        score = float(obs[self._index])
        return int(Action.BLOCK) if score >= self._threshold else int(Action.ALLOW)
