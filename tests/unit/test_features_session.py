"""F1-T10: session (16-20) and window (21-36) features follow features.md."""

import pytest

from wafarena.features.request import RequestInput
from wafarena.features.session import (
    SESSION_FEATURE_NAMES,
    WINDOW_SIZE,
    SessionTracker,
)

DENY = False
ALLOW = True


def test_session_block_has_five_features_and_window_has_sixteen():
    tracker = SessionTracker()

    assert len(SESSION_FEATURE_NAMES) == 5
    assert len(tracker.window_features()) == WINDOW_SIZE * 4


def test_fresh_session_features_are_all_zero():
    tracker = SessionTracker()

    assert tracker.session_features() == (0.0, 0.0, 0.0, 0.0, 0.0)
    assert tracker.window_features() == (0.0,) * (WINDOW_SIZE * 4)


def test_prior_denials_counts_non_allowed_requests():
    tracker = SessionTracker()
    for _ in range(3):
        tracker.record(RequestInput(params={"q": "x"}), modsec_pl2=0.0, allowed=DENY)

    features = dict(zip(SESSION_FEATURE_NAMES, tracker.session_features(), strict=True))
    assert features["prior_denials"] == pytest.approx(3 / 10)


def test_sql_kw_frac_is_fraction_of_prior_requests_with_sql_keywords():
    tracker = SessionTracker()
    tracker.record(RequestInput(params={"q": "union select"}), modsec_pl2=0.0, allowed=ALLOW)
    tracker.record(RequestInput(params={"q": "hello"}), modsec_pl2=0.0, allowed=ALLOW)

    features = dict(zip(SESSION_FEATURE_NAMES, tracker.session_features(), strict=True))
    assert features["sql_kw_frac"] == pytest.approx(0.5)


def test_window_holds_the_four_most_recent_requests_most_recent_first():
    tracker = SessionTracker()
    tracker.record(RequestInput(params={"q": "aaaa"}), modsec_pl2=0.1, allowed=DENY)
    tracker.record(RequestInput(params={"q": "bbbb"}), modsec_pl2=0.2, allowed=ALLOW)

    window = tracker.window_features()
    # most recent (bbbb, allowed) first: was_denied slot == 0
    assert window[3] == 0.0
    # second slot is the older denied request: was_denied == 1
    assert window[7] == 1.0


def test_window_is_zero_padded_when_fewer_than_four_requests():
    tracker = SessionTracker()
    tracker.record(RequestInput(params={"q": "x"}), modsec_pl2=0.5, allowed=ALLOW)

    window = tracker.window_features()
    assert window[4 * 1 :] == (0.0,) * (4 * (WINDOW_SIZE - 1))
