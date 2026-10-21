"""Recomputes the data file hashes and fails if they differ from data/splits/v1.json."""

import json
import sys

from wafarena.splits.builder import CORPUS_PATH, SESSIONS_PATH, SPLITS_PATH, file_sha256


def main() -> int:
    splits = json.loads(SPLITS_PATH.read_text())
    expected = splits["files_sha256"]
    actual = {
        "corpus.jsonl": file_sha256(CORPUS_PATH),
        "sessions.jsonl": file_sha256(SESSIONS_PATH),
    }
    if expected != actual:
        print(f"split verification failed:\n expected {expected}\n actual   {actual}")
        return 1
    print("splits verified: data files unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
