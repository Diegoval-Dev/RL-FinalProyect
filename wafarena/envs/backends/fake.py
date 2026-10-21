"""Deterministic in-memory backend for tests without the Docker lab.

Effect is True when the payload text contains a SQL metacharacter; functional mirrors effect; the
ModSecurity score is a deterministic function of the text so scores and blocks are reproducible.
"""

from wafarena.envs.backends.base import BackendResult
from wafarena.features.modsec import PARANOIA_LEVELS
from wafarena.mutations.payload import Payload
from wafarena.oracle import OracleResult

SQL_MARKERS = ("'", "--", "union", "or 1", "=", ";")
BLOCK_SCORE = 5


class FakeBackend:
    def _looks_malicious(self, text: str) -> bool:
        lowered = text.lower()
        return any(marker in lowered for marker in SQL_MARKERS)

    def check_functional(self, payload: Payload, endpoint: str, param: str) -> OracleResult:
        malicious = self._looks_malicious(payload.text)
        evidence = "structure_change" if malicious else "none"
        return OracleResult(malicious, malicious, evidence, "fake")

    def probe(self, payload: Payload, endpoint: str, param: str) -> BackendResult:
        oracle = self.check_functional(payload, endpoint, param)
        score = len(payload.text) % 10 + (BLOCK_SCORE if self._looks_malicious(payload.text) else 0)
        scores = {pl: score + pl for pl in PARANOIA_LEVELS}
        blocks = {pl: scores[pl] >= BLOCK_SCORE for pl in PARANOIA_LEVELS}
        return BackendResult(oracle, scores, blocks)

    def close(self) -> None:
        return None
