"""F1-T13: frozen splits satisfy the datos-y-splits contract (no leakage)."""

import json
from pathlib import Path

import pytest

SPLITS_PATH = Path(__file__).parents[2] / "data" / "splits" / "v1.json"
HOLDOUT_FAMILIES = {"error", "stacked"}


@pytest.fixture(scope="module")
def splits() -> dict:
    return json.loads(SPLITS_PATH.read_text())


def test_version_and_holdout_families(splits):
    assert splits["version"] == "v1"
    assert set(splits["holdout_families"]) == HOLDOUT_FAMILIES


def test_payload_splits_do_not_overlap(splits):
    seen = set()
    for ids in splits["payloads"].values():
        assert not (set(ids) & seen)
        seen |= set(ids)


def test_benign_splits_do_not_overlap(splits):
    seen = set()
    for ids in splits["benign"].values():
        assert not (set(ids) & seen)
        seen |= set(ids)


def test_every_split_is_non_empty(splits):
    assert all(ids for ids in splits["payloads"].values())
    assert all(ids for ids in splits["benign"].values())


def test_files_sha256_recorded(splits):
    assert set(splits["files_sha256"]) == {"corpus.jsonl", "sessions.jsonl"}


def test_payload_base_groups_do_not_cross_splits():
    import json as _json
    from pathlib import Path as _Path

    from wafarena.splits.builder import base_group

    corpus_path = _Path(__file__).parents[2] / "data" / "payloads" / "corpus.jsonl"
    corpus = {
        e["id"]: e for e in (_json.loads(line) for line in corpus_path.read_text().splitlines())
    }
    splits = _json.loads(SPLITS_PATH.read_text())["payloads"]

    group_split: dict[str, str] = {}
    for split_name, ids in splits.items():
        if split_name == "test-family":
            continue
        for payload_id in ids:
            group = base_group(corpus[payload_id])
            assert group_split.setdefault(group, split_name) == split_name
