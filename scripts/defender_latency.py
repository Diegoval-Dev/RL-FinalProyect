"""Generates results/summary/latency.csv: LAT of a defender checkpoint in real mode (F3-T10).

LAT (metricas.md) is the time the defender proxy adds over ModSecurity alone. For each of
`--requests` requests (the requests of defender-eval-v1's sessions, benign and attack, in order),
the same request is sent (a) straight to ModSecurity at the reference paranoia level
(`modsec-pl2`, which forwards to vulnapp) and (b) through the defender proxy serving the checkpoint
(`proxy-learned`, which scores it with ModSecurity PL1-PL4, builds the 37 features, asks the policy
and applies the action), alternating which of the two goes first. The added time of each request
is (b) - (a). The CSV reports p50 and p95 of the added time, of (a), of (b) and of the policy
decision alone (the checkpoint's `act` on the same observations, timed in-process), so the share
of the proxy's own ModSecurity scoring and of the network can be told apart.

Runs inside the lab runner with the `proxy-learned` service up (`make latency`).
"""

import argparse
import csv
import time
from pathlib import Path

import httpx
import numpy as np

from vulnapp.queries import get_endpoint
from wafarena.agents import load_checkpoint
from wafarena.envs.backends.fake import FakeBackend
from wafarena.envs.defender_env import DefenderEnv
from wafarena.eval import harness, metrics

OUTPUT = Path("results/summary/latency.csv")
MODSEC_URL = "http://modsec-pl2:8080"
PROXY_URL = "http://proxy-learned:8000"
SUITE = "defender-eval-v1"
ATTACKERS = ("corpus_replay", "random_mutation")
WARMUP = 20


def request_sequence(n: int) -> list[tuple[str, dict]]:
    """(path, params) of the first `n` requests of the suite's sessions, in plan order. Only the
    request texts are needed, so the sessions are replayed offline (no backend calls)."""
    spec = harness.DEFENDER_SUITES[SUITE]
    plan = harness.build_session_plan(spec)
    requests: list[tuple[str, dict]] = []
    for attacker in ATTACKERS:
        env = DefenderEnv(
            FakeBackend(),
            attacker=attacker,
            split=spec.benign_split,
            attack_split=spec.attack_split,
        )
        for item in plan:
            options = {"base_id": item.ref} if item.is_attack else {"session_id": item.ref}
            env.reset(seed=item.seed, options=options)
            done = False
            while not done and len(requests) < n:
                endpoint, param, payload = env._pending  # the request the defender is shown
                requests.append((get_endpoint(endpoint).path, {param: payload.text}))
                *_, terminated, truncated, _ = env.step(0)
                done = terminated or truncated
            if len(requests) >= n:
                return requests
    return requests


def timed_get(client: httpx.Client, url: str, path: str, params: dict) -> float:
    started = time.perf_counter()
    client.get(f"{url}{path}", params=params)
    return (time.perf_counter() - started) * 1000.0


def policy_ms(checkpoint: Path, n: int) -> list[float]:
    """In-process time of the policy decision alone on Defender-v0 observations."""
    agent = load_checkpoint(checkpoint)
    rng = np.random.default_rng(0)
    observations = rng.random((n, 37)).astype(np.float32)
    out = []
    for obs in observations:
        started = time.perf_counter()
        agent.act(obs, {}, explore=False)
        out.append((time.perf_counter() - started) * 1000.0)
    return out


def row(name: str, values: list[float], n: int) -> dict:
    p50, p95 = metrics.latency_percentiles(values)
    return {"measure": name, "requests": n, "p50_ms": f"{p50:.3f}", "p95_ms": f"{p95:.3f}"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=Path("checkpoints/refs/DEF-REF-1"))
    parser.add_argument("--requests", type=int, default=2000)
    args = parser.parse_args()
    requests = request_sequence(args.requests + WARMUP)
    modsec, proxy = [], []
    with httpx.Client(timeout=30) as client:
        for i, (path, params) in enumerate(requests):
            if i % 2 == 0:
                a = timed_get(client, MODSEC_URL, path, params)
                b = timed_get(client, PROXY_URL, path, params)
            else:
                b = timed_get(client, PROXY_URL, path, params)
                a = timed_get(client, MODSEC_URL, path, params)
            if i >= WARMUP:
                modsec.append(a)
                proxy.append(b)
    added = [b - a for a, b in zip(modsec, proxy, strict=True)]
    n = len(added)
    rows = [
        row("lat_added", added, n),
        row("modsec_pl2_alone", modsec, n),
        row("proxy_with_defender", proxy, n),
        row("policy_decision", policy_ms(args.checkpoint, n), n),
    ]
    for r in rows:
        r["defender"] = str(args.checkpoint)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["defender", *[k for k in rows[0] if k != "defender"]]
        )
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(r)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
