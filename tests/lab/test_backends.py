"""F1-T11: fast and real backends agree, and the fast backend sustains the step budget."""

import json
import time
from pathlib import Path

import pytest

from wafarena.envs.backends import FastBackend, RealBackend
from wafarena.envs.backends.cache import ModSecCache
from wafarena.features.modsec import PARANOIA_LEVELS
from wafarena.mutations.payload import Payload

pytestmark = pytest.mark.lab

CORPUS_PATH = Path("data/payloads/corpus.jsonl")
PARAM_BY_ENDPOINT = {
    "catalog": "category",
    "search": "q",
    "product": "id",
    "login": "username",
    "sort": "order",
    "comments": "body",
    "orders": "user_id",
    "cart_add": "qty",
}
SAMPLE_SIZE = 250
MIN_AGREEMENT = 0.99
MIN_STEPS_PER_SECOND = 300
PERF_STEPS = 2000


def sample_payloads(n: int) -> list[tuple[Payload, str, str]]:
    lines = CORPUS_PATH.read_text().splitlines()[:n]
    items = []
    for line in lines:
        entry = json.loads(line)
        param = PARAM_BY_ENDPOINT[entry["endpoint"]]
        items.append((Payload(entry["text"], entry["location"], 0), entry["endpoint"], param))
    return items


def signature(result) -> tuple:
    blocks = tuple(result.modsec_block[pl] for pl in PARANOIA_LEVELS)
    return (result.oracle.functional, result.oracle.effect, blocks)


def test_fast_and_real_backends_agree_on_at_least_99_percent(tmp_path):
    fast = FastBackend(cache=ModSecCache(tmp_path / "c.json"))
    real = RealBackend()
    payloads = sample_payloads(SAMPLE_SIZE)

    agree = sum(signature(fast.probe(*p)) == signature(real.probe(*p)) for p in payloads)
    fast.close()

    assert agree / len(payloads) >= MIN_AGREEMENT, f"{agree}/{len(payloads)}"


def test_fast_backend_sustains_300_steps_per_second_with_warm_cache(tmp_path):
    fast = FastBackend(cache=ModSecCache(tmp_path / "c.json"))
    payloads = sample_payloads(SAMPLE_SIZE)
    for payload in payloads:  # warm the caches
        fast.probe(*payload)

    start = time.perf_counter()
    for i in range(PERF_STEPS):
        fast.check_functional(*payloads[i % len(payloads)])
    elapsed = time.perf_counter() - start
    rate = PERF_STEPS / elapsed

    assert rate >= MIN_STEPS_PER_SECOND, f"{rate:.0f} steps/s"
