"""Drivers that turn a trained Agent into a Fase-1 policy (agentes-y-checkpoints.md)."""

import numpy as np

from wafarena.envs.attacker_obs import encode_observation
from wafarena.mutations.payload import Payload
from wafarena.mutations.registry import REGISTRY

SEND_ACTION = len(REGISTRY)
MAX_INTERNAL_STEPS = 150


class DefenderDriver:
    def __init__(self, agent):
        self._agent = agent

    def reset_session(self, session_id: str) -> None:
        reset = getattr(self._agent, "reset_session", None)
        if callable(reset):
            reset(session_id)

    def act(self, obs: np.ndarray) -> int:
        return int(self._agent.act(obs, {}, explore=False))


class AttackerDriver:
    """Runs the agent over the 288-dim observation, applying operators until it chooses SEND."""

    def __init__(self, agent, backend):
        self._agent = agent
        self._backend = backend

    def reset(self, base: Payload, endpoint: str, rng: np.random.Generator) -> None:
        self._payload = base
        self._endpoint = endpoint
        self._param = _PARAM_BY_ENDPOINT[endpoint]
        self._rng = rng
        self._mutations = 0

    def next_request(self, last_response: int) -> Payload | None:
        for _ in range(MAX_INTERNAL_STEPS):
            obs = encode_observation(
                self._payload.text,
                [last_response],
                self._mutations,
                MAX_INTERNAL_STEPS,
                0,
                1,
                0,
                1,
                _family_placeholder(),
            )
            action = int(self._agent.act(obs, {}, explore=False))
            if action == SEND_ACTION:
                return self._payload
            mutated = REGISTRY[action].apply(self._payload, self._rng)
            self._mutations += 1
            if (
                mutated is not None
                and self._backend.check_functional(mutated, self._endpoint, self._param).functional
            ):
                self._payload = mutated
        return self._payload


def _family_placeholder() -> str:
    return "union"


_PARAM_BY_ENDPOINT = {
    "catalog": "category",
    "search": "q",
    "product": "id",
    "login": "username",
    "sort": "order",
    "comments": "body",
    "orders": "user_id",
    "cart_add": "qty",
}
