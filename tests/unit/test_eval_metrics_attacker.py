"""F2-T04: attacker metrics of metricas.md against cases computed by hand."""

import math

import numpy as np
import pytest

from wafarena.eval import metrics
from wafarena.eval.metrics import EpisodeResult


def episode(evaded: bool, queries: int, attempts: int = 0, broken: int = 0, payload: str = "p"):
    return EpisodeResult(
        seed=0,
        base_id="b",
        family="tautology",
        evaded=evaded,
        banned=False,
        queries_used=queries,
        mutation_attempts=attempts,
        broken=broken,
        payload=payload,
    )


EPISODES = [
    episode(True, 3, attempts=10, broken=2, payload="a"),
    episode(True, 5, attempts=6, broken=1, payload="b"),
    episode(False, 50, attempts=4, broken=1),
    episode(True, 10, attempts=0, broken=0, payload="a"),
]


def test_evasion_rate_counts_evaded_episodes_over_all():
    assert metrics.evasion_rate(EPISODES) == pytest.approx(3 / 4)


def test_evasion_rate_of_empty_suite_raises():
    with pytest.raises(ValueError):
        metrics.evasion_rate([])


def test_queries_to_first_evasion_is_median_over_successes_only():
    assert metrics.queries_to_first_evasion(EPISODES) == 5  # median of 3, 5, 10


def test_queries_to_first_evasion_is_nan_without_successes():
    assert math.isnan(metrics.queries_to_first_evasion([episode(False, 50)]))


def test_censored_queries_treats_failures_as_the_budget():
    assert metrics.censored_queries(EPISODES, query_budget=50) == pytest.approx(
        (3 + 5 + 50 + 10) / 4
    )


def test_break_rate_is_broken_mutations_over_attempted_mutations():
    assert metrics.break_rate(EPISODES) == pytest.approx(4 / 20)


def test_break_rate_is_nan_without_mutations():
    assert math.isnan(metrics.break_rate([episode(False, 1)]))


@pytest.mark.parametrize(
    ("a", "b", "distance"),
    [("", "", 0), ("abc", "abc", 0), ("kitten", "sitting", 3), ("abc", "", 3), ("ab", "ba", 2)],
)
def test_levenshtein_matches_known_distances(a, b, distance):
    assert metrics.levenshtein(a, b) == distance


def test_normalized_levenshtein_divides_by_the_longer_string():
    assert metrics.normalized_levenshtein("kitten", "sitting") == pytest.approx(3 / 7)
    assert metrics.normalized_levenshtein("", "") == 0.0


def test_diversity_is_mean_normalized_distance_over_distinct_pairs():
    # distinct payloads "ab", "ac", "zz": distances ab-ac 1/2, ab-zz 2/2, ac-zz 2/2.
    value = metrics.diversity(["ab", "ac", "ab", "zz"])
    assert value == pytest.approx((0.5 + 1.0 + 1.0) / 3)


def test_diversity_is_nan_with_fewer_than_two_distinct_payloads():
    assert math.isnan(metrics.diversity(["a", "a"]))
    assert math.isnan(metrics.diversity([]))


def test_diversity_samples_at_most_max_pairs_and_is_deterministic():
    payloads = [f"payload-{i}" for i in range(60)]  # 1 770 pairs
    first = metrics.diversity(payloads, max_pairs=500, seed=1)
    assert first == metrics.diversity(payloads, max_pairs=500, seed=1)
    exact = metrics.diversity(payloads, max_pairs=10_000)
    assert first == pytest.approx(exact, abs=0.05)


def test_uniqueness_is_unique_over_total_successful_payloads():
    assert metrics.uniqueness(["a", "b", "a", "c"]) == pytest.approx(3 / 4)
    assert math.isnan(metrics.uniqueness([]))


def test_cumulative_regret_sums_gap_to_best_arm():
    mu = np.array([0.1, 0.5, 0.3])
    regret = metrics.cumulative_regret(mu, [0, 1, 2, 1])
    assert regret == pytest.approx([0.4, 0.4, 0.6, 0.6])
