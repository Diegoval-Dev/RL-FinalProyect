"""Defender proxy: assigns X-Request-ID, scores the request with ModSecurity PL1-4, builds the
observation, asks a DefenderPolicy for an action and applies it.

Actions (env-defensor.md): ALLOW forwards to vulnapp, BLOCK -> 403, CAPTCHA -> 403 challenge,
RATE_LIMIT -> 429, HONEYPOT -> forwards to the honeypot.
"""

import os
import uuid
from collections.abc import Callable

import httpx
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from wafarena.defenders.base import Action, DefenderPolicy
from wafarena.defenders.modsec import modsec_score
from wafarena.features.modsec import PARANOIA_LEVELS, modsec_features
from wafarena.features.request import REQUEST_FEATURE_NAMES, RequestInput, request_features

VULNAPP_URL = os.environ.get("VULNAPP_URL", "http://vulnapp:8000")
HONEYPOT_URL = os.environ.get("HONEYPOT_URL", "http://honeypot:8000")
REQUEST_ID_HEADER = "X-Request-ID"
OBS_SIZE = 37
SESSION_BLOCK = slice(16, 37)


def build_observation(params: dict, body_is_json: bool, scores: dict[int, int]) -> np.ndarray:
    obs = np.zeros(OBS_SIZE, dtype=np.float32)
    obs[: len(REQUEST_FEATURE_NAMES)] = request_features(
        RequestInput(params=params, body_is_json=body_is_json)
    )
    obs[12:16] = modsec_features(scores)
    return obs


def forward(url: str, method: str, path: str, params: dict, request_id: str) -> httpx.Response:
    headers = {REQUEST_ID_HEADER: request_id}
    return httpx.request(method, f"{url}{path}", params=params, headers=headers, timeout=10)


def create_app(policy: DefenderPolicy, score_fn: Callable = modsec_score) -> FastAPI:
    app = FastAPI(title="proxy", docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    async def handle(path: str, request: Request) -> JSONResponse:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        params = dict(request.query_params)
        full_path = "/" + path
        scores = {
            pl: score_fn(request.method, f"{full_path}?{request.url.query}", pl).score
            for pl in PARANOIA_LEVELS
        }
        obs = build_observation(params, body_is_json=False, scores=scores)
        action = Action(policy.act(obs))
        return _apply(action, request.method, full_path, params, request_id)

    def _apply(action, method, path, params, request_id) -> JSONResponse:
        if action == Action.BLOCK:
            return JSONResponse({"blocked": True}, status_code=403)
        if action == Action.CAPTCHA:
            return JSONResponse({"captcha": True}, status_code=403)
        if action == Action.RATE_LIMIT:
            return JSONResponse({"rate_limited": True}, status_code=429)
        target = HONEYPOT_URL if action == Action.HONEYPOT else VULNAPP_URL
        response = forward(target, method, path, params, request_id)
        return JSONResponse(_safe_json(response), status_code=response.status_code)

    def _safe_json(response: httpx.Response) -> dict:
        try:
            return response.json()
        except ValueError:
            return {"body": response.text}

    return app
