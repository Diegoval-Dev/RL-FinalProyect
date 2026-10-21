"""F1-T03: every query executed by vulnapp is recorded in oracle_log under its X-Request-ID."""

import uuid

import pytest

from vulnapp.queries import build_sql, get_endpoint

pytestmark = pytest.mark.lab

REQUEST_ID_HEADER = "X-Request-ID"


def fresh_request_id() -> str:
    return f"f103-{uuid.uuid4().hex}"


def logged_rows(admin_db, request_id: str) -> list[tuple]:
    return admin_db.execute(
        "SELECT endpoint, sql, error, rows_returned FROM oracle_log WHERE request_id = %s",
        (request_id,),
    ).fetchall()


def test_successful_query_is_logged_once_with_its_request_id(client, admin_db):
    spec = get_endpoint("search")
    request_id = fresh_request_id()

    response = client.post(
        spec.path, json=spec.benign_values, headers={REQUEST_ID_HEADER: request_id}
    )

    assert response.status_code == 200
    assert logged_rows(admin_db, request_id) == [
        (spec.name, build_sql(spec, spec.benign_values), None, len(response.json()["rows"]))
    ]


def test_failed_query_is_logged_with_the_database_error(client, admin_db):
    request_id = fresh_request_id()

    response = client.get("/product", params={"id": "abc"}, headers={REQUEST_ID_HEADER: request_id})

    assert response.status_code == 500
    [(endpoint, _sql, error, rows_returned)] = logged_rows(admin_db, request_id)
    assert endpoint == "product"
    assert error
    assert rows_returned == 0


def test_injected_sql_is_logged_verbatim(client, admin_db):
    spec = get_endpoint("catalog")
    request_id = fresh_request_id()

    client.get(
        spec.path, params={"category": "' OR '1'='1' --"}, headers={REQUEST_ID_HEADER: request_id}
    )

    [(sql,)] = admin_db.execute(
        "SELECT sql FROM oracle_log WHERE request_id = %s", (request_id,)
    ).fetchall()
    assert "OR '1'='1'" in sql
