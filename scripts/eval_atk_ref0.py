"""ATK-REF-0 on attacker-eval-v1 against modsec-pl1 and DEF-REF-1: the reference point of the
policy-gradient attackers (EXP-G1..G3, F3-T08 acceptance: «comparación con ATK-REF-0»).

ATK-REF-0 is a fixed checkpoint and the suite is fixed (same seeds, same base payloads), so one
evaluation per defender is the whole result. Writes results/summary/ATK-REF-0_eval.csv.
Runs inside the lab runner.
"""

import csv
from pathlib import Path

from wafarena.agents import load_checkpoint
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness

OUTPUT = Path("results/summary/ATK-REF-0_eval.csv")
SUITE = "attacker-eval-v1"
DEFENDERS = {
    "modsec-pl1": {"type": "modsec", "paranoia_level": 1},
    "DEF-REF-1": {"type": "checkpoint", "path": "DEF-REF-1"},
}


def main() -> None:
    agent = load_checkpoint(Path("checkpoints/refs/ATK-REF-0"))
    backend = resolve_backend("fast")
    rows = []
    try:
        for name, defender in DEFENDERS.items():
            results = harness.run_attacker_suite(agent, SUITE, defender=defender, backend=backend)
            budget = harness.ATTACKER_SUITES[SUITE].query_budget
            summary = harness.summarize_attacker(results, query_budget=budget)
            rows.append({"attacker": "ATK-REF-0", "defender": name, "suite": SUITE, **summary})
            print(rows[-1])
    finally:
        backend.close()
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
