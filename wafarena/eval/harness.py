"""Fixed evaluation suites (metricas.md, Suites de evaluación).

The same seeds produce the same base payloads, so every agent is judged on the same episodes.
"""

from dataclasses import dataclass

from wafarena.agents.base import Agent, strip_ground_truth
from wafarena.envs.attacker_env import SEND_ACTION, AttackerEnv
from wafarena.envs.backends.base import Backend
from wafarena.envs.resolve import resolve_backend, resolve_defender
from wafarena.eval.metrics import EpisodeResult


@dataclass(frozen=True)
class AttackerSuite:
    name: str
    split: str
    seeds: range
    query_budget: int


EVAL_SEEDS = range(1000, 1200)
ATTACKER_SUITES = {
    "attacker-eval-v1": AttackerSuite("attacker-eval-v1", "test", EVAL_SEEDS, 50),
    "attacker-eval-family-v1": AttackerSuite(
        "attacker-eval-family-v1", "test-family", EVAL_SEEDS, 50
    ),
}


def run_attacker_suite(
    agent: Agent,
    suite: str,
    *,
    defender=None,
    backend: Backend | str = "fast",
) -> list[EpisodeResult]:
    """Play the suite's episodes greedily (`explore=False`) and return one result per seed.

    The agent only sees `info` without `gt_*` keys and is never updated here.
    """
    if agent.role != "attacker":
        raise ValueError(f"attacker suites need an attacker agent, got role {agent.role!r}")
    spec = ATTACKER_SUITES[suite]
    env = AttackerEnv(
        backend=resolve_backend(backend),
        defender=resolve_defender(defender),
        split=spec.split,
        query_budget=spec.query_budget,
    )
    return [_play_episode(agent, env, seed) for seed in spec.seeds]


def _play_episode(agent: Agent, env: AttackerEnv, seed: int) -> EpisodeResult:
    obs, info = env.reset(seed=seed)
    base_id, family = info["base_id"], info["family"]
    attempts = broken = 0
    done = False
    while not done:
        action = int(agent.act(obs, strip_ground_truth(info), explore=False))
        obs, _reward, terminated, truncated, info = env.step(action)
        if action != SEND_ACTION:
            attempts += 1
            broken += int(info["broken"])
        done = terminated or truncated
    return EpisodeResult(
        seed=seed,
        base_id=base_id,
        family=family,
        evaded=bool(info["evaded"]),
        banned=bool(info["banned"]),
        queries_used=int(info["queries_used"]),
        mutation_attempts=attempts,
        broken=broken,
        payload=info["payload"],
    )
