"""F2-T05: the n-gram hashing in the attacker observation is fast and still deterministic.

A cryptographic hash (SHA1) per n-gram made long, heavily mutated payloads (CHR() encoding,
string concatenation) dominate every episode's cost; a non-cryptographic hash is enough here —
only a stable bucket assignment is needed, not collision resistance.
"""

import time

import numpy as np

from wafarena.envs.attacker_obs import NGRAM_SIZE, ngram_hashing

# ~400 chars: generous over the ~160-char worst case seen after 25 chained mutations (REGISTRY).
LONG_PAYLOAD = "'" + "||".join(f"CHR({i % 256})" for i in range(50)) + "'"


def test_output_shape_and_l2_normalization():
    vector = ngram_hashing("short payload")
    assert vector.shape == (NGRAM_SIZE,)
    assert np.isclose(np.linalg.norm(vector), 1.0)


def test_empty_text_is_the_zero_vector():
    assert np.array_equal(ngram_hashing(""), np.zeros(NGRAM_SIZE, dtype=np.float32))


def test_hashing_is_deterministic_across_calls_and_instances():
    assert np.array_equal(ngram_hashing(LONG_PAYLOAD), ngram_hashing(LONG_PAYLOAD))


def test_different_text_gives_a_different_vector():
    assert not np.array_equal(ngram_hashing("abc"), ngram_hashing("abd"))


def test_long_mutated_payload_hashes_well_under_a_millisecond():
    started = time.perf_counter()
    for _ in range(200):
        ngram_hashing(LONG_PAYLOAD)
    elapsed = (time.perf_counter() - started) / 200
    assert elapsed < 0.001, (
        f"{elapsed * 1000:.3f} ms per call: n-gram hashing is still the hot path"
    )
