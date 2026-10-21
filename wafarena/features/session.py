"""Session (indices 16-20) and window (21-36) features of the defender observation.

A SessionTracker accumulates the requests of one session and exposes the session-level block and
the window over the last WINDOW_SIZE requests. See features.md.
"""

import math
from collections import deque
from dataclasses import dataclass

from wafarena.features.request import (
    SESSION_LEN_NORM,
    RequestInput,
    request_features,
)

SESSION_FEATURE_NAMES: tuple[str, ...] = (
    "req_rate",
    "prior_denials",
    "prior_captcha_fail",
    "session_len",
    "sql_kw_frac",
)

WINDOW_SIZE = 4
REQ_RATE_WINDOW_SECONDS = 10.0
REQ_RATE_DIVISOR = 50
PRIOR_DENIALS_DIVISOR = 10
CAPTCHA_FAIL_DIVISOR = 5
SQL_KW_INDEX = 3
ENTROPY_INDEX = 1
SPECIAL_RATIO_INDEX = 2


@dataclass
class _PastRequest:
    entropy: float
    special_ratio: float
    modsec_pl2: float
    was_denied: float
    had_sql_kw: bool


class SessionTracker:
    def __init__(self) -> None:
        self._history: list[_PastRequest] = []
        self._window: deque[_PastRequest] = deque(maxlen=WINDOW_SIZE)
        self._captcha_failures = 0

    def record(
        self,
        request: RequestInput,
        modsec_pl2: float,
        allowed: bool,
        captcha_failed: bool = False,
    ) -> None:
        features = request_features(request)
        past = _PastRequest(
            entropy=features[ENTROPY_INDEX],
            special_ratio=features[SPECIAL_RATIO_INDEX],
            modsec_pl2=modsec_pl2,
            was_denied=0.0 if allowed else 1.0,
            had_sql_kw=features[SQL_KW_INDEX] > 0,
        )
        self._history.append(past)
        self._window.appendleft(past)
        if captcha_failed:
            self._captcha_failures += 1

    def session_features(self) -> tuple[float, ...]:
        n = len(self._history)
        denials = sum(p.was_denied for p in self._history)
        sql_kw = sum(p.had_sql_kw for p in self._history)
        return (
            min(1.0, n / REQ_RATE_DIVISOR),
            min(1.0, denials / PRIOR_DENIALS_DIVISOR),
            min(1.0, self._captcha_failures / CAPTCHA_FAIL_DIVISOR),
            min(1.0, math.log1p(n) / SESSION_LEN_NORM),
            (sql_kw / n) if n else 0.0,
        )

    def window_features(self) -> tuple[float, ...]:
        values: list[float] = []
        for i in range(WINDOW_SIZE):
            if i < len(self._window):
                past = self._window[i]
                values.extend([past.entropy, past.special_ratio, past.modsec_pl2, past.was_denied])
            else:
                values.extend([0.0, 0.0, 0.0, 0.0])
        return tuple(values)
