"""WafArena/Defender-v0: defend a traffic session request by request (env-defensor.md)."""

import json
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from vulnapp.queries import ENDPOINTS
from wafarena.attackers.corpus_replay import CorpusReplayAttacker
from wafarena.attackers.random_mutation import RandomMutationAttacker
from wafarena.defenders.base import Action
from wafarena.envs.attacker_env import PARAM_BY_ENDPOINT, _load_bases
from wafarena.envs.backends.base import Backend
from wafarena.envs.resolve import resolve_attacker_type, resolve_backend
from wafarena.features.modsec import modsec_features
from wafarena.features.request import RequestInput, request_features
from wafarena.features.session import SessionTracker
from wafarena.mutations.payload import Payload
from wafarena.splits.builder import SPLITS_PATH

OBS_SIZE = 37
N_ACTIONS = 5
MAX_SESSION_STEPS = 200
ENDPOINT_BY_PATH = {spec.path: spec.name for spec in ENDPOINTS}
ATTACKERS = {"corpus_replay": CorpusReplayAttacker, "random_mutation": RandomMutationAttacker}


class DefenderEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        backend: Backend | str,
        attacker=None,
        split="train",
        attack_ratio=0.1,
        reward=None,
        benign_abandon_prob=0.0,
        attack_split=None,
    ):
        self.observation_space = spaces.Box(0.0, 1.0, shape=(OBS_SIZE,), dtype=np.float32)
        self.action_space = spaces.Discrete(N_ACTIONS)
        self._backend = resolve_backend(backend)
        self._attacker_factory = ATTACKERS[resolve_attacker_type(attacker)]
        self._attack_ratio = attack_ratio
        self._reward = reward or {"alpha": 4.0, "beta": 1.0, "gamma": 0.5}
        self._abandon_prob = benign_abandon_prob
        self._bases = _load_bases(attack_split or split)
        self._benign = _load_benign_sessions(split)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        options = options or {}
        if "base_id" in options and "session_id" in options:
            raise ValueError("reset options base_id and session_id are exclusive: got both")
        self._tracker = SessionTracker()
        if "base_id" in options:
            self._is_attack = True
        elif "session_id" in options:
            self._is_attack = False
        else:
            self._is_attack = self.np_random.random() < self._attack_ratio
        self._step_index = 0
        if self._is_attack:
            self._start_attack_session(options.get("base_id"))
        else:
            self._start_benign_session(options.get("session_id"))
        self._pending = self._next_request()
        return self._obs(), self._info()

    def _start_attack_session(self, base_id=None):
        if base_id is None:
            base = self._bases[int(self.np_random.integers(len(self._bases)))]
        else:
            base = _find(self._bases, lambda b: b.base_id == base_id, base_id)
        self._session_id = f"atk-{base.base_id}"
        self._endpoint, self._param = base.endpoint, PARAM_BY_ENDPOINT[base.endpoint]
        self._attacker = self._attacker_factory()
        self._attacker.reset(Payload(base.text, base.location, 0), base.endpoint, self.np_random)
        self._last_response = 0

    def _start_benign_session(self, session_id=None):
        if session_id is None:
            session = self._benign[int(self.np_random.integers(len(self._benign)))]
        else:
            session = _find(self._benign, lambda s: s["session_id"] == session_id, session_id)
        self._session_id = session["session_id"]
        self._benign_requests = list(session["requests"])
        self._benign_cursor = 0

    def _next_request(self):
        if self._is_attack:
            payload = self._attacker.next_request(self._last_response)
            return None if payload is None else (self._endpoint, self._param, payload)
        if self._benign_cursor >= len(self._benign_requests):
            return None
        request = self._benign_requests[self._benign_cursor]
        self._benign_cursor += 1
        endpoint = ENDPOINT_BY_PATH.get(request["path"], "search")
        param = PARAM_BY_ENDPOINT[endpoint]
        value = str(next(iter(request["params"].values())))
        return (endpoint, param, Payload(value, "query", 0))

    def step(self, action: int):
        endpoint, param, payload = self._pending
        result = self._backend.probe(payload, endpoint, param)
        gt_effect = bool(result.oracle.effect) and self._is_attack
        reward = self._reward_for(Action(action), gt_effect)
        self._tracker.record(
            RequestInput(params={param: payload.text}),
            modsec_pl2=result.modsec_scores[2] / 50,
            allowed=action == 0,
        )
        self._last_response = 3 if action != 0 else (1 if gt_effect else 2)
        self._result = result
        self._step_index += 1
        terminated = self._is_terminal(Action(action))
        self._pending = None if terminated else self._next_request()
        if self._pending is None:
            terminated = True
        truncated = self._step_index >= MAX_SESSION_STEPS
        return self._obs_or_zeros(), reward, terminated, truncated, self._info(gt_effect)

    def _reward_for(self, action: Action, gt_effect: bool) -> float:
        a, b, g = self._reward["alpha"], self._reward["beta"], self._reward["gamma"]
        if not self._is_attack:
            return {
                Action.ALLOW: 0.0,
                Action.BLOCK: -a,
                Action.CAPTCHA: -b,
                Action.RATE_LIMIT: -g,
                Action.HONEYPOT: -a,
            }[action]
        allow = -10.0 if gt_effect else 0.0
        return {
            Action.ALLOW: allow,
            Action.BLOCK: 5.0,
            Action.CAPTCHA: 3.0,
            Action.RATE_LIMIT: 2.0,
            Action.HONEYPOT: 6.0,
        }[action]

    def _is_terminal(self, action: Action) -> bool:
        if action == Action.HONEYPOT:
            return True
        if not self._is_attack and action != Action.ALLOW:
            if self.np_random.random() < self._abandon_prob:
                return True
        return False

    def _obs(self) -> np.ndarray:
        endpoint, param, payload = self._pending
        result = self._backend.probe(payload, endpoint, param)
        obs = np.zeros(OBS_SIZE, dtype=np.float32)
        obs[:12] = request_features(RequestInput(params={param: payload.text}))
        obs[12:16] = modsec_features(result.modsec_scores)
        obs[16:21] = self._tracker.session_features()
        obs[21:37] = self._tracker.window_features()
        return np.clip(obs, 0.0, 1.0)

    def _obs_or_zeros(self) -> np.ndarray:
        return self._obs() if self._pending is not None else np.zeros(OBS_SIZE, dtype=np.float32)

    def _info(self, gt_effect=False) -> dict:
        info = {
            "session_id": self._session_id,
            "request_index": self._step_index,
            "modsec_would_block": [
                bool(getattr(self, "_result", None) and self._result.modsec_block[pl])
                for pl in (1, 2, 3, 4)
            ]
            if hasattr(self, "_result")
            else [False, False, False, False],
            "gt_label": "attack" if self._is_attack else "benign",
            "gt_effect": gt_effect,
            "gt_hard_tags": [],
        }
        return info


def _find(items, matches, name):
    for item in items:
        if matches(item):
            return item
    raise ValueError(f"{name!r} is not in the environment's split")


def _load_benign_sessions(split: str) -> list[dict]:
    allowed = set(json.loads(SPLITS_PATH.read_text())["benign"][split])
    path = Path("data/benign/sessions.jsonl")
    return [
        s
        for s in (json.loads(line) for line in path.read_text().splitlines())
        if s["session_id"] in allowed
    ]
