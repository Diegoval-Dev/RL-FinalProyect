"""F1-T06: ModSecDefender(pl) reproduces ModSecurity's block decisions at that PL.

This is the proxy's defence decision: the proxy builds the observation from the live ModSecurity
scores and applies the policy, so matching ModSec's would_block over 500 requests proves the proxy
with ModSecDefender(pl) reproduces ModSecurity at that PL.
"""

import httpx
import pytest
from proxy.app import build_observation

from vulnapp.queries import get_endpoint
from wafarena.defenders.base import Action
from wafarena.defenders.modsec import modsec_score
from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.features.modsec import PARANOIA_LEVELS, modsec_feature_index

pytestmark = pytest.mark.lab

BENIGN = [
    ("catalog", {"category": "Libros"}),
    ("search", {"q": "laptop"}),
    ("search", {"q": "O'Brien"}),
    ("product", {"id": "3"}),
    ("orders", {"user_id": "2"}),
]
ATTACKS = [
    ("search", {"q": "1' OR '1'='1"}),
    ("search", {"q": "' UNION SELECT token, 0, 0 FROM canary_secrets --"}),
    ("catalog", {"category": "' OR 1=1 --"}),
    ("product", {"id": "1 OR 1=1"}),
    ("orders", {"user_id": "1 OR 1=1"}),
]
TOTAL_REQUESTS = 500


def cases(n: int) -> list[tuple[str, dict]]:
    pool = BENIGN + ATTACKS
    return [pool[i % len(pool)] for i in range(n)]


def live_scores(path_with_query: str) -> dict[int, int]:
    return {pl: modsec_score("GET", path_with_query, pl).score for pl in PARANOIA_LEVELS}


@pytest.mark.parametrize("pl", PARANOIA_LEVELS)
def test_defender_blocks_exactly_when_modsec_blocks_over_500_requests(pl):
    defender = ModSecDefender(pl)
    mismatches = []
    for endpoint, params in cases(TOTAL_REQUESTS // len(PARANOIA_LEVELS)):
        path = get_endpoint(endpoint).path
        query = httpx.QueryParams(params)
        path_with_query = f"{path}?{query}"
        scores = live_scores(path_with_query)
        obs = build_observation(params, body_is_json=False, scores=scores)
        defender_blocks = defender.act(obs) == Action.BLOCK
        modsec_blocks = modsec_score("GET", path_with_query, pl).would_block
        if defender_blocks != modsec_blocks:
            mismatches.append((endpoint, params, defender_blocks, modsec_blocks, scores[pl]))
    assert not mismatches, mismatches


def test_observation_places_scores_at_the_modsec_indices():
    obs = build_observation({"q": "x"}, body_is_json=False, scores={1: 50, 2: 0, 3: 0, 4: 0})

    assert obs[modsec_feature_index(1)] == pytest.approx(1.0)
    assert obs[modsec_feature_index(2)] == 0.0
