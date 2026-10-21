"""F1-T05: anomaly score and block flag are derived from the ModSecurity audit log."""

import json

from wafarena.defenders.audit import (
    PARANOIA_LEVELS,
    AuditEntry,
    parse_audit_line,
    score_from_messages,
)

CRITICAL_SQLI_MESSAGE = {
    "message": "SQL Injection Attack Detected via libinjection",
    "details": {"ruleId": "942100", "severity": "2"},
}
BLOCKING_EVAL_MESSAGE = {
    "message": "Inbound Anomaly Score Exceeded (Total Score: 5)",
    "details": {"ruleId": "949110", "severity": "0"},
}
NOTICE_MESSAGE = {"message": "Rule notice", "details": {"ruleId": "920990", "severity": "5"}}


def audit_line(request_id: str, messages: list[dict], interrupted: bool) -> str:
    return json.dumps(
        {
            "transaction": {
                "unique_id": "abc",
                "is_interrupted": interrupted,
                "request": {"headers": {"X-Request-ID": request_id}},
                "response": {"http_code": 403 if interrupted else 200},
                "messages": messages,
            }
        }
    )


def test_paranoia_levels_are_one_to_four():
    assert PARANOIA_LEVELS == (1, 2, 3, 4)


def test_score_from_messages_sums_severity_contributions_ignoring_evaluation_rules():
    assert score_from_messages([CRITICAL_SQLI_MESSAGE, BLOCKING_EVAL_MESSAGE]) == 5


def test_score_from_messages_is_zero_without_matched_rules():
    assert score_from_messages([]) == 0


def test_score_from_messages_adds_notice_contribution():
    assert score_from_messages([NOTICE_MESSAGE]) == 2


def test_parse_audit_line_extracts_request_id_score_and_block():
    entry = parse_audit_line(
        audit_line("req-1", [CRITICAL_SQLI_MESSAGE, BLOCKING_EVAL_MESSAGE], True)
    )

    assert entry == AuditEntry(request_id="req-1", score=5, would_block=True, http_code=403)


def test_parse_audit_line_marks_benign_request_without_block():
    entry = parse_audit_line(audit_line("req-2", [], False))

    assert entry == AuditEntry(request_id="req-2", score=0, would_block=False, http_code=200)


def test_parse_audit_line_returns_none_for_non_json():
    assert parse_audit_line("not json") is None


def test_parse_audit_line_returns_none_without_request_id():
    line = json.dumps({"transaction": {"is_interrupted": False, "request": {"headers": {}}}})

    assert parse_audit_line(line) is None
