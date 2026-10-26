"""Checks the Phase 3 references as opponents (F3-T11 acceptance): both load with
`load_checkpoint` and play `--episodes` episodes, DEF-REF-1 through DefenderDriver as the defender
of Attacker-v0 and ATK-REF-1 through AttackerDriver as the attacker of Defender-v0 (every session
an attack session). Writes results/summary/refs_check.csv with one row per reference.

Runs inside the lab runner (make check-refs).
"""

import argparse
import csv
import time
from pathlib import Path

import numpy as np

from wafarena.agents import load_checkpoint
from wafarena.attackers.driver import AttackerDriver
from wafarena.defenders.driver import DefenderDriver
from wafarena.envs.attacker_env import N_ACTIONS as ATTACKER_ACTIONS
from wafarena.envs.attacker_env import AttackerEnv
from wafarena.envs.defender_env import DefenderEnv
from wafarena.envs.resolve import resolve_backend

REFS = Path("checkpoints/refs")
OUTPUT = Path("results/summary/refs_check.csv")
SEED = 0


def check_defender(backend, episodes: int) -> dict:
    agent = load_checkpoint(REFS / "DEF-REF-1")
    env = AttackerEnv(backend, defender=DefenderDriver(agent), split="test")
    rng = np.random.default_rng(SEED)
    sends = blocked = evaded = 0
    started = time.monotonic()
    for episode in range(episodes):
        env.reset(seed=SEED + episode)
        done = False
        while not done:
            action = int(rng.integers(ATTACKER_ACTIONS))
            *_, terminated, truncated, info = env.step(action)
            if "gt_defender_action" in info and action == ATTACKER_ACTIONS - 1:
                sends += 1
                blocked += int(info["gt_defender_action"] != 0)
            evaded += int(info["evaded"])
            done = terminated or truncated
    return {
        "ref": "DEF-REF-1",
        "loaded_as": type(agent).__name__,
        "role": agent.role,
        "driver": "DefenderDriver in Attacker-v0 (random attacker, split test)",
        "episodes": episodes,
        "requests_judged": sends,
        "blocked_fraction": round(blocked / sends, 6) if sends else "",
        "evasions": evaded,
        "seconds": round(time.monotonic() - started, 1),
    }


def check_attacker(backend, episodes: int) -> dict:
    agent = load_checkpoint(REFS / "ATK-REF-1")
    env = DefenderEnv(backend, attacker=AttackerDriver(agent), split="test", attack_ratio=1.0)
    rng = np.random.default_rng(SEED)
    requests = attacks = 0
    started = time.monotonic()
    for episode in range(episodes):
        env.reset(seed=SEED + episode)
        done = False
        while not done:
            *_, terminated, truncated, info = env.step(int(rng.integers(5)))
            requests += 1
            attacks += int(info["gt_label"] == "attack")
            done = terminated or truncated
    return {
        "ref": "ATK-REF-1",
        "loaded_as": type(agent).__name__,
        "role": agent.role,
        "driver": "AttackerDriver in Defender-v0 (random defender, split test)",
        "episodes": episodes,
        "requests_judged": requests,
        "blocked_fraction": "",
        "evasions": "",
        "seconds": round(time.monotonic() - started, 1),
        "attack_requests": attacks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=100)
    args = parser.parse_args()
    backend = resolve_backend("fast")
    try:
        rows = [check_defender(backend, args.episodes), check_attacker(backend, args.episodes)]
    finally:
        backend.close()
    columns = list(dict.fromkeys(k for r in rows for k in r))
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, restval="")
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(r)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
