"""Agent interface, checkpoints and the ground-truth firewall (agentes-y-checkpoints.md)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

import numpy as np
import yaml

import wafarena

GT_PREFIX = "gt_"
META_FILE = "meta.yaml"

# Names used in `meta.yaml: contract_versions` → keys of `wafarena.CONTRACT_VERSIONS`.
META_CONTRACT_KEYS = {
    "env_attacker": "env-atacante",
    "env_defender": "env-defensor",
    "oracle": "oraculo",
    "operators": "operadores-mutacion",
    "features": "features",
    "data": "datos-y-splits",
    "agents": "agentes-y-checkpoints",
}
ROLE_CONTRACTS = {
    "attacker": ("env_attacker", "operators", "features"),
    "defender": ("env_defender", "features"),
}


class ContractVersionError(Exception):
    """A checkpoint was trained against an incompatible (different MAJOR) contract version."""


@dataclass
class Transition:
    obs: np.ndarray
    action: int
    reward: float
    next_obs: np.ndarray
    terminated: bool
    truncated: bool
    info: Mapping[str, Any]  # info after the step (the one of next_obs); never carries gt_ keys


class Agent(Protocol):
    agent_id: str
    role: Literal["attacker", "defender"]

    def act(self, obs: np.ndarray, info: Mapping[str, Any], *, explore: bool) -> int: ...
    def observe(self, t: Transition) -> dict[str, float]: ...
    def save(self, path: Path) -> None: ...
    @classmethod
    def load(cls, path: Path) -> "Agent": ...


def strip_ground_truth(info: Mapping[str, Any]) -> dict[str, Any]:
    """Copy of `info` without the evaluation-only `gt_*` keys."""
    return {key: value for key, value in info.items() if not key.startswith(GT_PREFIX)}


_AGENT_CLASSES: dict[str, type] = {}


def register_agent(algo: str) -> Callable[[type], type]:
    """Class decorator: make `load_checkpoint` able to rebuild agents whose meta says `algo`."""

    def decorator(cls: type) -> type:
        _AGENT_CLASSES[algo] = cls
        return cls

    return decorator


def build_agent(
    algo: str,
    params: Mapping[str, Any],
    *,
    obs_dim: int,
    n_actions: int,
    seed: int,
    agent_id: str,
) -> Agent:
    """Instantiate the registered agent class for `algo` from experiment-config parameters."""
    try:
        cls = _AGENT_CLASSES[algo]
    except KeyError:
        raise KeyError(f"no agent registered for algo {algo!r}") from None
    return cls.from_config(
        params=params, obs_dim=obs_dim, n_actions=n_actions, seed=seed, agent_id=agent_id
    )


def current_contract_versions(role: str) -> dict[str, str]:
    return {
        name: wafarena.CONTRACT_VERSIONS[META_CONTRACT_KEYS[name]] for name in ROLE_CONTRACTS[role]
    }


def save_checkpoint(
    agent: Agent,
    path: Path,
    *,
    algo: str,
    obs_dim: int,
    n_actions: int,
    train: Mapping[str, Any] | None = None,
    eval_summary: Mapping[str, Any] | None = None,
) -> None:
    """Write `meta.yaml` plus the agent's weights into the directory `path`."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    meta = {
        "agent_id": agent.agent_id,
        "role": agent.role,
        "algo": algo,
        "obs_dim": obs_dim,
        "n_actions": n_actions,
        "contract_versions": current_contract_versions(agent.role),
        "train": dict(train or {}),
        "eval_summary": dict(eval_summary or {}),
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (path / META_FILE).write_text(yaml.safe_dump(meta, sort_keys=False))
    agent.save(path)


def _major(version: str) -> int:
    return int(str(version).split(".")[0])


def check_contract_versions(saved: Mapping[str, str]) -> None:
    for name, version in saved.items():
        if name not in META_CONTRACT_KEYS:
            raise ContractVersionError(f"unknown contract {name!r} in checkpoint meta")
        current = wafarena.CONTRACT_VERSIONS[META_CONTRACT_KEYS[name]]
        if _major(version) != _major(current):
            raise ContractVersionError(
                f"checkpoint trained with {name} {version}, code implements {current} "
                "(different MAJOR version)"
            )


def load_checkpoint(path: Path) -> Agent:
    """Rebuild the agent saved in `path`, after checking its contract versions."""
    path = Path(path)
    meta = yaml.safe_load((path / META_FILE).read_text())
    check_contract_versions(meta["contract_versions"])
    try:
        cls = _AGENT_CLASSES[meta["algo"]]
    except KeyError:
        raise KeyError(f"no agent registered for algo {meta['algo']!r}") from None
    return cls.load(path)
