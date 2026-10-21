"""WafArena/Attacker-v0: evade the defender starting from a base payload (env-atacante.md)."""

import json
from dataclasses import dataclass
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from wafarena.attackers.base import Response
from wafarena.defenders.base import Action
from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs.abstract_state import AbstractState
from wafarena.envs.attacker_obs import OBS_SIZE, encode_observation, family_index
from wafarena.envs.backends.base import Backend
from wafarena.features.modsec import modsec_features
from wafarena.features.request import RequestInput, request_features
from wafarena.mutations.payload import Payload
from wafarena.mutations.registry import REGISTRY
from wafarena.splits.builder import SPLITS_PATH

N_ACTIONS = len(REGISTRY) + 1
SEND_ACTION = len(REGISTRY)
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
REWARD_STEP = -0.1
REWARD_BROKEN = -5.0
REWARD_EVADED = 10.0
REWARD_BLOCKED = -1.0


@dataclass
class _BasePayload:
    base_id: str
    family: str
    endpoint: str
    text: str
    location: str


def _load_bases(split: str) -> list[_BasePayload]:
    splits = json.loads(SPLITS_PATH.read_text())["payloads"]
    allowed = set(splits[split])
    bases = []
    for line in CORPUS_PATH.read_text().splitlines():
        entry = json.loads(line)
        if entry["id"] in allowed:
            bases.append(
                _BasePayload(
                    entry["id"],
                    entry["family"],
                    entry["endpoint"],
                    entry["text"],
                    entry["location"],
                )
            )
    return bases


class AttackerEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        backend: Backend,
        defender=None,
        split="train",
        query_budget=50,
        ban_threshold=10,
        max_steps=150,
        families=None,
    ):
        self.observation_space = spaces.Box(0.0, 1.0, shape=(OBS_SIZE,), dtype=np.float32)
        self.action_space = spaces.Discrete(N_ACTIONS)
        self._backend = backend
        self._defender = defender or ModSecDefender(1)
        self._bases = [b for b in _load_bases(split) if families is None or b.family in families]
        self._query_budget = query_budget
        self._ban_threshold = ban_threshold
        self._max_steps = max_steps

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        options = options or {}
        base = self._select_base(options)
        self._base = base
        self._param = PARAM_BY_ENDPOINT[base.endpoint]
        self._payload = Payload(base.text, base.location, 0)
        self._responses = [int(Response.NONE)]
        self._mutations = self._queries = self._blocks = self._steps = 0
        return self._obs(), self._info()

    def _select_base(self, options):
        if "base_id" in options:
            return next(b for b in self._bases if b.base_id == options["base_id"])
        return self._bases[int(self.np_random.integers(len(self._bases)))]

    def step(self, action: int):
        self._steps += 1
        if action == SEND_ACTION:
            reward, terminated = self._send()
        else:
            reward, terminated = self._mutate(action)
        truncated = self._queries >= self._query_budget or self._steps >= self._max_steps
        if self._blocks >= self._ban_threshold:
            terminated = True
        return self._obs(), reward, terminated, truncated, self._info(terminated)

    def _mutate(self, action: int):
        operator = REGISTRY[action]
        mutated = operator.apply(self._payload, self.np_random)
        self._mutations += 1
        if mutated is None or mutated == self._payload:
            self._noop = True
            return REWARD_STEP, False
        result = self._backend.check_functional(mutated, self._base.endpoint, self._param)
        if not result.functional:
            self._broken = True
            return REWARD_STEP + REWARD_BROKEN, False
        self._payload = mutated
        return REWARD_STEP, False

    def _send(self):
        self._queries += 1
        result = self._backend.probe(self._payload, self._base.endpoint, self._param)
        defender_obs = self._defender_obs(result)
        self._defender.reset_session(self._base.base_id)
        action = Action(self._defender.act(defender_obs))
        response = self._response_class(action, result)
        self._responses.insert(0, int(response))
        self._last_defender_action = int(action)
        self._last_oracle = result.oracle
        if response == Response.PASS_EFFECT:
            return REWARD_EVADED, True
        if response in (Response.BLOCKED, Response.CAPTCHA, Response.RATE_LIMITED):
            self._blocks += 1
        return REWARD_BLOCKED, False

    def _response_class(self, action: Action, result) -> Response:
        if action == Action.BLOCK:
            return Response.BLOCKED
        if action == Action.CAPTCHA:
            return Response.CAPTCHA
        if action == Action.RATE_LIMIT:
            return Response.RATE_LIMITED
        if action == Action.HONEYPOT:
            return Response.PASS_NO_EFFECT
        return Response.PASS_EFFECT if result.oracle.effect else Response.PASS_NO_EFFECT

    def _defender_obs(self, result) -> np.ndarray:
        obs = np.zeros(37, dtype=np.float32)
        obs[:12] = request_features(RequestInput(params={self._param: self._payload.text}))
        obs[12:16] = modsec_features(result.modsec_scores)
        return obs

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
            self._base.family,
        )

    def _info(self, terminated=False) -> dict:
        info = {
            "abstract_state": AbstractState(
                family_index(self._base.family), self._responses[0], self._mutations
            ).encode(),
            "payload": self._payload.text,
            "base_id": self._base.base_id,
            "family": self._base.family,
            "endpoint": self._base.endpoint,
            "response": self._responses[0],
            "queries_used": self._queries,
            "blocks": self._blocks,
            "mutations": self._mutations,
            "noop": getattr(self, "_noop", False),
            "broken": getattr(self, "_broken", False),
            "evaded": self._responses[0] == int(Response.PASS_EFFECT),
            "banned": self._blocks >= self._ban_threshold,
        }
        if hasattr(self, "_last_defender_action"):
            info["gt_defender_action"] = self._last_defender_action
            info["gt_oracle"] = dict(vars(self._last_oracle))
        self._noop = self._broken = False
        return info
