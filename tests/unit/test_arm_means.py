"""F2-T05: offline estimate of each arm's mean reward (metricas.md, Regret acumulado)."""

import zlib

import numpy as np
import pytest

from wafarena.envs.backends.base import BackendResult
from wafarena.envs.backends.fake import FakeBackend
from wafarena.eval.arm_means import estimate_arm_means

DEFENDER = {"type": "modsec", "paranoia_level": 1}


class CoinBackend(FakeBackend):
    """Lets a payload through when a hash of its text is even: evasion is neither 0 nor 1."""

    def probe(self, payload, endpoint, param):
        result = super().probe(payload, endpoint, param)
        score = 0 if zlib.crc32(payload.text.encode()) % 2 == 0 else 9
        scores = {pl: score for pl in result.modsec_scores}
        return BackendResult(result.oracle, scores, {pl: score >= 5 for pl in scores})


def estimate(**kwargs):
    return estimate_arm_means(CoinBackend(), DEFENDER, pulls_per_arm=30, seed=0, **kwargs)


def test_returns_one_mean_per_arm_inside_the_unit_interval():
    means = estimate()
    assert means.shape == (16,)
    assert np.all((means >= 0.0) & (means <= 1.0))


def test_estimate_is_reproducible_for_a_fixed_seed():
    assert np.array_equal(estimate(), estimate())


def test_arms_have_nontrivial_means_with_a_coin_defender():
    means = estimate()
    assert 0.0 < means.mean() < 1.0


def test_estimate_changes_with_the_seed():
    other = estimate_arm_means(CoinBackend(), DEFENDER, pulls_per_arm=30, seed=1)
    assert not np.array_equal(estimate(), other)


def test_means_are_multiples_of_one_over_the_number_of_pulls():
    assert np.allclose(estimate() * 30, np.round(estimate() * 30))


def test_every_pull_starts_from_a_fresh_base_payload():
    calls = []

    class Counting(FakeBackend):
        def probe(self, payload, endpoint, param):
            calls.append(payload.text)
            return super().probe(payload, endpoint, param)

    estimate_arm_means(Counting(), DEFENDER, pulls_per_arm=5, seed=0)
    assert len(calls) == 16 * 5  # one SEND per pull, no state carried between pulls


def test_rejects_non_positive_number_of_pulls():
    with pytest.raises(ValueError):
        estimate_arm_means(FakeBackend(), DEFENDER, pulls_per_arm=0, seed=0)


def write_csv(path, rows):
    import csv

    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["defender", "arm", "operator", "mu", "pulls", "seed", "git_sha"])
        writer.writerows(rows)


def test_load_arm_means_returns_the_mu_vector_for_one_defender(tmp_path):
    from wafarena.eval.arm_means import load_arm_means

    path = tmp_path / "m.csv"
    rows = [["modsec-pl1", a, f"op{a}", 0.1 * a, 2000, 0, "abc"] for a in range(16)]
    rows += [["modsec-pl3", a, f"op{a}", 0.5, 2000, 0, "abc"] for a in range(16)]
    write_csv(path, rows)
    means = load_arm_means(path, "modsec-pl1")
    assert means.shape == (16,)
    assert means[5] == pytest.approx(0.5)
    assert np.all(load_arm_means(path, "modsec-pl3") == 0.5)


def test_load_arm_means_rejects_unknown_defender(tmp_path):
    from wafarena.eval.arm_means import load_arm_means

    path = tmp_path / "m.csv"
    write_csv(path, [["modsec-pl1", a, f"op{a}", 0.0, 2000, 0, "abc"] for a in range(16)])
    with pytest.raises(KeyError, match="modsec-pl9"):
        load_arm_means(path, "modsec-pl9")
