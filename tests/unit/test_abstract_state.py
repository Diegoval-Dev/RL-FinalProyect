"""F1-T12: the abstract state is a bijection onto [0, 120)."""

import itertools

from wafarena.envs.abstract_state import (
    N_BUCKETS,
    N_FAMILIES,
    N_RESPONSES,
    N_STATES,
    AbstractState,
    decode,
    mutation_bucket,
)

BUCKET_REPRESENTATIVE = {0: 0, 1: 1, 2: 3, 3: 6}


def test_encode_covers_every_state_exactly_once():
    seen = set()
    for family, response, bucket in itertools.product(
        range(N_FAMILIES), range(N_RESPONSES), range(N_BUCKETS)
    ):
        state = AbstractState(family, response, BUCKET_REPRESENTATIVE[bucket]).encode()
        assert state not in seen
        seen.add(state)
    assert seen == set(range(N_STATES))


def test_decode_inverts_encode():
    for family, response, bucket in itertools.product(
        range(N_FAMILIES), range(N_RESPONSES), range(N_BUCKETS)
    ):
        state = AbstractState(family, response, BUCKET_REPRESENTATIVE[bucket]).encode()
        assert decode(state) == (family, response, bucket)


def test_mutation_bucket_boundaries():
    assert [mutation_bucket(m) for m in (0, 1, 2, 3, 5, 6, 99)] == [0, 1, 1, 2, 2, 3, 3]
