"""Parsing of the OWASP CRS audit log (JSON) to a per-request anomaly score and block flag.

CRS runs in anomaly-scoring mode. Each matched rule contributes to the inbound anomaly score by
its severity; the evaluation rules (9xx) only report the accumulated total, so they are skipped
when reconstructing the score. The block decision is CRS's own `is_interrupted`.
"""

import json
from dataclasses import dataclass

PARANOIA_LEVELS: tuple[int, ...] = (1, 2, 3, 4)
REQUEST_ID_HEADER = "X-Request-ID"
EVALUATION_RULE_PREFIXES = ("949", "959", "980")
SEVERITY_SCORE = {"2": 5, "3": 4, "4": 3, "5": 2}


@dataclass(frozen=True)
class AuditEntry:
    request_id: str
    score: int
    would_block: bool
    http_code: int


def score_from_messages(messages: list[dict]) -> int:
    total = 0
    for message in messages:
        details = message.get("details", {})
        rule_id = str(details.get("ruleId", ""))
        if rule_id.startswith(EVALUATION_RULE_PREFIXES):
            continue
        total += SEVERITY_SCORE.get(str(details.get("severity", "")), 0)
    return total


def parse_audit_line(line: str) -> AuditEntry | None:
    line = line.strip()
    if not line.startswith("{"):
        return None
    try:
        transaction = json.loads(line)["transaction"]
    except (json.JSONDecodeError, KeyError):
        return None
    request_id = transaction.get("request", {}).get("headers", {}).get(REQUEST_ID_HEADER)
    if not request_id:
        return None
    return AuditEntry(
        request_id=request_id,
        score=score_from_messages(transaction.get("messages", [])),
        would_block=bool(transaction.get("is_interrupted", False)),
        http_code=int(transaction.get("response", {}).get("http_code", 0)),
    )
