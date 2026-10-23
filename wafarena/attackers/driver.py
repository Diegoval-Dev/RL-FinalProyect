"""AttackerDriver: wraps a trained Attacker-v0 Agent as an AttackerPolicy (agentes-y-checkpoints).

Lets a checkpoint from Phase 2/3 (ATK-REF-0, ATK-REF-1, ...) attack through `Defender-v0`. Unlike
Attacker-v0, Defender-v0 gives the attacker no backend or oracle: a mutation is applied blindly,
exactly like `RandomMutationAttacker` already does, and `next_request`'s `last_response` is
always one of `NONE`/`PASS_EFFECT`/`PASS_NO_EFFECT`/`BLOCKED` — `defender_env.py` itself collapses
CAPTCHA and RATE_LIMITED into `BLOCKED` before the attacker ever sees it, so no further
approximation is needed here to reuse those values directly as `Response` members.

`AttackerPolicy.reset` does not carry the base payload's family, so it is recovered by matching
`base.text` against the frozen corpus — exact, since `base` always comes from that same corpus.
"""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from wafarena.agents.base import Agent, strip_ground_truth
from wafarena.attackers.base import Response
from wafarena.envs.abstract_state import AbstractState
from wafarena.envs.attacker_env import SEND_ACTION
from wafarena.envs.attacker_obs import encode_observation, family_index, initial_responses
from wafarena.mutations.payload import Payload
from wafarena.mutations.registry import REGISTRY

CORPUS_PATH = Path("data/payloads/corpus.jsonl")
DEFAULT_QUERY_BUDGET = 50
DEFAULT_BAN_THRESHOLD = 10
DEFAULT_MAX_STEPS = 150


@lru_cache(maxsize=1)
def _text_to_family() -> dict[str, str]:
    return {
        entry["text"]: entry["family"]
        for entry in (json.loads(line) for line in CORPUS_PATH.read_text().splitlines())
    }


def _family_of(text: str) -> str:
    try:
        return _text_to_family()[text]
    except KeyError:
        raise ValueError(f"base payload text not found in the frozen corpus: {text!r}") from None


class AttackerDriver:
    def __init__(
        self,
        agent: Agent,
        *,
        query_budget: int = DEFAULT_QUERY_BUDGET,
        ban_threshold: int = DEFAULT_BAN_THRESHOLD,
        max_steps: int = DEFAULT_MAX_STEPS,
    ):
        if agent.role != "attacker":
            raise ValueError(f"AttackerDriver needs an attacker agent, got role {agent.role!r}")
        self._agent = agent
        self._query_budget, self._ban_threshold, self._max_steps = (
            query_budget,
            ban_threshold,
            max_steps,
        )

    def reset(self, base: Payload, endpoint: str, rng: np.random.Generator) -> None:
        self._payload = base
        self._family = _family_of(base.text)
        self._rng = rng
        self._responses = initial_responses()
        self._mutations = self._queries = self._blocks = 0
        self._done = False
        self._awaiting_first_request = True

    def next_request(self, last_response: int) -> Payload | None:
        if self._done:
            return None
        if not self._awaiting_first_request and self._record_response(last_response):
            return None
        self._awaiting_first_request = False
        for _ in range(self._max_steps):
            if self._queries >= self._query_budget:
                self._done = True
                return None
            action = int(
                self._agent.act(self._obs(), strip_ground_truth(self._info()), explore=False)
            )
            if action == SEND_ACTION:
                self._queries += 1
                return self._payload
            mutated = REGISTRY[action].apply(self._payload, self._rng)
            if mutated is not None:
                self._payload = mutated
            self._mutations += 1
        self._done = True  # safety: never reached SEND within max_steps
        return None

    def _record_response(self, last_response: int) -> bool:
        """Updates state for the previous SEND's outcome; returns True if the session is over."""
        self._responses.insert(0, int(last_response))
        if last_response == int(Response.PASS_EFFECT):
            self._done = True
            return True
        if last_response == int(Response.BLOCKED):
            self._blocks += 1
            if self._blocks >= self._ban_threshold:
                self._done = True
                return True
        return False

    def _obs(self) -> np.ndarray:
        return encode_observation(
            self._payload.text,
            self._responses[:4],
            self._mutations,
            self._max_steps,
            self._queries,
            self._query_budget,
            self._blocks,
            self._ban_threshold,
            self._family,
        )

    def _info(self) -> dict:
        return {
            "abstract_state": AbstractState(
                family_index(self._family), self._responses[0], self._mutations
            ).encode(),
            "payload": self._payload.text,
            "family": self._family,
            "mutations": self._mutations,
            "queries_used": self._queries,
            "blocks": self._blocks,
        }
