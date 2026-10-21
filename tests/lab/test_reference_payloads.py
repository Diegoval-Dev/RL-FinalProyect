"""F1-T02: every reference payload works against vulnapp without WAF."""

import json

import pytest
from vulnapp_requests import response_signature, send

from vulnapp.queries import ENDPOINTS
from vulnapp.reference import REFERENCE_PAYLOADS

pytestmark = pytest.mark.lab

SPECS = {spec.name: spec for spec in ENDPOINTS}
COMMENTS_PRODUCT_ID = "1"


def cases():
    return [
        (ref, location) for ref in REFERENCE_PAYLOADS for location in SPECS[ref.endpoint].locations
    ]


def inject(ref, text):
    return {**SPECS[ref.endpoint].benign_values, ref.param: text}


def row_count(client, spec, value, param, location):
    values = {**spec.benign_values, param: value}
    return len(send(client, spec, values, location).json()["rows"])


@pytest.mark.parametrize(
    ("ref", "location"),
    cases(),
    ids=lambda v: f"{v.endpoint}-{v.family}" if hasattr(v, "family") else v,
)
def test_reference_payload_produces_expected_effect_without_waf(client, ref, location):
    spec = SPECS[ref.endpoint]
    response = send(client, spec, inject(ref, ref.text), location)

    if ref.expect.kind == "extra_rows":
        baseline = row_count(client, spec, ref.expect.value, ref.param, location)
        assert len(response.json()["rows"]) > baseline
    elif ref.expect.kind == "rows_contain":
        assert ref.expect.value in json.dumps(response.json()["rows"], ensure_ascii=False)
    elif ref.expect.kind == "error_text":
        assert response.status_code == 500
        assert ref.expect.value in response.json()["error"]
    elif ref.expect.kind == "blind_pair":
        false_response = send(client, spec, inject(ref, ref.expect.value), location)
        assert response.status_code == 200
        assert response_signature(response) != response_signature(false_response)
    elif ref.expect.kind == "side_effect_author":
        comments = client.get("/comments", params={"product_id": COMMENTS_PRODUCT_ID}).json()
        assert ref.expect.value in {row["author"] for row in comments["rows"]}
    else:
        pytest.fail(f"unknown expectation kind {ref.expect.kind}")
