"""F1-T09: sessions.jsonl satisfies the datos-y-splits contract."""

import json
from pathlib import Path

import pytest

SESSIONS_PATH = Path(__file__).parents[2] / "data" / "benign" / "sessions.jsonl"
HARD_TAGS = {"apostrophe", "symbols", "code", "spanish", "emoji"}
MIN_SESSIONS = 5000
MIN_HARD = 1000


@pytest.fixture(scope="module")
def sessions() -> list[dict]:
    return [json.loads(line) for line in SESSIONS_PATH.read_text().splitlines() if line.strip()]


def test_has_at_least_five_thousand_sessions(sessions):
    assert len(sessions) >= MIN_SESSIONS


def test_has_at_least_one_thousand_hard_sessions(sessions):
    assert sum(s["kind"] == "hard" for s in sessions) >= MIN_HARD


def test_all_hard_tags_are_represented(sessions):
    seen = {tag for s in sessions for r in s["requests"] for tag in r["hard_tags"]}
    assert HARD_TAGS <= seen


def test_session_ids_are_unique(sessions):
    ids = [s["session_id"] for s in sessions]
    assert len(ids) == len(set(ids))


def test_every_session_has_requests(sessions):
    assert all(len(s["requests"]) > 0 for s in sessions)


def test_kinds_are_normal_or_hard(sessions):
    assert {s["kind"] for s in sessions} <= {"normal", "hard"}
