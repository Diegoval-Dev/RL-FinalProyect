"""Score the fixed ATK-REF-1 checkpoint on EXP-H1 validation defenders.

This selected EXP-G3 seed-1 checkpoint is one fixed reference, not five independent PPO seeds.
Its historical training queries are unavailable on the EXP-H1 query axis.
Run inside the lab runner with all ModSec services started.
"""

import csv
from pathlib import Path

import yaml

from wafarena.agents import load_checkpoint
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness

CHECKPOINT = Path("checkpoints/refs/ATK-REF-1")
OUTPUT = Path("results/summary/EXP-H1_ATK-REF-1.csv")
SUITE = "attacker-val-v1"
DEFENDERS = {
    "pl1": {"type": "modsec", "paranoia_level": 1},
    "defref1": {"type": "checkpoint", "path": "DEF-REF-1"},
}


def main() -> None:
    checkpoint_meta = yaml.safe_load((CHECKPOINT / "meta.yaml").read_text())
    backend = resolve_backend("fast")
    rows = []
    try:
        for name, defender in DEFENDERS.items():
            agent = load_checkpoint(CHECKPOINT)
            episodes = harness.run_attacker_suite(agent, SUITE, defender=defender, backend=backend)
            summary = harness.summarize_attacker(
                episodes, query_budget=harness.VALIDATION_SUITES[SUITE].query_budget
            )
            rows.append(
                {
                    "defender": name,
                    "suite": SUITE,
                    "checkpoint": checkpoint_meta["agent_id"],
                    "source_run_id": checkpoint_meta["train"]["run_id"],
                    "source_git_sha": checkpoint_meta["train"]["git_sha"],
                    "source_seed": checkpoint_meta["train"]["seed"],
                    "episodes": summary["episodes"],
                    "evasion_rate": summary["evasion_rate"],
                }
            )
            print(rows[-1], flush=True)
    finally:
        backend.close()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
