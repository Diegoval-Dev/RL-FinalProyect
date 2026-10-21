"""F1-T03: no legitimate request returns the canary token; a tautology does."""

import re

import pytest
from vulnapp_requests import send

from vulnapp.queries import ENDPOINTS, get_endpoint

pytestmark = pytest.mark.lab

BENIGN_CASES = [(spec, location) for spec in ENDPOINTS for location in spec.locations]
BENIGN_FLOW_PATHS = ["/", "/comments?product_id=1", "/cart"]
TAUTOLOGY_CATALOG_INPUT = "' OR '1'='1' --"
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]{32}")


def test_canary_token_is_32_random_alphanumeric_characters(canary_token):
    assert TOKEN_PATTERN.fullmatch(canary_token)


def test_hidden_product_row_carries_the_canary_token(admin_db, canary_token):
    hidden_rows = admin_db.execute(
        "SELECT count(*) FROM products WHERE hidden AND name LIKE %s", (f"%{canary_token}%",)
    ).fetchone()[0]

    assert hidden_rows == 1


@pytest.mark.parametrize(("spec", "location"), BENIGN_CASES, ids=lambda v: getattr(v, "name", v))
def test_benign_input_never_returns_canary_token(client, canary_token, spec, location):
    response = send(client, spec, spec.benign_values, location)

    assert canary_token not in response.text


@pytest.mark.parametrize("path", BENIGN_FLOW_PATHS)
def test_benign_flow_never_returns_canary_token(client, canary_token, path):
    assert canary_token not in client.get(path).text


def test_tautology_on_catalog_exposes_the_hidden_canary_row(client, canary_token):
    spec = get_endpoint("catalog")

    response = send(client, spec, {"category": TAUTOLOGY_CATALOG_INPUT}, "query")

    assert canary_token in response.text
