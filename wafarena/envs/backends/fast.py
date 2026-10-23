"""FastBackend: in-process oracle checks and cached ModSecurity scores (ADR-0005).

Functional checks are memoized in process (deterministic per payload); ModSecurity scores are read
from the four PL instances over HTTP and cached on disk, so a warm cache makes each step a lookup.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
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
        self._pool = ThreadPoolExecutor(max_workers=len(PARANOIA_LEVELS))

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
        found = {pl: self._cache.get(pl, "GET", path) for pl in PARANOIA_LEVELS}
        missing = [pl for pl, value in found.items() if value is None]
        # the paranoia-level instances are independent: query the uncached ones concurrently
        entries = self._pool.map(lambda pl: self._score_fn("GET", path, pl), missing)
        for pl, entry in zip(missing, entries, strict=True):
            self._cache.put(pl, "GET", path, entry.score, entry.would_block)
            found[pl] = (entry.score, entry.would_block)
        scores = {pl: found[pl][0] for pl in PARANOIA_LEVELS}
        blocks = {pl: found[pl][1] for pl in PARANOIA_LEVELS}
        return scores, blocks

    def cache_stats(self) -> dict[str, float]:
        total = self._cache.hits + self._cache.misses
        return {
            "hits": self._cache.hits,
            "misses": self._cache.misses,
            "hit_rate": self._cache.hits / total if total else 0.0,
        }

    def close(self) -> None:
        self._pool.shutdown(wait=True)
        self._cache.flush()
