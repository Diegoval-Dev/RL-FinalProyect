"""F1-T04: the oracle compares the structure of SQL through pglast fingerprints."""

from wafarena.oracle.sql import fingerprint


def test_fingerprint_ignores_literal_values_when_structure_is_equal():
    assert fingerprint("SELECT id FROM products WHERE name = 'a'") == fingerprint(
        "SELECT id FROM products WHERE name = 'b'"
    )


def test_fingerprint_changes_when_injected_clause_changes_structure():
    assert fingerprint("SELECT id FROM products WHERE id = 3") != fingerprint(
        "SELECT id FROM products WHERE id = 3 OR 1=1"
    )


def test_fingerprint_returns_none_when_sql_does_not_parse():
    assert fingerprint("SELECT id FROM products WHERE name = 'a") is None
