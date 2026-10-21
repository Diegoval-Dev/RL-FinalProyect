import logging
import os
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

APP_DATABASE_URL_ENV = "APP_DATABASE_URL"
LOGGER_DATABASE_URL_ENV = "LOGGER_DATABASE_URL"
INSERT_ORACLE_LOG_SQL = (
    "INSERT INTO oracle_log (request_id, endpoint, sql, error, rows_returned) "
    "VALUES (%s, %s, %s, %s, %s)"
)


@dataclass(frozen=True)
class QueryOutcome:
    rows: list[dict]
    error: str | None


@dataclass(frozen=True)
class QueryRecord:
    request_id: str
    endpoint: str
    sql: str
    outcome: QueryOutcome


def record_parameters(record: QueryRecord) -> tuple:
    return (
        record.request_id,
        record.endpoint,
        record.sql,
        record.outcome.error,
        len(record.outcome.rows),
    )


class PostgresRunner:
    """Runs one SQL string per connection, as the app role; statements may be stacked."""

    def __init__(self, dsn: str | None = None):
        self._dsn = dsn

    def __call__(self, sql: str, params: tuple | None = None) -> QueryOutcome:
        dsn = self._dsn or os.environ[APP_DATABASE_URL_ENV]
        try:
            with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as connection:
                connection.prepare_threshold = None
                cursor = connection.execute(sql, params)
                rows = cursor.fetchall() if cursor.description else []
        except psycopg.Error as error:
            logger.info("query failed: %s", error)
            return QueryOutcome(rows=[], error=str(error))
        return QueryOutcome(rows=rows, error=None)


class OracleLog:
    """Writes each executed query to oracle_log as the logger role, unreadable by the app role."""

    def __init__(self, dsn: str | None = None):
        self._dsn = dsn

    def __call__(self, record: QueryRecord) -> None:
        dsn = self._dsn or os.environ[LOGGER_DATABASE_URL_ENV]
        with psycopg.connect(dsn, autocommit=True) as connection:
            connection.execute(INSERT_ORACLE_LOG_SQL, record_parameters(record))
