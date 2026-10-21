"""F1-T04: check_request reads oracle_log by X-Request-ID and reports the evidence."""

import uuid

import pytest
from vulnapp_requests import send

from vulnapp.queries import get_endpoint
from wafarena.mutations.payload import Payload
from wafarena.oracle import Oracle

pytestmark = pytest.mark.lab

REQUEST_ID_HEADER = "X-Request-ID"
CANARY_UNION_SEARCH = "' UNION SELECT id, token, 0 FROM canary_secrets --"
CANARY_WRITE_STACKED = "1); INSERT INTO canary_writes DEFAULT VALUES; --"


@pytest.fixture(scope="session")
def oracle():
    return Oracle()


def fresh_request_id() -> str:
    return f"f104-{uuid.uuid4().hex}"


def test_union_over_canary_table_is_reported_as_canary_leak(client, oracle):
    spec = get_endpoint("search")
    request_id = fresh_request_id()
    send(client, spec, {"q": CANARY_UNION_SEARCH}, "json", headers={REQUEST_ID_HEADER: request_id})

    result = oracle.check_request(request_id)

    assert (result.effect, result.evidence) == (True, "canary_leak")


def test_stacked_canary_insert_is_reported_as_canary_write(client, oracle):
    spec = get_endpoint("cart_add")
    request_id = fresh_request_id()
    values = {**spec.benign_values, "qty": CANARY_WRITE_STACKED}
    send(client, spec, values, "form", headers={REQUEST_ID_HEADER: request_id})

    result = oracle.check_request(request_id)

    assert (result.effect, result.evidence) == (True, "canary_write")


def test_stacked_canary_insert_direct_check_leaves_no_row_behind(oracle, admin_db):
    spec = get_endpoint("cart_add")
    writes_before = admin_db.execute("SELECT count(*) FROM canary_writes").fetchone()[0]

    result = oracle.check_direct(Payload(CANARY_WRITE_STACKED, "form", 0), spec.name, "qty")

    writes_after = admin_db.execute("SELECT count(*) FROM canary_writes").fetchone()[0]
    assert result.evidence == "canary_write"
    assert writes_after == writes_before


def test_benign_request_is_reported_without_effect(client, oracle):
    spec = get_endpoint("search")
    request_id = fresh_request_id()
    send(client, spec, spec.benign_values, "query", headers={REQUEST_ID_HEADER: request_id})

    result = oracle.check_request(request_id)

    assert (result.effect, result.evidence) == (False, "none")


def test_request_without_log_entry_is_reported_without_effect(oracle):
    result = oracle.check_request(fresh_request_id())

    assert (result.functional, result.effect, result.evidence) == (False, False, "none")
