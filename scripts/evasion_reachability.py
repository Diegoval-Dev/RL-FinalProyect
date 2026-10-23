"""Is evasion reachable at all? Greedy search over operator sequences against ModSecurity PL1.

For each `train` payload, 25 steps: try every operator 4 times, keep the functional mutant with
the lowest PL1 anomaly score (ties go to the lowest arm index), stop descending when none improves.
Writes results/summary/evasion_reachability_pl1.csv. Run inside the lab: make evasion-reachability
"""

import csv
import subprocess
import time
from pathlib import Path

import numpy as np

from wafarena.envs.attacker_env import PARAM_BY_ENDPOINT, _load_bases
from wafarena.envs.backends import make_backend
from wafarena.mutations.payload import Payload
from wafarena.mutations.registry import REGISTRY

OUTPUT = Path("results/summary/evasion_reachability_pl1.csv")
STEPS, SAMPLES, SEED, PL = 25, 4, 0, 1
BLOCK_THRESHOLD = 5


def git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def climb(backend, base, rng) -> tuple[int, int, bool]:
    """Returns (start score, best score, whether any probed mutant evaded PL1 with effect)."""
    param = PARAM_BY_ENDPOINT[base.endpoint]
    current = Payload(base.text, base.location, 0)
    start = best = backend.probe(current, base.endpoint, param).modsec_scores[PL]
    evaded = False
    for _ in range(STEPS):
        candidates = []
        for arm, operator in enumerate(REGISTRY):
            for _ in range(SAMPLES):
                mutant = operator.apply(current, rng)
                if mutant is None or mutant == current:
                    continue
                if not backend.check_functional(mutant, base.endpoint, param).functional:
                    continue
                result = backend.probe(mutant, base.endpoint, param)
                evaded = evaded or (not result.modsec_block[PL] and result.oracle.effect)
                candidates.append((result.modsec_scores[PL], arm, mutant))
        if not candidates:
            break
        score, _arm, mutant = min(candidates, key=lambda c: (c[0], c[1]))
        if score <= best:
            best, current = score, mutant
    return start, best, evaded


def main() -> None:
    backend = make_backend("fast")
    rng = np.random.default_rng(SEED)
    started = time.monotonic()
    rows = []
    for base in _load_bases("train"):
        start, best, evaded = climb(backend, base, rng)
        rows.append([base.base_id, base.family, start, best, int(evaded)])
    backend.close()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["base_id", "family", "start_score", "best_score", "evaded", "git_sha"])
        sha = git_sha()
        writer.writerows([[*row, sha] for row in rows])
    starts, bests = np.array([r[2] for r in rows]), np.array([r[3] for r in rows])
    print(f"{len(rows)} payloads in {time.monotonic() - started:.0f} s")
    print(
        f"PL{PL} score: start mean {starts.mean():.1f} min {starts.min()}; "
        f"best mean {bests.mean():.1f} min {bests.min()} (block threshold {BLOCK_THRESHOLD})"
    )
    print(f"payloads that evaded: {sum(r[4] for r in rows)} / {len(rows)}")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
