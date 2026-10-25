"""Diagnostic (exploratory, F3-T08): what DEF-REF-1 does with the n-th query of one session.

Every evasion of the policy-gradient attackers against DEF-REF-1 lands on the 10th query
(QFE = 10). This replays, inside Attacker-v0, sessions that only SEND the unmutated base payload
(no mutation, ban threshold lifted so sessions run on), and counts the defender's action at each
query index: if the policy changes with the session's length, it shows here. Writes
results/summary/DEF-REF-1_session_diag.csv. Runs inside the lab runner.
"""

import csv
from collections import Counter
from pathlib import Path

from wafarena.defenders.base import Action
from wafarena.envs.attacker_env import SEND_ACTION, AttackerEnv
from wafarena.envs.resolve import resolve_backend

OUTPUT = Path("results/summary/DEF-REF-1_session_diag.csv")
EPISODES, QUERIES, FIRST_SEED = 40, 20, 3000


def main() -> None:
    backend = resolve_backend("fast")
    counts: dict[int, Counter] = {}
    try:
        env = AttackerEnv(
            backend,
            defender={"type": "checkpoint", "path": "DEF-REF-1"},
            split="val",
            ban_threshold=10_000,
        )
        for episode in range(EPISODES):
            env.reset(seed=FIRST_SEED + episode)
            for query in range(1, QUERIES + 1):
                *_, terminated, truncated, info = env.step(SEND_ACTION)
                counts.setdefault(query, Counter())[Action(info["gt_defender_action"]).name] += 1
                if terminated or truncated:
                    break
    finally:
        backend.close()
    names = [a.name for a in Action]
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["query", "sessions", *names])
        writer.writeheader()
        for query, counter in sorted(counts.items()):
            writer.writerow({"query": query, "sessions": sum(counter.values()), **counter})
    print(OUTPUT.read_text())


if __name__ == "__main__":
    main()
