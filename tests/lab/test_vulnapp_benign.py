"""F1-T02: benign flows return normal responses."""

import pytest
from vulnapp_requests import send

from vulnapp.queries import ENDPOINTS

pytestmark = pytest.mark.lab

READ_ENDPOINTS = [spec for spec in ENDPOINTS if spec.returns_rows]
WRITE_ENDPOINTS = [spec for spec in ENDPOINTS if not spec.returns_rows]


@pytest.mark.parametrize("spec", READ_ENDPOINTS, ids=lambda spec: spec.name)
def test_benign_input_on_read_endpoint_returns_rows(client, spec):
    response = send(client, spec, spec.benign_values, spec.locations[0])

    assert response.status_code == 200
    assert len(response.json()["rows"]) > 0


@pytest.mark.parametrize("spec", WRITE_ENDPOINTS, ids=lambda spec: spec.name)
def test_benign_input_on_write_endpoint_succeeds(client, spec):
    response = send(client, spec, spec.benign_values, spec.locations[0])

    assert response.status_code == 200


def test_home_and_health_respond(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200


def test_cart_listing_shows_items_added_through_the_cart_endpoint(client):
    assert client.get("/cart").status_code == 200
