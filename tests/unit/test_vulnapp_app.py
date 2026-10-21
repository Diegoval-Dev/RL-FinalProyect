"""F1-T02: HTTP behavior of vulnapp with a fake database runner."""

import pytest
from fastapi.testclient import TestClient

from vulnapp.app import create_app
from vulnapp.db import QueryOutcome
from vulnapp.queries import ENDPOINTS, build_sql


class RecordingRunner:
    def __init__(self, outcome: QueryOutcome | None = None):
        self.outcome = outcome or QueryOutcome(rows=[{"id": 1}], error=None)
        self.calls: list[tuple[str, tuple | None]] = []

    def __call__(self, sql: str, params: tuple | None = None) -> QueryOutcome:
        self.calls.append((sql, params))
        return self.outcome


def send(client, spec, values, location):
    if location == "query":
        return client.get(spec.path, params=values)
    if location == "form":
        return client.post(spec.path, data=values)
    return client.post(spec.path, json=values)


def endpoint_locations():
    return [(spec, location) for spec in ENDPOINTS for location in spec.locations]


@pytest.fixture
def runner():
    return RecordingRunner()


@pytest.fixture
def client(runner):
    return TestClient(create_app(runner))


@pytest.mark.parametrize(
    ("spec", "location"), endpoint_locations(), ids=lambda v: getattr(v, "name", v)
)
def test_endpoint_accepts_every_declared_location_and_runs_concatenated_sql(
    client, runner, spec, location
):
    response = send(client, spec, spec.benign_values, location)

    assert response.status_code == 200
    assert runner.calls[-1] == (build_sql(spec, spec.benign_values), None)


@pytest.mark.parametrize("spec", ENDPOINTS, ids=lambda spec: spec.name)
def test_endpoint_rejects_params_sent_in_undeclared_location(client, runner, spec):
    undeclared = [loc for loc in ("query", "form", "json") if loc not in spec.locations]
    for location in undeclared:
        assert send(client, spec, spec.benign_values, location).status_code in (400, 405)
    assert runner.calls == []


@pytest.mark.parametrize("spec", ENDPOINTS, ids=lambda spec: spec.name)
def test_endpoint_with_missing_param_returns_400_without_touching_database(client, runner, spec):
    location = spec.locations[0]
    incomplete = dict(list(spec.benign_values.items())[:-1])

    assert send(client, spec, incomplete, location).status_code == 400
    assert runner.calls == []


def test_database_error_is_returned_verbatim_to_the_client():
    runner = RecordingRunner(QueryOutcome(rows=[], error="invalid input syntax for type integer"))
    client = TestClient(create_app(runner))
    spec = ENDPOINTS[0]

    response = send(client, spec, spec.benign_values, spec.locations[0])

    assert response.status_code == 500
    assert "invalid input syntax" in response.json()["error"]


def test_health_endpoint_does_not_touch_the_database(client, runner):
    assert client.get("/health").status_code == 200
    assert runner.calls == []


def test_benign_comment_listing_uses_bound_parameters(client, runner):
    client.get("/comments", params={"product_id": "1"})

    sql, params = runner.calls[-1]
    assert params == (1,) and "%s" in sql


def test_benign_comment_listing_rejects_non_numeric_product_id(client):
    assert client.get("/comments", params={"product_id": "1 OR 1=1"}).status_code == 400
