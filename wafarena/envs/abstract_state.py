"""Abstract state for tabular methods: a bijection onto [0, 120) (env-atacante.md).

abstract_state = family_idx * 24 + last_response_idx * 4 + mutation_bucket
mutation_bucket: 0 -> 0 mutations, 1 -> 1-2, 2 -> 3-5, 3 -> 6 or more.
"""

from dataclasses import dataclass

N_FAMILIES = 5
N_RESPONSES = 6
N_BUCKETS = 4
N_STATES = N_FAMILIES * N_RESPONSES * N_BUCKETS  # 120


def mutation_bucket(mutations: int) -> int:
    if mutations <= 0:
        return 0
    if mutations <= 2:
        return 1
    if mutations <= 5:
        return 2
    return 3


@dataclass(frozen=True)
class AbstractState:
    family_idx: int
    last_response_idx: int
    mutations: int

    def encode(self) -> int:
        return (
            self.family_idx * (N_RESPONSES * N_BUCKETS)
            + self.last_response_idx * N_BUCKETS
            + (mutation_bucket(self.mutations))
        )


def decode(state: int) -> tuple[int, int, int]:
    if not 0 <= state < N_STATES:
        raise ValueError(f"state {state} out of range")
    family_idx, rest = divmod(state, N_RESPONSES * N_BUCKETS)
    last_response_idx, bucket = divmod(rest, N_BUCKETS)
    return family_idx, last_response_idx, bucket
