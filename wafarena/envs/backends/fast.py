"""FastBackend: in-process oracle checks and cached ModSecurity scores (ADR-0005).

Functional checks are memoized in process (deterministic per payload); ModSecurity scores are read
from the four PL instances over HTTP and cached on disk, so a warm cache makes each step a lookup.
"""

from collections.abc import Callable
from urllib.parse import urlencode

from vulnapp.queries import get_endpoint
from wafarena.defenders.modsec import modsec_score
from wafarena.envs.backends.base import BackendResult
from wafarena.envs.backends.cache import ModSecCache
from wafarena.features.modsec import PARANOIA_LEVELS
from wafarena.mutations.payload import Payload
from wafarena.oracle import Oracle, OracleResult


class FastBackend:
    def __init__(
        self,
        oracle: Oracle | None = None,
        cache: ModSecCache | None = None,
        score_fn: Callable = modsec_score,
    ):
        self._oracle = oracle or Oracle()
        self._cache = cache or ModSecCache()
        self._score_fn = score_fn
        self._functional: dict[tuple[str, str, str], OracleResult] = {}

    def check_functional(self, payload: Payload, endpoint: str, param: str) -> OracleResult:
        key = (endpoint, param, payload.text)
        if key not in self._functional:
            self._functional[key] = self._oracle.check_direct(payload, endpoint, param)
        return self._functional[key]

    def probe(self, payload: Payload, endpoint: str, param: str) -> BackendResult:
        oracle_result = self.check_functional(payload, endpoint, param)
        scores, blocks = self._modsec(payload, endpoint, param)
        return BackendResult(oracle_result, scores, blocks)

    def _request_path(self, payload: Payload, endpoint: str, param: str) -> str:
        spec = get_endpoint(endpoint)
        values = {**spec.benign_values, param: payload.text}
        return f"{spec.path}?{urlencode(values)}"

    def _modsec(self, payload: Payload, endpoint: str, param: str):
        path = self._request_path(payload, endpoint, param)
        scores, blocks = {}, {}
        for pl in PARANOIA_LEVELS:
            cached = self._cache.get(pl, "GET", path)
            if cached is None:
                entry = self._score_fn("GET", path, pl)
                self._cache.put(pl, "GET", path, entry.score, entry.would_block)
                cached = (entry.score, entry.would_block)
            scores[pl], blocks[pl] = cached[0], cached[1]
        return scores, blocks

    def close(self) -> None:
        self._cache.flush()
