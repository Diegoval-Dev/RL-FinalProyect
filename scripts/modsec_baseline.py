"""Generates results/summary/modsec_baseline_corpus.csv: block rate per PL.

Runs inside the lab runner. Sends each request through the ModSecurity PL instances exactly as a
client would hit vulnapp (payload in its real parameter and location), and records the CRS block
rate for the attack set (reference payloads) and the benign set (endpoint benign inputs).

Until F1-T07 provides data/payloads/corpus.jsonl this uses the reference payloads; it regenerates
the same CSV from the corpus when it exists.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from vulnapp.queries import ENDPOINTS, get_endpoint
from vulnapp.reference import REFERENCE_PAYLOADS
from wafarena.defenders.audit import PARANOIA_LEVELS
from wafarena.defenders.modsec import modsec_score

OUTPUT = Path("results/summary/modsec_baseline_corpus.csv")


@dataclass(frozen=True)
class Probe:
    method: str
    path: str
    data: dict | None


def query_probe(path: str, values: dict) -> Probe:
    return Probe("GET", f"{path}?{urlencode(values)}", None)


def attack_probes() -> list[Probe]:
    probes = []
    for ref in REFERENCE_PAYLOADS:
        spec = get_endpoint(ref.endpoint)
        values = {**spec.benign_values, ref.param: ref.text}
        location = spec.locations[0]
        probes.append(
            query_probe(spec.path, values)
            if location == "query"
            else Probe("POST", spec.path, values)
        )
    return probes


def benign_probes() -> list[Probe]:
    probes = []
    for spec in ENDPOINTS:
        location = spec.locations[0]
        probes.append(
            query_probe(spec.path, dict(spec.benign_values))
            if location == "query"
            else Probe("POST", spec.path, dict(spec.benign_values))
        )
    return probes


def block_rate(probes: list[Probe], pl: int) -> float:
    blocked = 0
    for probe in probes:
        kwargs = {"data": probe.data} if probe.data is not None else {}
        blocked += modsec_score(probe.method, probe.path, pl, **kwargs).would_block
    return blocked / len(probes)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    attacks = attack_probes()
    benign = benign_probes()
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["pl", "set", "n", "block_rate"])
        for pl in PARANOIA_LEVELS:
            writer.writerow([pl, "attack", len(attacks), f"{block_rate(attacks, pl):.4f}"])
            writer.writerow([pl, "benign", len(benign), f"{block_rate(benign, pl):.4f}"])
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
