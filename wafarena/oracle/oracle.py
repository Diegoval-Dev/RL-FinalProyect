import os
import uuid
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from vulnapp.db import APP_DATABASE_URL_ENV, SET_REQUEST_ID_SQL, serialize_rows
from vulnapp.queries import build_sql, find_endpoint
from wafarena.mutations.payload import Payload
from wafarena.oracle.decision import OracleResult, decide
from wafarena.oracle.sql import fingerprint

ORACLE_DATABASE_URL_ENV = "ORACLE_DATABASE_URL"
TOKEN_SQL = "SELECT token FROM canary_secrets"
COUNT_WRITES_SQL = "SELECT count_canary_writes(%s)"
LOG_ENTRIES_SQL = (
    "SELECT endpoint, sql, error, rows_json::text FROM oracle_log WHERE request_id = %s"
)
DIRECT_REQUEST_PREFIX = "direct-"


@dataclass(frozen=True)
class Execution:
    error: str | None
    response_text: str
    canary_writes: int


NOTHING_EXECUTED = Execution(error=None, response_text="", canary_writes=0)


class Oracle:
    """Decides whether a payload is functional and had an effect, see oraculo.md."""

    def __init__(self, app_dsn: str | None = None, oracle_dsn: str | None = None):
        self._app_dsn = app_dsn
        self._oracle_dsn = oracle_dsn
        self._token: str | None = None
        self._app_connection: psycopg.Connection | None = None

    def check_direct(self, payload: Payload, endpoint: str, param: str) -> OracleResult:
        spec = find_endpoint(endpoint)
        template = fingerprint(build_sql(spec, spec.benign_values))
        sql = build_sql(spec, {**spec.benign_values, param: payload.text})
        sql_fingerprint = fingerprint(sql)
        execution = (
            self._execute_in_rollback(sql) if sql_fingerprint is not None else NOTHING_EXECUTED
        )
        return decide(
            sql_fingerprint,
            template,
            execution.error,
            execution.response_text,
            execution.canary_writes,
            self.token,
        )

    def check_request(self, request_id: str) -> OracleResult:
        entries = self._log_entries(request_id)
        if not entries:
            return OracleResult(False, False, "none", "no oracle_log entry for request")
        if len(entries) > 1:
            raise ValueError(f"request {request_id} has {len(entries)} logged queries")
        endpoint, sql, error, rows_json = entries[0]
        spec = find_endpoint(endpoint)
        if spec is None:
            return OracleResult(False, False, "none", "endpoint has no template")
        return decide(
            fingerprint(sql),
            fingerprint(build_sql(spec, spec.benign_values)),
            error,
            rows_json,
            self._count_writes(request_id),
            self.token,
        )

    @property
    def token(self) -> str:
        if self._token is None:
            with self._oracle_connection() as connection:
                self._token = connection.execute(TOKEN_SQL).fetchone()[0]
        return self._token

    def _execute_in_rollback(self, sql: str) -> Execution:
        try:
            return self._run_in_rollback(sql)
        except psycopg.OperationalError:
            self._drop_app_connection()  # the lab restarted or the link dropped: retry once
            return self._run_in_rollback(sql)

    def _run_in_rollback(self, sql: str) -> Execution:
        request_id = f"{DIRECT_REQUEST_PREFIX}{uuid.uuid4().hex}"
        connection = self._app_connection_for_use()
        try:
            connection.execute(SET_REQUEST_ID_SQL, (request_id,))
            cursor = connection.execute(sql)
            rows = cursor.fetchall() if cursor.description else []
            writes = connection.execute(COUNT_WRITES_SQL, (request_id,)).fetchone()[
                "count_canary_writes"
            ]
            return Execution(None, serialize_rows(rows), writes)
        except psycopg.Error as error:
            if connection.broken:
                raise  # a dead link is not a SQL error; the caller reconnects
            return Execution(str(error), "", 0)
        finally:
            if not connection.broken and not connection.closed:
                self._reset_session(connection)

    @staticmethod
    def _reset_session(connection: psycopg.Connection) -> None:
        """Undo the check completely: roll back and drop session state a stacked payload could
        leave behind (prepared statements, temp tables), so checks stay independent."""
        connection.rollback()
        connection.autocommit = True
        try:
            connection.execute("DISCARD ALL")
        finally:
            connection.autocommit = False

    def _app_connection_for_use(self) -> psycopg.Connection:
        """One persistent connection: opening one per payload dominated the cost of a check."""
        if self._app_connection is None or self._app_connection.closed:
            dsn = self._app_dsn or os.environ[APP_DATABASE_URL_ENV]
            self._app_connection = psycopg.connect(dsn, autocommit=False, row_factory=dict_row)
        return self._app_connection

    def _drop_app_connection(self) -> None:
        if self._app_connection is not None:
            try:
                self._app_connection.close()
            except psycopg.Error:
                pass
        self._app_connection = None

    def close(self) -> None:
        self._drop_app_connection()

    def _log_entries(self, request_id: str) -> list[tuple]:
        with self._oracle_connection() as connection:
            return connection.execute(LOG_ENTRIES_SQL, (request_id,)).fetchall()

    def _count_writes(self, request_id: str) -> int:
        with self._oracle_connection() as connection:
            return connection.execute(COUNT_WRITES_SQL, (request_id,)).fetchone()[0]

    def _oracle_connection(self) -> psycopg.Connection:
        dsn = self._oracle_dsn or os.environ[ORACLE_DATABASE_URL_ENV]
        return psycopg.connect(dsn, autocommit=True)
