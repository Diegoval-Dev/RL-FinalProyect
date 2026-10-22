"""Metrics of metricas.md, computed from per-episode and per-request records."""

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

MAX_DIVERSITY_PAIRS = 500


@dataclass(frozen=True)
class EpisodeResult:
    """Outcome of one `Attacker-v0` episode (built by the harness, free of `gt_` data)."""

    seed: int
    base_id: str
    family: str
    evaded: bool
    banned: bool
    queries_used: int
    mutation_attempts: int
    broken: int
    payload: str  # payload at the end of the episode; the successful one when `evaded`


def evasion_rate(episodes: Sequence[EpisodeResult]) -> float:
    """ER: episodes with evasion / episodes."""
    if not episodes:
        raise ValueError("evasion_rate needs at least one episode")
    return sum(e.evaded for e in episodes) / len(episodes)


def queries_to_first_evasion(episodes: Sequence[EpisodeResult]) -> float:
    """QFE: median `queries_used` over episodes with evasion (nan if none)."""
    used = [e.queries_used for e in episodes if e.evaded]
    return float(np.median(used)) if used else math.nan


def censored_queries(episodes: Sequence[EpisodeResult], query_budget: int) -> float:
    """QFE-c: mean `queries_used`, counting episodes without evasion as `query_budget`."""
    return float(np.mean([e.queries_used if e.evaded else query_budget for e in episodes]))


def break_rate(episodes: Sequence[EpisodeResult]) -> float:
    """BRK: broken mutations / mutation actions taken (nan if no mutation was tried)."""
    attempts = sum(e.mutation_attempts for e in episodes)
    return sum(e.broken for e in episodes) / attempts if attempts else math.nan


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            cost = 0 if char_a == char_b else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
        previous = current
    return previous[-1]


def normalized_levenshtein(a: str, b: str) -> float:
    longest = max(len(a), len(b))
    return levenshtein(a, b) / longest if longest else 0.0


def diversity(payloads: Sequence[str], *, max_pairs: int = MAX_DIVERSITY_PAIRS, seed: int = 0):
    """DIV: mean normalized Levenshtein distance between pairs of distinct payloads.

    Uses every pair, or `max_pairs` pairs sampled without replacement when there are more.
    nan with fewer than two distinct payloads.
    """
    distinct = sorted(set(payloads))
    if len(distinct) < 2:
        return math.nan
    n_pairs = len(distinct) * (len(distinct) - 1) // 2
    if n_pairs <= max_pairs:
        pairs = itertools.combinations(distinct, 2)
    else:
        rng = np.random.default_rng(seed)
        chosen = set()
        while len(chosen) < max_pairs:
            i, j = sorted(rng.choice(len(distinct), size=2, replace=False))
            chosen.add((int(i), int(j)))
        pairs = ((distinct[i], distinct[j]) for i, j in sorted(chosen))
    return float(np.mean([normalized_levenshtein(a, b) for a, b in pairs]))


def uniqueness(payloads: Sequence[str]) -> float:
    """UNQ: unique successful payloads / successful payloads (nan if none)."""
    return len(set(payloads)) / len(payloads) if payloads else math.nan


def cumulative_regret(arm_means: Sequence[float], chosen_arms: Sequence[int]) -> np.ndarray:
    """R(t) = Σ (μ* − μ_{a_t}) for a bandit, with `arm_means` estimated offline."""
    means = np.asarray(arm_means, dtype=float)
    return np.cumsum(means.max() - means[np.asarray(chosen_arms, dtype=int)])
