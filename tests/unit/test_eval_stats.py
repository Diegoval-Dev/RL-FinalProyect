"""F2-T04: bootstrap confidence intervals (metricas.md, Estadística)."""

import numpy as np
import pytest

from wafarena.eval.stats import CI, bootstrap_ci, bootstrap_diff_ci


def test_bootstrap_ci_of_constant_values_collapses_to_the_constant():
    ci = bootstrap_ci([0.3] * 10)
    assert ci == CI(mean=pytest.approx(0.3), low=pytest.approx(0.3), high=pytest.approx(0.3))


def test_bootstrap_ci_matches_hand_computed_interval_for_bernoulli_sample():
    # 50 zeros and 50 ones: mean 0.5, SE = 0.5 / sqrt(100) = 0.05, so 95 % CI ≈ 0.5 ± 1.96 * 0.05.
    ci = bootstrap_ci([0] * 50 + [1] * 50)
    assert ci.mean == pytest.approx(0.5)
    assert ci.low == pytest.approx(0.402, abs=0.01)
    assert ci.high == pytest.approx(0.598, abs=0.01)


def test_bootstrap_ci_width_tracks_the_standard_error_of_a_normal_sample():
    sample = np.random.default_rng(123).normal(0.0, 1.0, 400)
    ci = bootstrap_ci(sample)
    expected_width = 2 * 1.96 * sample.std(ddof=1) / np.sqrt(len(sample))
    assert ci.low < sample.mean() < ci.high
    assert ci.high - ci.low == pytest.approx(expected_width, abs=0.02)


def test_bootstrap_ci_is_deterministic_given_seed():
    values = [0.1, 0.4, 0.2, 0.9, 0.5]
    assert bootstrap_ci(values, seed=3) == bootstrap_ci(values, seed=3)
    assert bootstrap_ci(values, seed=3) != bootstrap_ci(values, seed=4)


def test_bootstrap_ci_single_value_is_degenerate():
    assert bootstrap_ci([0.7]) == CI(0.7, 0.7, 0.7)


@pytest.mark.parametrize("kwargs", [{"confidence": 0.0}, {"confidence": 1.0}, {"n_resamples": 0}])
def test_bootstrap_ci_rejects_invalid_arguments(kwargs):
    with pytest.raises(ValueError):
        bootstrap_ci([1.0, 2.0], **kwargs)


def test_bootstrap_ci_rejects_empty_input():
    with pytest.raises(ValueError):
        bootstrap_ci([])


def test_bootstrap_diff_ci_excludes_zero_when_groups_clearly_differ():
    rng = np.random.default_rng(0)
    a = rng.normal(1.0, 0.1, 10)
    b = rng.normal(0.0, 0.1, 10)
    ci = bootstrap_diff_ci(a, b)
    assert ci.mean == pytest.approx(a.mean() - b.mean())
    assert ci.low > 0 and not ci.contains_zero


def test_bootstrap_diff_ci_contains_zero_for_identical_groups():
    values = [0.2, 0.4, 0.3, 0.5, 0.1]
    assert bootstrap_diff_ci(values, values).contains_zero
