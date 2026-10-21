"""F1-T02: registry of vulnerable endpoints, templates and reference payloads."""

import string
from pathlib import Path

import pytest

from vulnapp.docs import render_endpoints_md
from vulnapp.queries import ENDPOINTS, FAMILIES, LOCATIONS, build_sql
from vulnapp.reference import REFERENCE_PAYLOADS

ENDPOINTS_MD = Path(__file__).parents[2] / "lab" / "vulnapp" / "ENDPOINTS.md"
VULNERABLE_ENDPOINT_COUNT = 8


def template_fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_registry_declares_eight_vulnerable_endpoints():
    assert len(ENDPOINTS) == VULNERABLE_ENDPOINT_COUNT


def test_registry_has_unique_names_and_paths_per_method():
    assert len({spec.name for spec in ENDPOINTS}) == len(ENDPOINTS)


@pytest.mark.parametrize("spec", ENDPOINTS, ids=lambda spec: spec.name)
def test_template_fields_match_declared_params(spec):
    assert template_fields(spec.template) == set(spec.params)


@pytest.mark.parametrize("spec", ENDPOINTS, ids=lambda spec: spec.name)
def test_benign_values_cover_every_param(spec):
    assert set(spec.benign_values) == set(spec.params)


@pytest.mark.parametrize("spec", ENDPOINTS, ids=lambda spec: spec.name)
def test_build_sql_with_benign_values_leaves_no_placeholder(spec):
    sql = build_sql(spec, spec.benign_values)
    assert "{" not in sql and "}" not in sql


@pytest.mark.parametrize("spec", ENDPOINTS, ids=lambda spec: spec.name)
def test_build_sql_concatenates_value_without_escaping(spec):
    param = spec.params[0]
    values = {**spec.benign_values, param: "O'Brien"}
    assert "O'Brien" in build_sql(spec, values)


@pytest.mark.parametrize("spec", ENDPOINTS, ids=lambda spec: spec.name)
def test_spec_uses_known_locations_and_families(spec):
    assert set(spec.locations) <= set(LOCATIONS)
    assert set(spec.families) <= set(FAMILIES)


@pytest.mark.parametrize("spec", ENDPOINTS, ids=lambda spec: spec.name)
def test_every_declared_family_has_a_reference_payload(spec):
    covered = {ref.family for ref in REFERENCE_PAYLOADS if ref.endpoint == spec.name}
    assert covered == set(spec.families)


def test_reference_payloads_target_declared_params():
    by_name = {spec.name: spec for spec in ENDPOINTS}
    assert all(ref.param in by_name[ref.endpoint].params for ref in REFERENCE_PAYLOADS)


def test_every_family_is_covered_by_at_least_one_endpoint():
    assert {ref.family for ref in REFERENCE_PAYLOADS} == set(FAMILIES)


def test_blind_reference_payloads_carry_a_false_counterpart():
    blind = [ref for ref in REFERENCE_PAYLOADS if ref.family == "boolean_blind"]
    assert blind and all(ref.expect.kind == "blind_pair" and ref.expect.value for ref in blind)


def test_endpoints_markdown_matches_generated_document():
    assert ENDPOINTS_MD.read_text() == render_endpoints_md()
