"""Deterministic benign-session generator.

Produces realistic benign sessions against vulnapp's endpoints, with `normal` and `hard` templates.
Hard sessions carry values tagged by the difficulty they introduce (apostrophe, symbols, code,
spanish, emoji). The oracle must report effect=False for every request (verified in the builder).

A deterministic generator stands in for Locust/Playwright so the corpus is reproducible and runs in
CI; the HTTP-replay path (real mode) can drive these same sessions through the proxy later.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy as np

HARD_TAGS = ("apostrophe", "symbols", "code", "spanish", "emoji")

NORMAL_VALUES = {
    "catalog": {"category": ["Libros", "Electrónica", "Hogar", "Ropa"]},
    "search": {"q": ["lap", "cafe", "camisa", "teclado", "gorra"]},
    "product": {"id": ["1", "2", "3", "4", "7"]},
    "login": {"username": ["ana", "luis", "maria"], "password": ["ana2024", "luis2024"]},
    "orders": {"user_id": ["2", "3", "4"]},
}

HARD_VALUES = {
    "apostrophe": ["O'Brien", "D'Angelo", "l'Hôpital"],
    "symbols": ["50% off!", "a+b=c", "(tienda)", "#oferta", "<etiqueta>"],
    "code": ["SELECT me", "drop beat", "union jack", "order now"],
    "spanish": ["mañana", "camión", "niño", "corazón", "pingüino"],
    "emoji": ["café ☕", "libro 📚", "oferta 🔥", "envío 🚚"],
}

READ_ENDPOINTS = ("catalog", "search", "product", "orders")
TEMPLATE_PATHS = {
    "catalog": "/catalog",
    "search": "/search",
    "product": "/product",
    "login": "/login",
    "orders": "/orders",
}


@dataclass(frozen=True)
class SessionRequest:
    t: float
    method: str
    path: str
    params: dict
    body: dict | None
    content_type: str | None
    hard_tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Session:
    session_id: str
    kind: str
    template_id: str
    generator: str
    requests: list[SessionRequest]


def _pick(rng: np.random.Generator, values: list[str]) -> str:
    return values[int(rng.integers(len(values)))]


def _normal_request(rng: np.random.Generator, endpoint: str, t: float) -> SessionRequest:
    params = {p: _pick(rng, options) for p, options in NORMAL_VALUES[endpoint].items()}
    return SessionRequest(t, "GET", TEMPLATE_PATHS[endpoint], params, None, None, [])


def _hard_request(rng: np.random.Generator, tag: str, t: float) -> SessionRequest:
    value = _pick(rng, HARD_VALUES[tag])
    return SessionRequest(t, "GET", "/search", {"q": value}, None, None, [tag])


def generate(n_normal: int, n_hard: int, seed: int = 0) -> Iterator[Session]:
    rng = np.random.default_rng(seed)
    counter = 0
    for _ in range(n_normal):
        length = 1 + int(rng.integers(5))
        requests = [
            _normal_request(rng, _pick(rng, list(READ_ENDPOINTS)), float(step))
            for step in range(length)
        ]
        yield Session(f"b-{counter:06d}", "normal", "t-normal-browse", "generator", requests)
        counter += 1
    for i in range(n_hard):
        tag = HARD_TAGS[i % len(HARD_TAGS)]
        length = 1 + int(rng.integers(3))
        requests = [_hard_request(rng, tag, float(step)) for step in range(length)]
        yield Session(f"b-{counter:06d}", "hard", f"t-hard-{tag}", "generator", requests)
        counter += 1
