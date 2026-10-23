"""Offline estimate of each bandit arm's mean reward, for the regret R(t) (metricas.md)."""

import csv
from pathlib import Path

import numpy as np

from wafarena.envs.backends.base import Backend
from wafarena.envs.bandit_env import N_ARMS, BanditEnv

DEFAULT_PULLS_PER_ARM = 2000


def estimate_arm_means(
    backend: Backend,
    defender,
    *,
    pulls_per_arm: int = DEFAULT_PULLS_PER_ARM,
    seed: int = 0,
    split: str = "train",
    query_budget: int = 50,
) -> np.ndarray:
    """μ_a = P(evasion) of pulling arm `a` once from a fresh base payload of `split`.

    Every arm gets `pulls_per_arm` independent pulls with a fixed seed. The live bandit keeps
    mutating the same payload across pulls, so these means are an approximation of the true
    (state-dependent) arm values; the report declares it.
    """
    if pulls_per_arm < 1:
        raise ValueError("pulls_per_arm must be positive")
    env = BanditEnv(backend=backend, defender=defender, split=split, query_budget=query_budget)
    means = np.zeros(N_ARMS)
    for arm in range(N_ARMS):
        env.reset(seed=seed + arm)
        wins = 0
        for _ in range(pulls_per_arm):
            _obs, reward, _terminated, _truncated, _info = env.step(arm)
            wins += int(reward)
            env.reset()  # next pull starts from a new base payload
        means[arm] = wins / pulls_per_arm
    return means


def defender_label(defender: dict) -> str:
    """Matches bandit_arm_means.py's `defender` column: {"type": "modsec", ...} -> "modsec-pl1"."""
    if defender["type"] != "modsec":
        raise ValueError(f"no offline arm means for defender type {defender['type']!r}")
    return f"modsec-pl{defender['paranoia_level']}"


def load_arm_means(path: Path, defender: str) -> np.ndarray:
    """μ_a for every arm against `defender` (a label like "modsec-pl1"), from a means CSV."""
    means = {}
    with Path(path).open() as handle:
        for row in csv.DictReader(handle):
            if row["defender"] == defender:
                means[int(row["arm"])] = float(row["mu"])
    if not means:
        raise KeyError(f"no arm means recorded for defender {defender!r} in {path}")
    return np.array([means[arm] for arm in sorted(means)])


def regret_curve(chosen_arms, mu_per_step) -> np.ndarray:
    """Cumulative R(t) = Σ (μ* − μ_{a_t}); `mu_per_step` is one μ vector or one row per step."""
    chosen = np.asarray(chosen_arms, dtype=int)
    mu = np.asarray(mu_per_step, dtype=float)
    if mu.ndim == 1:
        mu = np.broadcast_to(mu, (len(chosen), mu.shape[0]))
    instant = mu.max(axis=1) - mu[np.arange(len(chosen)), chosen]
    return np.cumsum(instant)
