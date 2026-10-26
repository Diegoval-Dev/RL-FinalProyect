"""DQN sanity check on CartPole-v1 (F3-T03, ADR-0006): does our DQN learn a textbook task?

Trains `DQNAgent` through the same `act`/`observe` protocol the runner uses, with the same model
selection protocol as the runner: every `EVAL_EVERY` steps the greedy policy plays
`SELECT_EPISODES` episodes on selection seeds and the best snapshot is kept (the analogue of `val`);
the kept snapshot is then confirmed on `CONFIRM_EPISODES` other episodes that never took part in
the selection (the analogue of `test`). A run passes when that confirmation's mean return is at
least `THRESHOLD` (195, the classic "solved" bar of CartPole) within `TOTAL_STEPS`.

Grading the last policy instead is not a check of the implementation: DQN on CartPole learns and
then oscillates (it was the first criterion tried, see Hallazgos de la Fase 3). Every variant of
the EXP-F ablation is checked; one row per (variant, seed) goes to
results/summary/dqn_cartpole_sanity.csv, with the final policy's return reported alongside.

Usage: uv run python scripts/dqn_cartpole_sanity.py [--variant base double ...] [--seeds 0 1]
"""

import argparse
import copy
import csv
import time
from pathlib import Path

import gymnasium as gym
import numpy as np

from wafarena.agents.base import Transition
from wafarena.agents.dqn import DQNAgent

THRESHOLD = 195.0
TOTAL_STEPS = 60_000
EVAL_EVERY = 5_000
SELECT_EPISODES = 10
CONFIRM_EPISODES = 20
SELECT_SEED, CONFIRM_SEED = 10_000, 20_000
OUT = Path("results/summary/dqn_cartpole_sanity.csv")
PARAMS = {
    "role": "attacker",  # no defender-only metrics on CartPole
    "hidden": [64, 64],
    "lr": 1e-3,
    "gamma": 0.99,
    "buffer_size": 20_000,
    "batch_size": 64,
    "learning_starts": 1_000,
    "train_freq": 1,
    "target_update": 500,
    "epsilon": {"start": 1.0, "end": 0.02, "decay_steps": 20_000},
}
VARIANTS = {
    "base": {},
    "double": {"double": True},
    "dueling": {"double": True, "dueling": True},
    "per": {"double": True, "dueling": True, "per": True},
}


def greedy_return(agent: DQNAgent, env, first_seed: int, episodes: int) -> float:
    returns = []
    for episode in range(episodes):
        obs, _ = env.reset(seed=first_seed + episode)
        done, total = False, 0.0
        while not done:
            obs, reward, terminated, truncated, _ = env.step(agent.act(obs, {}, explore=False))
            total += reward
            done = terminated or truncated
        returns.append(total)
    return float(np.mean(returns))


def train_and_evaluate(variant: str, seed: int) -> dict:
    import torch

    torch.set_num_threads(1)
    env, eval_env = gym.make("CartPole-v1"), gym.make("CartPole-v1")
    agent = DQNAgent(
        f"cartpole-{variant}",
        seed,
        obs_dim=4,
        n_actions=2,
        **PARAMS,
        **VARIANTS[variant],
    )
    started = time.monotonic()
    best_score, best_step, best_weights = -1.0, 0, None
    obs, _ = env.reset(seed=seed)
    for step in range(1, TOTAL_STEPS + 1):
        action = agent.act(obs, {}, explore=True)
        next_obs, reward, terminated, truncated, _ = env.step(action)
        agent.observe(Transition(obs, action, reward, next_obs, terminated, truncated, {}))
        obs = env.reset()[0] if terminated or truncated else next_obs
        if step % EVAL_EVERY == 0:
            score = greedy_return(agent, eval_env, SELECT_SEED, SELECT_EPISODES)
            if score > best_score:
                best_score, best_step = score, step
                best_weights = copy.deepcopy(agent.q_net.state_dict())
    final = greedy_return(agent, eval_env, CONFIRM_SEED, CONFIRM_EPISODES)
    agent.q_net.load_state_dict(best_weights)
    confirmed = greedy_return(agent, eval_env, CONFIRM_SEED, CONFIRM_EPISODES)
    return {
        "variant": variant,
        "seed": seed,
        "total_steps": TOTAL_STEPS,
        "best_step": best_step,
        "selection_return": round(best_score, 2),
        "confirmed_return": round(confirmed, 2),
        "final_policy_return": round(final, 2),
        "threshold": THRESHOLD,
        "passed": int(confirmed >= THRESHOLD),
        "duration_s": round(time.monotonic() - started, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(VARIANTS), nargs="+", default=sorted(VARIANTS))
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    args = parser.parse_args()
    rows = []
    for variant in args.variant:
        for seed in args.seeds:
            rows.append(train_and_evaluate(variant, seed))
            print(rows[-1], flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    failed = [r for r in rows if not r["passed"]]
    print(f"wrote {OUT}: {len(rows) - len(failed)}/{len(rows)} passed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
