"""Fixed evaluation suites (metricas.md, Suites de evaluación).

The same seeds produce the same base payloads, so every agent is judged on the same episodes.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from wafarena.agents.base import Agent, strip_ground_truth
from wafarena.envs.attacker_env import SEND_ACTION, AttackerEnv
from wafarena.envs.backends.base import Backend
from wafarena.envs.defender_env import DefenderEnv
from wafarena.envs.resolve import resolve_backend, resolve_defender
from wafarena.eval import metrics
from wafarena.eval.metrics import EpisodeResult, RequestRecord
from wafarena.splits.builder import SPLITS_PATH


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
# Model selection runs on `val`; these suites are never part of the reported evaluation.
VALIDATION_SUITES = {
    "attacker-val-v1": AttackerSuite("attacker-val-v1", "val", range(2000, 2200), 50),
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
    spec = {**ATTACKER_SUITES, **VALIDATION_SUITES}[suite]
    env = AttackerEnv(
        backend=resolve_backend(backend),
        defender=resolve_defender(defender),
        split=spec.split,
        query_budget=spec.query_budget,
    )
    return [_play_episode(agent, env, seed) for seed in spec.seeds]


def summarize_attacker(results: list[EpisodeResult], *, query_budget: int) -> dict[str, float]:
    """All attacker metrics of metricas.md for one suite run."""
    winners = [r.payload for r in results if r.evaded]
    return {
        "episodes": len(results),
        "evasions": sum(r.evaded for r in results),
        "evasion_rate": metrics.evasion_rate(results),
        "qfe": metrics.queries_to_first_evasion(results),
        "qfe_c": metrics.censored_queries(results, query_budget),
        "diversity": metrics.diversity(winners),
        "uniqueness": metrics.uniqueness(winners),
        "break_rate": metrics.break_rate(results),
    }


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


@dataclass(frozen=True)
class SessionPlan:
    """One session of a defender suite: which attack payload or benign session, and the env seed."""

    is_attack: bool
    ref: str  # payload base_id (attack) or session_id (benign)
    seed: int


@dataclass(frozen=True)
class DefenderSuite:
    name: str
    benign_split: str
    attack_split: str
    attackers: tuple[str, ...]
    n_sessions: int = 2000
    attack_ratio: float = 0.1
    all_benign: bool = False  # use every session of `benign_split` once instead of sampling
    attacks_like: str | None = None  # reuse the attack sessions of another suite


PLAN_SEEDS = {"benign": 2000, "attack": 2001, "order": 2002}
ENV_SEED_BASE = 5000
SCRIPTED_ATTACKERS = ("corpus-replay", "random-mutation")
REFS_DIR = Path("checkpoints/refs")
DEFENDER_SUITES = {
    "defender-eval-v1": DefenderSuite(
        "defender-eval-v1", "test", "test", (*SCRIPTED_ATTACKERS, "ATK-REF-0")
    ),
    "defender-eval-hard-v1": DefenderSuite(
        "defender-eval-hard-v1",
        "test-hard",
        "test",
        SCRIPTED_ATTACKERS,
        all_benign=True,
        attacks_like="defender-eval-v1",
    ),
    "defender-eval-family-v1": DefenderSuite(
        "defender-eval-family-v1", "test", "test-family", SCRIPTED_ATTACKERS
    ),
}
# Model selection for defenders; like attacker-val-v1, never part of the reported evaluation.
DEFENDER_VALIDATION_SUITES = {
    "defender-val-v1": DefenderSuite(
        "defender-val-v1", "val", "val", (*SCRIPTED_ATTACKERS, "ATK-REF-0")
    ),
}
PER_ATTACKER_METRICS = ("tpr", "er_d", "f1")


def _split_ids(kind: str, split: str) -> list[str]:
    return sorted(json.loads(SPLITS_PATH.read_text())[kind][split])


def _sample(ids: list[str], n: int, seed: int) -> list[str]:
    rng = np.random.default_rng(seed)
    return [ids[i] for i in rng.integers(len(ids), size=n)]


def _defender_suite(name: str) -> DefenderSuite:
    return {**DEFENDER_SUITES, **DEFENDER_VALIDATION_SUITES}[name]


def _attack_refs(spec: DefenderSuite) -> list[str]:
    source = _defender_suite(spec.attacks_like) if spec.attacks_like else spec
    n_attacks = round(source.n_sessions * source.attack_ratio)
    return _sample(_split_ids("payloads", source.attack_split), n_attacks, PLAN_SEEDS["attack"])


def _benign_refs(spec: DefenderSuite) -> list[str]:
    ids = _split_ids("benign", spec.benign_split)
    if spec.all_benign:
        return ids
    n_benign = spec.n_sessions - round(spec.n_sessions * spec.attack_ratio)
    return _sample(ids, n_benign, PLAN_SEEDS["benign"])


def build_session_plan(spec: DefenderSuite) -> list[SessionPlan]:
    """Deterministic, shuffled list of the suite's sessions; identical for every defender."""
    entries = [(True, ref) for ref in _attack_refs(spec)]
    entries += [(False, ref) for ref in _benign_refs(spec)]
    order = np.random.default_rng(PLAN_SEEDS["order"]).permutation(len(entries))
    return [
        SessionPlan(entries[i][0], entries[i][1], ENV_SEED_BASE + position)
        for position, i in enumerate(order)
    ]


