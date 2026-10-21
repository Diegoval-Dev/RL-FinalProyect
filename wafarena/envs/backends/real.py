"""RealBackend: oracle effect and ModSecurity scores obtained live over HTTP (ADR-0005).

Used for validation and the demo; no cache, so results reflect the running lab exactly.
"""

from collections.abc import Callable
from urllib.parse import urlencode

from vulnapp.queries import get_endpoint
from wafarena.defenders.modsec import modsec_score
from wafarena.envs.backends.base import BackendResult
from wafarena.features.modsec import PARANOIA_LEVELS
from wafarena.mutations.payload import Payload
from wafarena.oracle import Oracle, OracleResult


class RealBackend:
    def __init__(self, oracle: Oracle | None = None, score_fn: Callable = modsec_score):
        self._oracle = oracle or Oracle()
        self._score_fn = score_fn

    def check_functional(self, payload: Payload, endpoint: str, param: str) -> OracleResult:
        return self._oracle.check_direct(payload, endpoint, param)

    def probe(self, payload: Payload, endpoint: str, param: str) -> BackendResult:
        oracle_result = self.check_functional(payload, endpoint, param)
        spec = get_endpoint(endpoint)
        values = {**spec.benign_values, param: payload.text}
        path = f"{spec.path}?{urlencode(values)}"
        scores, blocks = {}, {}
        for pl in PARANOIA_LEVELS:
            entry = self._score_fn("GET", path, pl)
            scores[pl], blocks[pl] = entry.score, entry.would_block
        return BackendResult(oracle_result, scores, blocks)

    def close(self) -> None:
        return None
