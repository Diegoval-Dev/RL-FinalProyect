"""Training loop for `Attacker-v0` and `Defender-v0` agents: episode statistics, train.csv and
TensorBoard. The loop is the same for both roles; only the per-episode statistics differ."""

import csv
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

import numpy as np

from wafarena.agents.base import Agent, Transition, strip_ground_truth
from wafarena.envs.attacker_env import SEND_ACTION, AttackerEnv
from wafarena.envs.defender_env import DefenderEnv

BASE_COLUMNS = [
    "step",
    "episode",
    "return",
    "length",
    "evaded",
    "banned",
    "queries_used",
    "mutation_attempts",
    "broken",
    "complete",
]


class _Episode:
    """Accumulates one `Attacker-v0` episode's statistics; attacker-specific counters live here."""

    columns = BASE_COLUMNS

    def __init__(self) -> None:
        self.reward = 0.0
        self.length = 0
        self.mutation_attempts = 0
        self.broken = 0
        self.metrics: dict[str, list[float]] = defaultdict(list)

    def add(self, action: int, reward: float, info: dict, metrics: dict[str, float]) -> None:
        self.reward += reward
        self.length += 1
        if action != SEND_ACTION:
            self.mutation_attempts += 1
            self.broken += int(info["broken"])
        for name, value in metrics.items():
            self.metrics[name].append(float(value))

    def row(self, step: int, index: int, info: dict, complete: bool) -> dict:
        row = {
            "step": step,
            "episode": index,
            "return": round(self.reward, 6),
            "length": self.length,
            "evaded": int(info["evaded"]),
            "banned": int(info["banned"]),
            "queries_used": info["queries_used"],
            "mutation_attempts": self.mutation_attempts,
            "broken": self.broken,
            "complete": int(complete),
        }
        for name, values in self.metrics.items():
            row[f"m_{name}"] = round(float(np.mean(values)), 6)
        return row


DEFENDER_COLUMNS = [
    "step",
    "episode",
    "return",
    "length",
    "attack",
    "blocked",
    "allowed_effect",
    "complete",
]


class DefenderEpisode:
    """One `Defender-v0` episode (a session). `attack` and `allowed_effect` come from the `gt_*`
    keys, read here for logging only: the agent never sees them (`strip_ground_truth`)."""

    columns = DEFENDER_COLUMNS

    def __init__(self) -> None:
        self.reward = 0.0
        self.length = 0
        self.blocked = 0
        self.allowed_effect = 0
        self.attack = False
        self.metrics: dict[str, list[float]] = defaultdict(list)

    def add(self, action: int, reward: float, info: dict, metrics: dict[str, float]) -> None:
        self.reward += reward
        self.length += 1
        self.attack = info["gt_label"] == "attack"
        self.blocked += int(action != 0)
        self.allowed_effect += int(action == 0 and bool(info["gt_effect"]))
        for name, value in metrics.items():
            self.metrics[name].append(float(value))

    def row(self, step: int, index: int, info: dict, complete: bool) -> dict:
        row = {
            "step": step,
            "episode": index,
            "return": round(self.reward, 6),
            "length": self.length,
            "attack": int(self.attack),
            "blocked": self.blocked,
            "allowed_effect": self.allowed_effect,
            "complete": int(complete),
        }
        for name, values in self.metrics.items():
            row[f"m_{name}"] = round(float(np.mean(values)), 6)
        return row


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    extra = sorted({key for row in rows for key in row} - set(columns))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns + extra, restval="")
        writer.writeheader()
        writer.writerows(rows)


def train(
    agent: Agent,
    env: AttackerEnv | DefenderEnv,
    *,
    total_steps: int,
    seed: int,
    out_dir: Path,
    eval_every: int,
    on_eval: Callable[[int], None] | None = None,
    tensorboard: bool = True,
    episode_stats: type = _Episode,
) -> None:
    """Interact for exactly `total_steps` env steps, calling `on_eval(step)` periodically.

    The env is seeded once, so the whole run is determined by `seed`. The agent only sees `info`
    without `gt_*` keys. Writes `train.csv` (one row per episode, columns from `episode_stats`:
    the attacker's by default, `DefenderEpisode` for `Defender-v0`) and, optionally, `tb/`.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    writer = _tensorboard_writer(out_dir / "tb") if tensorboard else None
    rows: list[dict] = []
    obs, info = env.reset(seed=seed)
    episode = episode_stats()
    try:
        for step in range(1, total_steps + 1):
            action = int(agent.act(obs, strip_ground_truth(info), explore=True))
            next_obs, reward, terminated, truncated, next_info = env.step(action)
            metrics = agent.observe(
                Transition(
                    obs,
                    action,
                    reward,
                    next_obs,
                    terminated,
                    truncated,
                    strip_ground_truth(next_info),
                )
            )
            episode.add(action, reward, next_info, metrics)
            done = terminated or truncated
            if done or step == total_steps:
                rows.append(episode.row(step, len(rows), next_info, complete=done))
                if writer:
                    _log_episode(writer, rows[-1])
            if on_eval and (step % eval_every == 0 or step == total_steps):
                on_eval(step)
            if done:
                obs, info = env.reset()
                episode = episode_stats()
            else:
                obs, info = next_obs, next_info
    finally:
        _write_csv(out_dir / "train.csv", rows, episode_stats.columns)
        if writer:
            writer.close()


def _tensorboard_writer(path: Path):
    from tensorboardX import SummaryWriter

    return SummaryWriter(str(path))


def _log_episode(writer, row: dict) -> None:
    for name, value in row.items():
        if name not in ("step", "episode", "complete"):
            writer.add_scalar(f"train/{name}", float(value), row["step"])
