"""F2-T04: defender metrics of metricas.md against cases computed by hand."""

import math

import pytest

from wafarena.eval import metrics
from wafarena.eval.metrics import RequestRecord

ALLOW, BLOCK, CAPTCHA, RATE_LIMIT, HONEYPOT = range(5)


def rec(is_attack: bool, action: int, effect: bool = False, session: str = "s"):
    return RequestRecord(is_attack=is_attack, action=action, effect=effect, session_id=session)


ATTACKS = [
    rec(True, ALLOW, effect=True),
    rec(True, BLOCK, effect=True),
    rec(True, CAPTCHA),
    rec(True, ALLOW),
]
BENIGN = [
    rec(False, ALLOW, session="s1"),
    rec(False, ALLOW, session="s1"),
    rec(False, CAPTCHA, session="s2"),
    rec(False, BLOCK, session="s3"),
    rec(False, HONEYPOT, session="s3"),
]
RECORDS = ATTACKS + BENIGN


def test_tpr_counts_attack_requests_not_allowed():
    assert metrics.tpr(RECORDS) == pytest.approx(2 / 4)


def test_evasion_suffered_counts_allowed_attacks_with_effect_over_attacks_with_effect():
    assert metrics.evasion_suffered(RECORDS) == pytest.approx(1 / 2)


def test_fpr_counts_benign_requests_not_allowed():
    assert metrics.fpr(RECORDS) == pytest.approx(3 / 5)


def test_fpr_hard_counts_only_block_and_honeypot():
    assert metrics.fpr_hard(RECORDS) == pytest.approx(2 / 5)


def test_fpr_by_session_counts_benign_sessions_with_any_friction():
    assert metrics.fpr_by_session(RECORDS) == pytest.approx(2 / 3)
    assert metrics.fpr_hard_by_session(RECORDS) == pytest.approx(1 / 3)


def test_f1_binarizes_action_not_allow():
    # TP = 2, FP = 3, FN = 2 → precision 2/5, recall 2/4.
    assert metrics.f1(RECORDS) == pytest.approx(2 * 0.4 * 0.5 / 0.9)


def test_defender_rates_are_nan_without_the_relevant_class():
    assert math.isnan(metrics.tpr(BENIGN))
    assert math.isnan(metrics.fpr(ATTACKS))
    assert math.isnan(metrics.evasion_suffered([rec(True, ALLOW)]))


def test_latency_percentiles_are_p50_and_p95_in_ms():
    p50, p95 = metrics.latency_percentiles(list(range(1, 101)))
    assert p50 == pytest.approx(50.5)
    assert p95 == pytest.approx(95.05)


def test_gap_is_absolute_difference_between_modes():
    assert metrics.gap(0.31, 0.25) == pytest.approx(0.06)
    assert metrics.gap(0.25, 0.31) == pytest.approx(0.06)
