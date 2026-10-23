"""F2-T05: the fast backend scores the missing paranoia levels concurrently and counts cache use."""

import threading
import time

import pytest

from wafarena.defenders.audit import AuditEntry
from wafarena.envs.backends.cache import ModSecCache
from wafarena.envs.backends.fast import FastBackend
from wafarena.mutations.payload import Payload
from wafarena.oracle import OracleResult


class StubOracle:
    def check_direct(self, payload, endpoint, param):
        return OracleResult(True, True, "structure_change", "stub")


def make_backend(tmp_path, score_fn):
    return FastBackend(
        oracle=StubOracle(), cache=ModSecCache(tmp_path / "c.json"), score_fn=score_fn
    )


def score_by_pl(method, path, pl):
    return AuditEntry("r", score=pl * 3, would_block=pl >= 2, http_code=200)


PAYLOAD = Payload("1' OR '1'='1", "query", 0)


def test_scores_and_blocks_are_mapped_to_the_right_paranoia_level(tmp_path):
    result = make_backend(tmp_path, score_by_pl).probe(PAYLOAD, "search", "q")
    assert result.modsec_scores == {1: 3, 2: 6, 3: 9, 4: 12}
    assert result.modsec_block == {1: False, 2: True, 3: True, 4: True}


def test_missing_levels_are_scored_concurrently(tmp_path):
    inside = 0
    peak = 0
    lock = threading.Lock()

    def slow_score(method, path, pl):
        nonlocal inside, peak
        with lock:
            inside += 1
            peak = max(peak, inside)
        time.sleep(0.05)
        with lock:
            inside -= 1
        return score_by_pl(method, path, pl)

    started = time.perf_counter()
    make_backend(tmp_path, slow_score).probe(PAYLOAD, "search", "q")
    assert peak == 4
    assert time.perf_counter() - started < 0.15  # four sequential calls would take 0.2 s


def test_only_uncached_levels_are_requested(tmp_path):
    calls = []

    def recording(method, path, pl):
        calls.append(pl)
        return score_by_pl(method, path, pl)

    backend = make_backend(tmp_path, recording)
    backend.probe(PAYLOAD, "search", "q")
    assert sorted(calls) == [1, 2, 3, 4]
    backend.probe(PAYLOAD, "search", "q")
    assert sorted(calls) == [1, 2, 3, 4]


def test_cache_counts_hits_and_misses(tmp_path):
    backend = make_backend(tmp_path, score_by_pl)
    backend.probe(PAYLOAD, "search", "q")
    backend.probe(PAYLOAD, "search", "q")
    assert backend.cache_stats() == {"hits": 4, "misses": 4, "hit_rate": pytest.approx(0.5)}


def test_scoring_errors_propagate(tmp_path):
    def failing(method, path, pl):
        raise TimeoutError("no audit entry")

    with pytest.raises(TimeoutError):
        make_backend(tmp_path, failing).probe(PAYLOAD, "search", "q")
