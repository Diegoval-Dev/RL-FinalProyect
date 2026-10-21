"""F1-T04: the five oracle guarantees, checked against the running laboratory."""

import pytest
from vulnapp_requests import send

from vulnapp.queries import ENDPOINTS, get_endpoint
from vulnapp.reference import REFERENCE_PAYLOADS
from wafarena.mutations.payload import Payload
from wafarena.oracle import Oracle

pytestmark = pytest.mark.lab

CATALOG_TAUTOLOGY = "' OR '1'='1' --"
WITHOUT_CLOSING_QUOTE = "admin --"
DETERMINISM_RUNS = 100
BENIGN_PARAM_CASES = [(spec, param) for spec in ENDPOINTS for param in spec.params]


@pytest.fixture(scope="session")
def oracle():
    return Oracle()


@pytest.mark.parametrize(
    "ref",
    REFERENCE_PAYLOADS,
    ids=lambda ref: f"{ref.endpoint}-{ref.family}-{ref.param}",
)
def test_reference_payloads_have_effect_on_direct_check(oracle, ref):
    spec = get_endpoint(ref.endpoint)

    result = oracle.check_direct(Payload(ref.text, spec.locations[0], 0), ref.endpoint, ref.param)

    assert result.effect is True


@pytest.mark.parametrize(("spec", "param"), BENIGN_PARAM_CASES, ids=lambda v: getattr(v, "name", v))
def test_benign_values_have_no_effect_on_direct_check(oracle, spec, param):
    payload = Payload(spec.benign_values[param], spec.locations[0], 0)

    result = oracle.check_direct(payload, spec.name, param)

    assert result.effect is False


def test_payload_without_closing_quote_is_not_functional(oracle):
    payload = Payload(WITHOUT_CLOSING_QUOTE, "form", 0)

    result = oracle.check_direct(payload, "login", "username")

    assert result.functional is False


def test_same_payload_gives_same_result_on_every_check(oracle):
    payload = Payload(CATALOG_TAUTOLOGY, "query", 0)

    results = {oracle.check_direct(payload, "catalog", "category") for _ in range(DETERMINISM_RUNS)}

    assert len(results) == 1


@pytest.mark.parametrize("spec", ENDPOINTS, ids=lambda spec: spec.name)
def test_no_legitimate_request_returns_the_canary_token(client, canary_token, spec):
    for location in spec.locations:
        response = send(client, spec, spec.benign_values, location)
        assert canary_token not in response.text
