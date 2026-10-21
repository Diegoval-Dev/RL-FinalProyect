"""Entry point to regenerate data/payloads/corpus.jsonl (runs in the lab runner)."""

import collections
import os

from wafarena.corpus.builder import functional_payloads, write_corpus
from wafarena.oracle import Oracle


def current_commit() -> str:
    return os.environ.get("VERIFIED_COMMIT", "unknown")


def main() -> None:
    entries = list(functional_payloads(Oracle(), current_commit()))
    write_corpus(entries)
    by_family = collections.Counter(entry.family for entry in entries)
    print(f"wrote {len(entries)} functional payloads")
    for family, count in sorted(by_family.items()):
        print(f"  {family}: {count}")


if __name__ == "__main__":
    main()
