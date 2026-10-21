"""Builds data/payloads/corpus.jsonl: SQLi payloads the oracle confirms as functional.

Deterministic given the input templates; the same run regenerates the same file. Runs inside the
lab runner because it calls the oracle against vulnapp.
"""

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from vulnapp.queries import FAMILIES, Family
from wafarena.corpus.templates import ENDPOINT_CONTEXTS, candidates, endpoint_spec
from wafarena.mutations.payload import Payload
from wafarena.oracle import Oracle

CORPUS_PATH = Path("data/payloads/corpus.jsonl")
SOURCE = "WAFArena/curated"
SOURCE_REF = "wafarena/corpus/templates.py"


@dataclass(frozen=True)
class CorpusEntry:
    id: str
    family: Family
    endpoint: str
    text: str
    location: str
    source: str
    source_ref: str
    adapted_for_postgres: bool
    verified_commit: str


def payload_id(family: str, endpoint: str, text: str) -> str:
    digest = hashlib.sha1(f"{family}|{endpoint}|{text}".encode()).hexdigest()[:10]
    return f"p-{digest}"


def functional_payloads(oracle: Oracle, commit: str) -> Iterator[CorpusEntry]:
    seen: set[str] = set()
    for ec in ENDPOINT_CONTEXTS:
        spec = endpoint_spec(ec.endpoint)
        location = spec.locations[0]
        for family in FAMILIES:
            for text in candidates(ec, family):
                key = f"{family}|{ec.endpoint}|{text}"
                if key in seen:
                    continue
                seen.add(key)
                result = oracle.check_direct(Payload(text, location, 0), ec.endpoint, ec.param)
                if result.functional:
                    yield CorpusEntry(
                        id=payload_id(family, ec.endpoint, text),
                        family=family,
                        endpoint=ec.endpoint,
                        text=text,
                        location=location,
                        source=SOURCE,
                        source_ref=SOURCE_REF,
                        adapted_for_postgres=True,
                        verified_commit=commit,
                    )


def write_corpus(entries: list[CorpusEntry], path: Path = CORPUS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for entry in sorted(entries, key=lambda e: (e.family, e.endpoint, e.id)):
            handle.write(json.dumps(entry.__dict__, ensure_ascii=False) + "\n")
