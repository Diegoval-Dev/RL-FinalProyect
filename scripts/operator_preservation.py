"""Generates results/summary/operator_preservation.csv (runs in the lab runner).

For each operator and family: applicability rate (how often the operator applies to a payload) and
preservation rate (of the applied mutations, how many keep the payload functional per the oracle).
"""

import collections
import csv
import json
from pathlib import Path

import numpy as np

from wafarena.corpus.templates import ENDPOINT_CONTEXTS
from wafarena.mutations.payload import Payload
from wafarena.mutations.registry import REGISTRY, operator_names
from wafarena.oracle import Oracle

CORPUS_PATH = Path("data/payloads/corpus.jsonl")
OUTPUT = Path("results/summary/operator_preservation.csv")
PARAM_BY_ENDPOINT = {ec.endpoint: ec.param for ec in ENDPOINT_CONTEXTS}
SEED = 0


def load_corpus() -> list[dict]:
    return [json.loads(line) for line in CORPUS_PATH.read_text().splitlines() if line.strip()]


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    oracle = Oracle()
    corpus = load_corpus()
    rng = np.random.default_rng(SEED)

    applied = collections.Counter()
    preserved = collections.Counter()
    total = collections.Counter()

    for operator in REGISTRY:
        for entry in corpus:
            family = entry["family"]
            total[(operator.name, family)] += 1
            payload = Payload(entry["text"], entry["location"], 0)
            mutated = operator.apply(payload, rng)
            if mutated is None:
                continue
            applied[(operator.name, family)] += 1
            result = oracle.check_direct(
                mutated, entry["endpoint"], PARAM_BY_ENDPOINT[entry["endpoint"]]
            )
            if result.functional:
                preserved[(operator.name, family)] += 1

    with OUTPUT.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["operator", "family", "n", "applicability", "preservation"])
        for name in operator_names():
            for family in sorted({e["family"] for e in corpus}):
                n = total[(name, family)]
                a = applied[(name, family)]
                applicability = a / n if n else 0.0
                preservation = preserved[(name, family)] / a if a else 0.0
                writer.writerow([name, family, n, f"{applicability:.4f}", f"{preservation:.4f}"])
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
