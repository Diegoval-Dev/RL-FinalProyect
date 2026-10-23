"""F2-T03: the training loop (experimentos.md, Salida: train.csv)."""

import csv
from pathlib import Path

import numpy as np
import pytest

from wafarena.agents import Transition, build_agent, register_agent
from wafarena.envs.attacker_env import N_ACTIONS, AttackerEnv
from wafarena.envs.backends.fake import FakeBackend
from wafarena.trainer import train


@register_agent("toy-random")
class ToyRandomAgent:
    """Picks random actions and records everything the loop hands it."""

    role = "attacker"

    def __init__(self, agent_id: str, seed: int):
        self.agent_id = agent_id
        self._rng = np.random.default_rng(seed)
        self.act_infos: list[dict] = []
        self.transitions: list[Transition] = []

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id):
        return cls(agent_id, seed)

    def act(self, obs, info, *, explore):
        assert explore is True
        self.act_infos.append(dict(info))
        return int(self._rng.integers(N_ACTIONS))

    def observe(self, t):
        self.transitions.append(t)
        return {"seen": float(len(self.transitions))}

    def save(self, path: Path) -> None: ...

    @classmethod
    def load(cls, path: Path):
        raise NotImplementedError


def make_env() -> AttackerEnv:
    return AttackerEnv(backend=FakeBackend(), split="train", query_budget=10, max_steps=30)


def make_agent(seed: int = 0) -> ToyRandomAgent:
    return build_agent("toy-random", {}, obs_dim=288, n_actions=N_ACTIONS, seed=seed, agent_id="t")


def read_rows(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def run(tmp_path: Path, total_steps=200, seed=0, eval_every=50, on_eval=None):
    agent = make_agent(seed)
    train(
        agent,
        make_env(),
        total_steps=total_steps,
        seed=seed,
        out_dir=tmp_path,
        eval_every=eval_every,
        on_eval=on_eval,
        tensorboard=False,
    )
    return agent


def test_build_agent_rejects_unknown_algo():
    with pytest.raises(KeyError, match="no-such-algo"):
        build_agent("no-such-algo", {}, obs_dim=1, n_actions=1, seed=0, agent_id="x")


def test_loop_takes_exactly_total_steps(tmp_path):
    agent = run(tmp_path, total_steps=137)
    assert len(agent.transitions) == 137 and len(agent.act_infos) == 137


def test_agent_never_sees_ground_truth_keys(tmp_path):
    agent = run(tmp_path)
    keys = {k for info in agent.act_infos for k in info} | {
        k for t in agent.transitions for k in t.info
    }
    assert "abstract_state" in keys
    assert not any(k.startswith("gt_") for k in keys)


def test_transitions_chain_within_an_episode(tmp_path):
    agent = run(tmp_path, total_steps=120)
    ts = agent.transitions
    for current, following in zip(ts, ts[1:], strict=False):
        if not (current.terminated or current.truncated):
            assert np.array_equal(current.next_obs, following.obs)


def test_train_csv_logs_one_row_per_episode_with_attacker_stats(tmp_path):
    run(tmp_path, total_steps=300)
    rows = read_rows(tmp_path / "train.csv")
    assert rows and {"step", "episode", "return", "length", "evaded", "broken", "complete"} <= set(
        rows[0]
    )
    completed = [r for r in rows if r["complete"] == "1"]
    assert [int(r["episode"]) for r in rows] == list(range(len(rows)))
    assert sum(int(r["length"]) for r in rows) == 300
    assert all(int(r["broken"]) <= int(r["mutation_attempts"]) for r in completed)
    assert "m_seen" in rows[0]  # agent training metrics are averaged per episode


def test_final_partial_episode_is_flagged_incomplete(tmp_path):
    run(tmp_path, total_steps=7)
    rows = read_rows(tmp_path / "train.csv")
    assert rows[-1]["complete"] == "0"


def test_training_is_deterministic_given_seed(tmp_path):
    run(tmp_path / "a", seed=5)
    run(tmp_path / "b", seed=5)
    assert (tmp_path / "a" / "train.csv").read_text() == (tmp_path / "b" / "train.csv").read_text()
    run(tmp_path / "c", seed=6)
    assert (tmp_path / "a" / "train.csv").read_text() != (tmp_path / "c" / "train.csv").read_text()


def test_on_eval_fires_every_eval_interval_and_at_the_end(tmp_path):
    steps = []
    run(tmp_path, total_steps=120, eval_every=50, on_eval=steps.append)
    assert steps == [50, 100, 120]


def test_tensorboard_writes_event_files(tmp_path):
    train(
        make_agent(),
        make_env(),
        total_steps=60,
        seed=0,
        out_dir=tmp_path,
        eval_every=30,
        on_eval=None,
        tensorboard=True,
    )
    assert list((tmp_path / "tb").glob("events.out.tfevents.*"))
