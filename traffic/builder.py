"""Writes data/benign/sessions.jsonl and verifies the oracle reports effect=False everywhere.

Runs in the lab runner. Verifies every distinct (endpoint, param, value) once through the oracle so
a benign value that accidentally injected would fail the build.
"""

import json
from dataclasses import asdict
from pathlib import Path

from traffic.generator import Session, generate
from vulnapp.queries import get_endpoint
from wafarena.mutations.payload import Payload
from wafarena.oracle import Oracle

SESSIONS_PATH = Path("data/benign/sessions.jsonl")
N_NORMAL = 4000
N_HARD = 1200
SEED = 0
ENDPOINT_BY_PATH = {
    "/catalog": ("catalog", "category"),
    "/search": ("search", "q"),
    "/product": ("product", "id"),
    "/orders": ("orders", "user_id"),
    "/login": ("login", "username"),
}


def distinct_values(sessions: list[Session]) -> set[tuple[str, str, str]]:
    values = set()
    for session in sessions:
        for request in session.requests:
            endpoint, param = ENDPOINT_BY_PATH[request.path]
            values.add((endpoint, param, str(request.params[param])))
    return values


def verify_no_effect(oracle: Oracle, values: set[tuple[str, str, str]]) -> None:
    for endpoint, param, value in values:
        spec = get_endpoint(endpoint)
        result = oracle.check_direct(Payload(value, spec.locations[0], 0), endpoint, param)
        if result.effect:
            raise ValueError(f"benign value has effect: {endpoint}.{param}={value!r}")


def write_sessions(sessions: list[Session], path: Path = SESSIONS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for session in sessions:
            handle.write(json.dumps(asdict(session), ensure_ascii=False) + "\n")


def main() -> None:
    sessions = list(generate(N_NORMAL, N_HARD, SEED))
    verify_no_effect(Oracle(), distinct_values(sessions))
    write_sessions(sessions)
    hard = sum(s.kind == "hard" for s in sessions)
    print(f"wrote {len(sessions)} sessions ({hard} hard) to {SESSIONS_PATH}")


if __name__ == "__main__":
    main()
