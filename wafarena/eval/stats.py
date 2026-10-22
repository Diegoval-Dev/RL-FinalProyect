"""Bootstrap confidence intervals over seeds (metricas.md, Estadística)."""

from collections.abc import Sequence
from typing import NamedTuple

import numpy as np

N_RESAMPLES = 10_000
CONFIDENCE = 0.95


class CI(NamedTuple):
    mean: float
    low: float
    high: float

    @property
    def contains_zero(self) -> bool:
        return self.low <= 0.0 <= self.high


def _validate(confidence: float, n_resamples: int) -> None:
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be in (0, 1), got {confidence}")
    if n_resamples < 1:
        raise ValueError(f"n_resamples must be positive, got {n_resamples}")


def _percentile_interval(samples: np.ndarray, confidence: float) -> tuple[float, float]:
    tail = (1.0 - confidence) / 2.0 * 100.0
    low, high = np.percentile(samples, [tail, 100.0 - tail])
    return float(low), float(high)


def _as_sample(values: Sequence[float]) -> np.ndarray:
    sample = np.asarray(values, dtype=float)
    if sample.size == 0:
        raise ValueError("bootstrap needs at least one value")
    return sample


def bootstrap_ci(
    values: Sequence[float],
    *,
    confidence: float = CONFIDENCE,
    n_resamples: int = N_RESAMPLES,
    seed: int = 0,
) -> CI:
    """Percentile bootstrap CI of the mean of `values` (one value per seed)."""
    _validate(confidence, n_resamples)
    sample = _as_sample(values)
    rng = np.random.default_rng(seed)
    means = rng.choice(sample, size=(n_resamples, sample.size)).mean(axis=1)
    low, high = _percentile_interval(means, confidence)
    return CI(float(sample.mean()), low, high)


def bootstrap_diff_ci(
    a: Sequence[float],
    b: Sequence[float],
    *,
    confidence: float = CONFIDENCE,
    n_resamples: int = N_RESAMPLES,
    seed: int = 0,
) -> CI:
    """Percentile bootstrap CI of mean(a) − mean(b), resampling each group independently."""
    _validate(confidence, n_resamples)
    sample_a, sample_b = _as_sample(a), _as_sample(b)
    rng = np.random.default_rng(seed)
    means_a = rng.choice(sample_a, size=(n_resamples, sample_a.size)).mean(axis=1)
    means_b = rng.choice(sample_b, size=(n_resamples, sample_b.size)).mean(axis=1)
    low, high = _percentile_interval(means_a - means_b, confidence)
    return CI(float(sample_a.mean() - sample_b.mean()), low, high)
