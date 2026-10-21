from dataclasses import dataclass
from typing import Literal

Evidence = Literal[
    "structure_change", "canary_leak", "canary_write", "canary_error", "none", "syntax_error"
]


@dataclass(frozen=True)
class OracleResult:
    functional: bool
    effect: bool
    evidence: Evidence
    detail: str


def decide(
    fingerprint: str | None,
    template_fingerprint: str,
    error: str | None,
    response_text: str,
    canary_writes: int,
    token: str,
) -> OracleResult:
    if fingerprint is None:
        return OracleResult(False, False, "syntax_error", "SQL does not parse")
    if fingerprint == template_fingerprint:
        return OracleResult(False, False, "none", "payload stayed a literal")
    if token in response_text:
        return OracleResult(True, True, "canary_leak", "token in response")
    if error is None and canary_writes > 0:
        return OracleResult(True, True, "canary_write", "row written to canary_writes")
    if error is None:
        return OracleResult(True, True, "structure_change", "different structure, no error")
    if token in error:
        return OracleResult(True, True, "canary_error", "token in database error")
    return OracleResult(False, False, "syntax_error", "execution error without canary")
