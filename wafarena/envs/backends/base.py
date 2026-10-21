"""Backend interface: the world the environments query (oracle effect + ModSecurity scores).

Two speeds (ADR-0005): FastBackend runs oracle checks in-process and batches ModSecurity over HTTP
with a persistent cache; RealBackend goes through the proxy. The defender decision is not here — the
environment owns the policy; the backend only reports oracle and ModSecurity signals.
"""

from dataclasses import dataclass
from typing import Protocol

from wafarena.features.modsec import PARANOIA_LEVELS
from wafarena.mutations.payload import Payload
from wafarena.oracle import OracleResult


@dataclass(frozen=True)
class BackendResult:
    oracle: OracleResult
    modsec_scores: dict[int, int]
    modsec_block: dict[int, bool]


class Backend(Protocol):
    def check_functional(self, payload: Payload, endpoint: str, param: str) -> OracleResult: ...
    def probe(self, payload: Payload, endpoint: str, param: str) -> BackendResult: ...
    def close(self) -> None: ...


def empty_scores() -> dict[int, int]:
    return {pl: 0 for pl in PARANOIA_LEVELS}