def run_defender_suite(
    defender,
    suite: str,
    *,
    attacker: str,
    backend: Backend | str = "fast",
) -> list[RequestRecord]:
    """Play every session of the suite against one scripted attacker; one record per request.

    `defender` is an `Agent` (role "defender") or a `DefenderPolicy`. Agents only see `info`
    without `gt_*` keys and are never updated here.
    """
    if hasattr(defender, "role") and defender.role != "defender":
        raise ValueError(f"defender suites need a defender, got role {defender.role!r}")
    spec = _defender_suite(suite)
    if attacker not in spec.attackers:
        raise ValueError(f"suite {suite} does not include attacker {attacker!r}")
    attacker_arg = (
        attacker.replace("-", "_")
        if attacker in SCRIPTED_ATTACKERS
        else {"type": "checkpoint", "path": str(REFS_DIR / attacker)}
    )
    env = DefenderEnv(
        backend=resolve_backend(backend),
        attacker=attacker_arg,
        split=spec.benign_split,
        attack_split=spec.attack_split,
    )
    records: list[RequestRecord] = []
    for item in build_session_plan(spec):
        records.extend(_play_session(defender, env, item))
    return records


def _play_session(defender, env: DefenderEnv, item: SessionPlan) -> list[RequestRecord]:
    options = {"base_id": item.ref} if item.is_attack else {"session_id": item.ref}
    obs, info = env.reset(seed=item.seed, options=options)
    is_policy = hasattr(defender, "reset_session")
    if is_policy:
        defender.reset_session(info["session_id"])
    records, done = [], False
    while not done:
        if is_policy:
            action = int(defender.act(obs))
        else:
            action = int(defender.act(obs, strip_ground_truth(info), explore=False))
        obs, _reward, terminated, truncated, info = env.step(action)
        records.append(
            RequestRecord(
                is_attack=info["gt_label"] == "attack",
                action=action,
                effect=bool(info["gt_effect"]),
                session_id=info["session_id"],
            )
        )
        done = terminated or truncated
    return records


def summarize_defender(records: list[RequestRecord]) -> dict[str, float]:
    """All per-request and per-session defender metrics of metricas.md for one set of records."""
    return {
        "requests": len(records),
        "attack_requests": sum(r.is_attack for r in records),
        "tpr": metrics.tpr(records),
        "er_d": metrics.evasion_suffered(records),
        "fpr": metrics.fpr(records),
        "fpr_h": metrics.fpr_hard(records),
        "fpr_s": metrics.fpr_by_session(records),
        "fpr_h_s": metrics.fpr_hard_by_session(records),
        "f1": metrics.f1(records),
    }


def evaluate_defender(defender, suite: str, *, backend: Backend | str = "fast") -> dict:
    """Play the suite against each of its attackers; metrics over the pooled requests, plus
    `<metric>@<attacker>` for the attack-side metrics of each attacker alone.

    Every attacker meets the same benign sessions, so pooling repeats them once per attacker:
    FPR is unchanged by that, and TPR stays a per-request rate over every attack request."""
    backend = resolve_backend(backend)
    pooled: list[RequestRecord] = []
    per_attacker: dict[str, float] = {}
    for attacker in _defender_suite(suite).attackers:
        records = run_defender_suite(defender, suite, attacker=attacker, backend=backend)
        pooled.extend(records)
        alone = summarize_defender(records)
        per_attacker.update({f"{m}@{attacker}": alone[m] for m in PER_ATTACKER_METRICS})
    return {**summarize_defender(pooled), **per_attacker}
