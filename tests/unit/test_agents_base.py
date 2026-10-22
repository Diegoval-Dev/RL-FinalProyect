"""F2-T02: Agent interface, checkpoints and the ground-truth firewall (agentes-y-checkpoints.md)."""

import ast
from pathlib import Path

import numpy as np
import pytest
import yaml

import wafarena
from wafarena.agents import (
    ContractVersionError,
    Transition,
    load_checkpoint,
    register_agent,
    save_checkpoint,
    strip_ground_truth,
)

AGENTS_DIR = Path(wafarena.__file__).parent / "agents"


@register_agent("test-table")
class TableAgent:
    """Minimal tabular agent used only to exercise the checkpoint round trip."""

    def __init__(self, agent_id: str, n_states: int = 4, n_actions: int = 3):
        self.agent_id = agent_id
        self.role = "attacker"
        self.q = np.zeros((n_states, n_actions))

    def act(self, obs, info, *, explore):
        return int(np.argmax(self.q[int(info["abstract_state"])]))

    def observe(self, t: Transition) -> dict[str, float]:
        self.q[int(t.info["abstract_state"]), t.action] += t.reward
        return {"td_error": float(t.reward)}

    def save(self, path: Path) -> None:
        np.save(path / "q_table.npy", self.q)

    @classmethod
    def load(cls, path: Path) -> "TableAgent":
        meta = yaml.safe_load((path / "meta.yaml").read_text())
        q = np.load(path / "q_table.npy")
        agent = cls(meta["agent_id"], *q.shape)
        agent.q = q
        return agent


def trained_agent() -> TableAgent:
    agent = TableAgent("ATK-TEST")
    agent.q[2, 1] = 5.0
    return agent


def save(agent, path: Path, **overrides) -> None:
    save_checkpoint(agent, path, algo="test-table", obs_dim=288, n_actions=3, **overrides)


def test_checkpoint_round_trip_restores_weights_and_behaviour(tmp_path):
    agent = trained_agent()
    save(agent, tmp_path / "ck")
    loaded = load_checkpoint(tmp_path / "ck")
    assert isinstance(loaded, TableAgent)
    assert loaded.agent_id == "ATK-TEST"
    assert np.array_equal(loaded.q, agent.q)
    assert loaded.act(np.zeros(288), {"abstract_state": 2}, explore=False) == 1


def test_checkpoint_meta_follows_the_contract(tmp_path):
    save(trained_agent(), tmp_path / "ck", train={"exp_id": "EXP-D1", "seed": 3})
    meta = yaml.safe_load((tmp_path / "ck" / "meta.yaml").read_text())
    assert {"agent_id", "role", "algo", "obs_dim", "n_actions"} <= meta.keys()
    assert meta["algo"] == "test-table" and meta["role"] == "attacker"
    assert meta["train"] == {"exp_id": "EXP-D1", "seed": 3}
    assert meta["contract_versions"]["env_attacker"] == wafarena.CONTRACT_VERSIONS["env-atacante"]
    assert "created_at" in meta


def _rewrite_versions(path: Path, **versions: str) -> None:
    meta_path = path / "meta.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["contract_versions"].update(versions)
    meta_path.write_text(yaml.safe_dump(meta))


def test_load_checkpoint_rejects_different_major_version(tmp_path):
    save(trained_agent(), tmp_path / "ck")
    _rewrite_versions(tmp_path / "ck", env_attacker="2.0")
    with pytest.raises(ContractVersionError, match="env_attacker"):
        load_checkpoint(tmp_path / "ck")


def test_load_checkpoint_accepts_different_minor_version(tmp_path):
    save(trained_agent(), tmp_path / "ck")
    _rewrite_versions(tmp_path / "ck", features="1.7")
    assert isinstance(load_checkpoint(tmp_path / "ck"), TableAgent)


def test_load_checkpoint_rejects_unknown_contract_name(tmp_path):
    save(trained_agent(), tmp_path / "ck")
    _rewrite_versions(tmp_path / "ck", made_up="1.0")
    with pytest.raises(ContractVersionError, match="made_up"):
        load_checkpoint(tmp_path / "ck")


def test_load_checkpoint_rejects_unregistered_algo(tmp_path):
    save(trained_agent(), tmp_path / "ck")
    meta_path = tmp_path / "ck" / "meta.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["algo"] = "no-such-algo"
    meta_path.write_text(yaml.safe_dump(meta))
    with pytest.raises(KeyError, match="no-such-algo"):
        load_checkpoint(tmp_path / "ck")


def test_strip_ground_truth_removes_only_gt_keys():
    info = {"abstract_state": 7, "payload": "x", "gt_oracle": {"a": 1}, "gt_defender_action": 4}
    clean = strip_ground_truth(info)
    assert clean == {"abstract_state": 7, "payload": "x"}
    assert "gt_oracle" in info  # the input is not mutated


def gt_accesses(source: str) -> list[str]:
    """String literals naming a `gt_*` key (the bare prefix constant is allowed)."""
    return [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.startswith("gt_")
        and node.value != "gt_"
    ]


def test_gt_scanner_detects_ground_truth_access():
    assert gt_accesses('x = info["gt_oracle"]') == ["gt_oracle"]
    assert gt_accesses('x = info.get("gt_defender_action")') == ["gt_defender_action"]
    assert gt_accesses('GT_PREFIX = "gt_"') == []


def test_agents_package_never_reads_ground_truth_keys():
    offenders = {
        path.name: found
        for path in AGENTS_DIR.rglob("*.py")
        if (found := gt_accesses(path.read_text()))
    }
    assert offenders == {}
