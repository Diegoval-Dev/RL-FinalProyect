import logging
import os
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

DATABASE_URL_ENV = "DATABASE_URL"


@dataclass(frozen=True)
class QueryOutcome:
    rows: list[dict]
    error: str | None


class PostgresRunner:
    """Runs one SQL string per connection; statements may be stacked when no params are given."""

    def __init__(self, dsn: str | None = None):
        self._dsn = dsn

    def __call__(self, sql: str, params: tuple | None = None) -> QueryOutcome:
        dsn = self._dsn or os.environ[DATABASE_URL_ENV]
        try:
            with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as connection:
                connection.prepare_threshold = None
                cursor = connection.execute(sql, params)
                rows = cursor.fetchall() if cursor.description else []
        except psycopg.Error as error:
            logger.info("query failed: %s", error)
            return QueryOutcome(rows=[], error=str(error))
        return QueryOutcome(rows=rows, error=None)
