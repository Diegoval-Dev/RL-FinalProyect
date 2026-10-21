"""F1-T04: the decision table of oraculo.md, one case per row, plus precedence."""

import pytest

from wafarena.oracle.decision import OracleResult, decide

TOKEN = "Zk3pQ9vL2mXc7RtYb8NwHd4JfG6sAe1U"
TEMPLATE = "template-fingerprint"
PAYLOAD = "payload-fingerprint"
NO_ROWS = "[]"


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            dict(fingerprint=None, error=None, response_text=NO_ROWS, canary_writes=0),
            OracleResult(False, False, "syntax_error", "SQL does not parse"),
        ),
        (
            dict(fingerprint=TEMPLATE, error=None, response_text=NO_ROWS, canary_writes=0),
            OracleResult(False, False, "none", "payload stayed a literal"),
        ),
        (
            dict(
                fingerprint=PAYLOAD,
                error=None,
                response_text=f'[{{"t": "{TOKEN}"}}]',
                canary_writes=0,
            ),
            OracleResult(True, True, "canary_leak", "token in response"),
        ),
        (
            dict(fingerprint=PAYLOAD, error=None, response_text=NO_ROWS, canary_writes=1),
            OracleResult(True, True, "canary_write", "row written to canary_writes"),
        ),
        (
            dict(
                fingerprint=PAYLOAD,
                error=f"invalid input: {TOKEN}",
                response_text="",
                canary_writes=0,
            ),
            OracleResult(True, True, "canary_error", "token in database error"),
        ),
        (
            dict(fingerprint=PAYLOAD, error=None, response_text=NO_ROWS, canary_writes=0),
            OracleResult(True, True, "structure_change", "different structure, no error"),
        ),
        (
            dict(
                fingerprint=PAYLOAD,
                error="syntax error at or near",
                response_text="",
                canary_writes=0,
            ),
            OracleResult(False, False, "syntax_error", "execution error without canary"),
        ),
    ],
    ids=[
        "unparsable",
        "literal",
        "leak",
        "write",
        "canary-error",
        "structure",
        "error-without-canary",
    ],
)
def test_decide_follows_contract_table(kwargs, expected):
    result = decide(template_fingerprint=TEMPLATE, token=TOKEN, **kwargs)

    assert result == expected


def test_decide_reports_leak_before_write_when_both_occur():
    result = decide(
        fingerprint=PAYLOAD,
        template_fingerprint=TEMPLATE,
        error=None,
        response_text=TOKEN,
        canary_writes=1,
        token=TOKEN,
    )

    assert result.evidence == "canary_leak"
