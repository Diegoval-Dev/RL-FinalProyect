"""F2-T04: a scripted attack session always sends at least one request."""

import numpy as np

from wafarena.attackers.random_mutation import DEFAULT_MAX_MUTATIONS, RandomMutationAttacker
from wafarena.mutations.payload import Payload


def session_length(seed: int) -> int:
    attacker = RandomMutationAttacker()
    attacker.reset(Payload("1' OR '1'='1", "query", 0), "search", np.random.default_rng(seed))
    sent = 0
    while attacker.next_request(3) is not None:
        sent += 1
    return sent


def test_every_session_sends_between_one_and_max_requests():
    lengths = {session_length(seed) for seed in range(200)}
    assert min(lengths) >= 1
    assert max(lengths) <= DEFAULT_MAX_MUTATIONS
    assert len(lengths) > 1  # the budget really varies
