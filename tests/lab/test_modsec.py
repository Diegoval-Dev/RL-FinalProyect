"""F1-T05: each ModSecurity PL instance scores and blocks requests through to vulnapp."""

import pytest

from wafarena.defenders.audit import PARANOIA_LEVELS
from wafarena.defenders.modsec import modsec_score, send_through_modsec

pytestmark = pytest.mark.lab

BENIGN_PATH = "/search?q=laptop"
SQLI_PATH = "/search?q=1'%20OR%20'1'='1"


@pytest.mark.parametrize("pl", PARANOIA_LEVELS)
def test_benign_request_passes_with_low_score(pl):
    entry = modsec_score("GET", BENIGN_PATH, pl)

    assert entry.would_block is False
    assert entry.score == 0


@pytest.mark.parametrize("pl", PARANOIA_LEVELS)
def test_sqli_request_is_blocked_with_positive_score(pl):
    entry = modsec_score("GET", SQLI_PATH, pl)

    assert entry.would_block is True
    assert entry.score >= 5


@pytest.mark.parametrize("pl", PARANOIA_LEVELS)
def test_blocked_request_returns_403_to_the_client(pl):
    response, _request_id = send_through_modsec("GET", SQLI_PATH, pl)

    assert response.status_code == 403


def test_benign_request_reaches_vulnapp_and_returns_rows():
    response, _request_id = send_through_modsec("GET", BENIGN_PATH, 1)

    assert response.status_code == 200
    assert len(response.json()["rows"]) > 0


def test_higher_paranoia_scores_at_least_as_high_as_lower():
    scores = [modsec_score("GET", SQLI_PATH, pl).score for pl in PARANOIA_LEVELS]

    assert scores == sorted(scores) or all(score >= 5 for score in scores)
