"""F2-T05: hex_string must not grow without bound when applied to its own output.

Found running EXP-A1 against the real lab: reapplying hex_string to an already hex-encoded
literal stays oracle-functional every time (hex-of-hex is always valid hex), so an unbounded
chain balloons the payload geometrically and eventually OOMs the process handling it.
"""

import numpy as np
import pytest

from wafarena.mutations.operators import HexString
from wafarena.mutations.payload import Payload

OPERATOR = HexString()
BASE = Payload("' AND 'x' LIKE 'x' --", "query", 0)


def chain(rng: np.random.Generator, start: Payload = BASE, n: int = 30) -> list[int]:
    lengths, current = [len(start.text)], start
    for _ in range(n):
        mutated = OPERATOR.apply(current, rng)
        if mutated is None:
            break
        current = mutated
        lengths.append(len(current.text))
    return lengths


def test_first_application_still_hex_encodes_a_literal():
    rng = np.random.default_rng(0)
    lengths = chain(rng, n=1)
    assert len(lengths) == 2 and lengths[1] > lengths[0]


def test_repeated_application_stops_instead_of_growing_without_bound():
    rng = np.random.default_rng(0)
    lengths = chain(rng, n=30)
    assert len(lengths) < 30  # it gave up well before 30 applications
    assert max(lengths) < 500  # and never ballooned


@pytest.mark.parametrize("seed", range(5))
def test_bounded_on_arbitrary_text_too(seed):
    rng = np.random.default_rng(seed)
    lengths = chain(rng, start=Payload("'a' OR 'b'='b'", "query", 0), n=30)
    assert max(lengths) < 500


def test_marker_check_is_case_insensitive():
    """F2-T08: case_swap can scramble the marker's letters (convert_from -> convert_fROm),
    which a case-sensitive check would no longer recognize, letting hex_string reapply forever
    and the payload balloon (found running EXP-D1 against the real lab: an 8 KB URL with 40
    nested wraps, after case_swap had mangled the marker on every previous layer)."""
    mangled = "' AND 'x' LIKE 'x' -- convert_fROm(decode('ab','hex'),'UTF8')"
    assert OPERATOR.apply(Payload(mangled, "query", 0), np.random.default_rng(0)) is None


def test_bounded_even_when_case_swap_runs_between_applications():
    from wafarena.mutations.operators import CaseSwap

    rng = np.random.default_rng(0)
    case_swap = CaseSwap()
    current = BASE
    lengths = [len(current.text)]
    for _ in range(100):
        mutated = OPERATOR.apply(current, rng)
        if mutated is not None:
            current = mutated
        mutated = case_swap.apply(current, rng)
        if mutated is not None:
            current = mutated
        lengths.append(len(current.text))
    assert max(lengths) < 500
