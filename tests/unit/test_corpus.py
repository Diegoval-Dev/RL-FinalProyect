"""F1-T07: corpus.jsonl satisfies the datos-y-splits contract."""

import collections
import json
from pathlib import Path

import pytest

CORPUS_PATH = Path(__file__).parents[2] / "data" / "payloads" / "corpus.jsonl"
VALID_FAMILIES = {"tautology", "union", "error", "boolean_blind", "stacked"}
REQUIRED_FIELDS = {
    "id",
    "family",
    "endpoint",
    "text",
    "location",
    "source",
    "source_ref",
    "adapted_for_postgres",
    "verified_commit",
}
MIN_TOTAL = 200
MIN_PER_FAMILY = 30


@pytest.fixture(scope="module")
def entries() -> list[dict]:
    return [json.loads(line) for line in CORPUS_PATH.read_text().splitlines() if line.strip()]


def test_corpus_file_exists():
    assert CORPUS_PATH.exists()


def test_every_entry_has_the_required_fields(entries):
    assert all(REQUIRED_FIELDS <= set(entry) for entry in entries)


def test_every_family_is_valid(entries):
    assert {entry["family"] for entry in entries} <= VALID_FAMILIES


def test_corpus_has_at_least_two_hundred_functional_payloads(entries):
    assert len(entries) >= MIN_TOTAL


def test_each_family_has_at_least_thirty_payloads(entries):
    counts = collections.Counter(entry["family"] for entry in entries)
    assert all(counts[family] >= MIN_PER_FAMILY for family in VALID_FAMILIES), counts


def test_ids_are_unique(entries):
    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids))


def test_all_payloads_marked_adapted_for_postgres(entries):
    assert all(entry["adapted_for_postgres"] is True for entry in entries)
