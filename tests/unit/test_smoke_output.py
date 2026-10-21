"""F1-T14: the smoke summary has the expected shape and valid rates."""

import csv
from pathlib import Path

import pytest

SMOKE_PATH = Path(__file__).parents[2] / "results" / "summary" / "smoke.csv"
EXPECTED_HEADER = ["mode", "pl", "role", "episodes", "random_evasion_rate"]


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    with SMOKE_PATH.open() as handle:
        return list(csv.DictReader(handle))


def test_smoke_file_exists():
    assert SMOKE_PATH.exists()


def test_header_matches(rows):
    with SMOKE_PATH.open() as handle:
        assert next(csv.reader(handle)) == EXPECTED_HEADER


def test_both_modes_and_all_paranoia_levels_present(rows):
    attacker = [r for r in rows if r["role"] == "attacker"]
    assert {r["mode"] for r in attacker} == {"fast", "real"}
    assert {r["pl"] for r in attacker} == {"1", "2", "3", "4"}


def test_evasion_rates_are_in_unit_range(rows):
    rates = [float(r["random_evasion_rate"]) for r in rows if r["role"] == "attacker"]
    assert all(0.0 <= rate <= 1.0 for rate in rates)
