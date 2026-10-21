"""Smoke test: random agents against both environments in fast and real mode.

Runs 100 episodes per paranoia level for a random attacker (recording the random evasion rate) and
100 episodes for a random defender (sanity: it must run without error). Writes the random evasion
rates to results/summary/smoke.csv as a sanity baseline for the handoff.
"""

import csv
from pathlib import Path

import numpy as np

import wafarena.envs  # noqa: F401
from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs.attacker_env import N_ACTIONS, AttackerEnv
from wafarena.envs.backends import make_backend
from wafarena.envs.defender_env import DefenderEnv
from wafarena.features.modsec import PARANOIA_LEVELS

OUTPUT = Path("results/summary/smoke.csv")
EPISODES = {"fast": 100, "real": 15}
MAX_STEPS = {"fast": 60, "real": 25}
SEED = 0


def random_attacker_evasion(mode: str, pl: int, rng: np.random.Generator) -> float:
    backend = make_backend(mode)
    env = AttackerEnv(
        backend=backend, defender=ModSecDefender(pl), split="train", max_steps=MAX_STEPS[mode]
    )
    evasions = 0
    for episode in range(EPISODES[mode]):
        env.reset(seed=SEED + episode)
        done = False
        while not done:
            _obs, _r, terminated, truncated, info = env.step(int(rng.integers(N_ACTIONS)))
            done = terminated or truncated
        evasions += int(info["evaded"])
    backend.close()
    return evasions / EPISODES[mode]


def random_defender_runs(mode: str, rng: np.random.Generator) -> int:
    backend = make_backend(mode)
    env = DefenderEnv(backend=backend, split="train", attack_ratio=0.3)
    completed = 0
    for episode in range(EPISODES[mode]):
        env.reset(seed=SEED + episode)
        done = False
        while not done:
            _obs, _r, terminated, truncated, _info = env.step(int(rng.integers(5)))
            done = terminated or truncated
        completed += 1
    backend.close()
    return completed


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    rows = []
    for mode in ("fast", "real"):
        for pl in PARANOIA_LEVELS:
            rate = random_attacker_evasion(mode, pl, rng)
            rows.append([mode, pl, "attacker", EPISODES[mode], f"{rate:.4f}"])
        completed = random_defender_runs(mode, rng)
        rows.append([mode, "-", "defender", completed, "-"])
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["mode", "pl", "role", "episodes", "random_evasion_rate"])
        writer.writerows(rows)
    print(f"wrote {OUTPUT}")
    for row in rows:
        print("  " + ",".join(str(c) for c in row))


if __name__ == "__main__":
    main()
