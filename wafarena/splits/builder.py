"""Builds the frozen split file data/splits/v1.json (datos-y-splits.md).

Payloads: families in `holdout_families` go entirely to `test-family`; the rest are split 60/20/20
by base group so that variants of the same base never cross splits. Benign sessions: hard sessions
from reserved templates go to `test-hard`; the rest split 60/20/20 by session.
"""

import hashlib
import json
import re
from pathlib import Path

import numpy as np

CORPUS_PATH = Path("data/payloads/corpus.jsonl")
SESSIONS_PATH = Path("data/benign/sessions.jsonl")
SPLITS_PATH = Path("data/splits/v1.json")

HOLDOUT_FAMILIES = ("error", "stacked")
RESERVED_HARD_TEMPLATES = ("t-hard-code", "t-hard-emoji")
COMMENT_TAILS = ("-- -", "-- x", "--+", "--", "#")
TRAIN_FRACTION = 0.6
VAL_FRACTION = 0.2
SEED = 0


def strip_comment_tail(text: str) -> str:
    stripped = text.rstrip()
    for tail in COMMENT_TAILS:
        if stripped.endswith(tail):
            return stripped[: -len(tail)].rstrip()
    return stripped


def base_group(entry: dict) -> str:
    skeleton = re.sub(r"\s+", " ", strip_comment_tail(entry["text"]))
    raw = f"{entry['family']}|{entry['endpoint']}|{skeleton}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _split_groups(groups: list[str], rng: np.random.Generator) -> tuple[list, list, list]:
    shuffled = list(groups)
    rng.shuffle(shuffled)
    n = len(shuffled)
    train_end = int(n * TRAIN_FRACTION)
    val_end = train_end + int(n * VAL_FRACTION)
    return shuffled[:train_end], shuffled[train_end:val_end], shuffled[val_end:]


def split_payloads(corpus: list[dict], rng: np.random.Generator) -> dict:
    result = {"train": [], "val": [], "test": [], "test-family": []}
    groups_by_family: dict[str, dict[str, list[str]]] = {}
    for entry in corpus:
        if entry["family"] in HOLDOUT_FAMILIES:
            result["test-family"].append(entry["id"])
            continue
        groups_by_family.setdefault(entry["family"], {}).setdefault(base_group(entry), []).append(
            entry["id"]
        )
    for family in sorted(groups_by_family):
        groups = sorted(groups_by_family[family])
        train, val, test = _split_groups(groups, rng)
        for split_name, chosen in (("train", train), ("val", val), ("test", test)):
            for group in chosen:
                result[split_name].extend(groups_by_family[family][group])
    return {k: sorted(v) for k, v in result.items()}


def split_benign(sessions: list[dict], rng: np.random.Generator) -> dict:
    result = {"train": [], "val": [], "test": [], "test-hard": []}
    splittable = []
    for session in sessions:
        if session["kind"] == "hard" and session["template_id"] in RESERVED_HARD_TEMPLATES:
            result["test-hard"].append(session["session_id"])
        else:
            splittable.append(session["session_id"])
    rng.shuffle(splittable)
    n = len(splittable)
    train_end = int(n * TRAIN_FRACTION)
    val_end = train_end + int(n * VAL_FRACTION)
    result["train"] = splittable[:train_end]
    result["val"] = splittable[train_end:val_end]
    result["test"] = splittable[val_end:]
    return {k: sorted(v) for k, v in result.items()}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_splits(commit: str) -> dict:
    corpus = [json.loads(line) for line in CORPUS_PATH.read_text().splitlines() if line.strip()]
    sessions = [json.loads(line) for line in SESSIONS_PATH.read_text().splitlines() if line.strip()]
    return {
        "version": "v1",
        "created_commit": commit,
        "files_sha256": {
            "corpus.jsonl": file_sha256(CORPUS_PATH),
            "sessions.jsonl": file_sha256(SESSIONS_PATH),
        },
        "payloads": split_payloads(corpus, np.random.default_rng(SEED)),
        "benign": split_benign(sessions, np.random.default_rng(SEED + 1)),
        "holdout_families": list(HOLDOUT_FAMILIES),
    }


def write_splits(commit: str, path: Path = SPLITS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_splits(commit), indent=2, ensure_ascii=False) + "\n")
