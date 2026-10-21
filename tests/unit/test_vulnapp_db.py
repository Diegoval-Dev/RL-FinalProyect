"""F1-T03: oracle_log rows are derived from the executed query and its outcome."""

from vulnapp.db import QueryOutcome, QueryRecord, record_parameters


def test_record_parameters_counts_returned_rows_when_query_succeeds():
    record = QueryRecord(
        "req-1", "search", "SELECT 1", QueryOutcome(rows=[{"a": 1}, {"a": 2}], error=None)
    )

    assert record_parameters(record) == ("req-1", "search", "SELECT 1", None, 2)


def test_record_parameters_keeps_error_and_zero_rows_when_query_fails():
    record = QueryRecord("req-2", "product", "SELECT x", QueryOutcome(rows=[], error="boom"))

    assert record_parameters(record) == ("req-2", "product", "SELECT x", "boom", 0)
