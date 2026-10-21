"""F1-T03: the app role cannot read or write oracle_log; the logger role can."""

import uuid

import psycopg
import pytest

pytestmark = pytest.mark.lab


def test_app_role_cannot_read_oracle_log(app_db):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_db.execute("SELECT 1 FROM oracle_log")


def test_app_role_cannot_write_oracle_log(app_db):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_db.execute(
            "INSERT INTO oracle_log (request_id, endpoint, sql, rows_returned) "
            "VALUES ('forged', 'forged', 'forged', 0)"
        )


def test_logger_role_can_insert_and_read_oracle_log(logger_db, admin_db):
    request_id = f"f103-role-{uuid.uuid4().hex}"
    logger_db.execute(
        "INSERT INTO oracle_log (request_id, endpoint, sql, rows_returned) "
        "VALUES (%s, 'roles-test', 'SELECT 1', 0)",
        (request_id,),
    )

    found = logger_db.execute(
        "SELECT count(*) FROM oracle_log WHERE request_id = %s", (request_id,)
    ).fetchone()[0]
    admin_db.execute("DELETE FROM oracle_log WHERE request_id = %s", (request_id,))
    assert found == 1


def test_app_role_can_read_canary_secrets(app_db):
    # Required so that a union payload can leak the token; the oracle decides from the leak.
    assert app_db.execute("SELECT token FROM canary_secrets").fetchall()
