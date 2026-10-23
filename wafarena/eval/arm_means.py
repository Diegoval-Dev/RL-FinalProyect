"""Offline estimate of each bandit arm's mean reward, for the regret R(t) (metricas.md)."""

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
