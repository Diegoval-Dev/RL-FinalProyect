"""F2-T03: end-to-end experiment runs (experimentos.md, Salida)."""

import copy
import csv
import dataclasses
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import yaml

from wafarena import run as runner
from wafarena.agents import register_agent
from wafarena.envs.attacker_env import N_ACTIONS, SEND_ACTION
from wafarena.envs.backends.fake import FakeBackend
from wafarena.eval import harness
from wafarena.runconfig import ConfigError
from wafarena.runmeta import DirtyTreeError

N_STATES = 120
REPO = Path(__file__).parents[2]
EPISODES = 20  # suites are shortened here; their real definitions are tested in test_eval_harness


@pytest.fixture(autouse=True, scope="module")
def short_suites():
    patch = pytest.MonkeyPatch()
    for suites in (harness.ATTACKER_SUITES, harness.VALIDATION_SUITES):
        for name, suite in list(suites.items()):
            short = range(suite.seeds.start, suite.seeds.start + EPISODES)
            patch.setitem(suites, name, dataclasses.replace(suite, seeds=short))
    yield
    patch.undo()


@register_agent("toy-tabular")
class ToyTabularAgent:
    """Epsilon-greedy tabular Q-learning on the abstract state, to exercise the runner."""

    role = "attacker"

    def __init__(self, agent_id: str, seed: int, epsilon: float = 0.3, alpha: float = 0.5):
        self.agent_id = agent_id
        self.q = np.zeros((N_STATES, N_ACTIONS))
        self.q[:, SEND_ACTION] = 0.01  # greedy ties go to SEND so evaluation episodes end quickly
        self._rng = np.random.default_rng(seed)
        self._epsilon, self._alpha = epsilon, alpha
        self._state = 0

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id):
        return cls(agent_id, seed, **params)

    def act(self, obs, info, *, explore):
        self._state = info["abstract_state"]
        if explore and self._rng.random() < self._epsilon:
            return int(self._rng.integers(N_ACTIONS))
        return int(np.argmax(self.q[self._state]))

    def observe(self, t):
        target = t.reward + (0.0 if t.terminated else 0.9 * self.q[t.info["abstract_state"]].max())
        error = target - self.q[self._state, t.action]
        self.q[self._state, t.action] += self._alpha * error
        return {"td_error": float(error)}

    def save(self, path: Path) -> None:
        np.save(path / "q_table.npy", self.q)

    @classmethod
    def load(cls, path: Path):
        agent = cls(yaml.safe_load((path / "meta.yaml").read_text())["agent_id"], seed=0)
        agent.q = np.load(path / "q_table.npy")
        return agent


CONFIG = {
    "exp_id": "EXP-D1",
    "run_name": "toy",
    "seeds": [0, 1],
    "env": {"id": "WafArena/Attacker-v0", "query_budget": 10, "max_steps": 30},
    "agent": {"algo": "toy-tabular", "params": {"epsilon": 0.3}},
    "train": {"total_steps": 400},
    "eval": {"suites": ["attacker-eval-v1"], "every_steps": 200, "final": True},
    "logging": {"tensorboard": True},
}


def config(**changes):
    raw = copy.deepcopy(CONFIG)
    for key, value in changes.items():
        raw[key] = value
    return raw


def go(tmp_path: Path, raw=None, **kwargs):
    return runner.run_experiment(
        raw or config(),
        results_root=tmp_path,
        repo=REPO,
        allow_dirty=True,
        backend=FakeBackend(),
        **kwargs,
    )


def read_csv(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def finished(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("results")
    go(root)
    return root / "EXP-D1" / "toy" / "s0"


def test_run_produces_the_documented_output_tree(finished):
    for name in (
        "config.resolved.yaml",
        "meta.yaml",
        "train.csv",
        "eval.csv",
        "final_eval.json",
        "tb",
        "checkpoint",
    ):
        assert (finished / name).exists(), name
    assert (finished / "checkpoint" / "meta.yaml").exists()
    assert (finished.parent / "s1").is_dir()


def test_resolved_config_has_defaults_expanded(finished):
    resolved = yaml.safe_load((finished / "config.resolved.yaml").read_text())
    assert resolved["env"]["backend"] == "fast" and resolved["env"]["split"] == "train"


def test_meta_has_run_id_and_duration(finished):
    meta = yaml.safe_load((finished / "meta.yaml").read_text())
    assert meta["run_id"].startswith("EXP-D1__toy__s0__") and meta["duration_s"] >= 0


def test_eval_csv_evaluates_on_val_only_at_each_interval(finished):
    rows = read_csv(finished / "eval.csv")
    assert [int(r["step"]) for r in rows] == [200, 400]
    assert {r["suite"] for r in rows} == {"attacker-val-v1"}
    assert {"evasion_rate", "qfe_c", "break_rate"} <= set(rows[0])


def test_checkpoint_is_the_best_on_validation(finished):
    rows = read_csv(finished / "eval.csv")
    best = max(float(r["evasion_rate"]) for r in rows)
    meta = yaml.safe_load((finished / "checkpoint" / "meta.yaml").read_text())
    assert meta["eval_summary"]["suite"] == "attacker-val-v1"
    assert meta["eval_summary"]["evasion_rate"] == pytest.approx(best)
    assert meta["train"]["exp_id"] == "EXP-D1" and meta["train"]["seed"] == 0
    assert meta["train"]["run_id"].startswith("EXP-D1__toy__s0__")
    assert meta["algo"] == "toy-tabular" and meta["n_actions"] == N_ACTIONS


def test_final_eval_runs_the_requested_suites_on_the_best_checkpoint(finished):
    final = json.loads((finished / "final_eval.json").read_text())
    assert set(final["suites"]) == {"attacker-eval-v1"}
    assert final["suites"]["attacker-eval-v1"]["episodes"] == EPISODES
    assert final["best_step"] in (200, 400)


def test_same_seed_gives_identical_results(tmp_path):
    go(tmp_path / "a")
    go(tmp_path / "b")
    for name in ("eval.csv", "train.csv", "final_eval.json"):
        first = (tmp_path / "a" / "EXP-D1" / "toy" / "s0" / name).read_text()
        second = (tmp_path / "b" / "EXP-D1" / "toy" / "s0" / name).read_text()
        assert first == second, name


def test_different_seeds_train_differently(finished):
    first = (finished / "train.csv").read_text()
    assert first != (finished.parent / "s1" / "train.csv").read_text()


def test_existing_run_is_not_overwritten(tmp_path):
    go(tmp_path)
    with pytest.raises(FileExistsError):
        go(tmp_path)
    go(tmp_path, overwrite=True)


def test_test_split_is_rejected_for_training(tmp_path):
    raw = config()
    raw["env"]["split"] = "test"
    with pytest.raises(ConfigError, match="train"):
        go(tmp_path, raw)
    assert not list(tmp_path.iterdir())


def test_dirty_tree_blocks_the_run_before_writing(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (
        ["init", "-q", "-b", "w"],
        ["config", "user.email", "t@e.c"],
        ["config", "user.name", "t"],
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True)
    (repo / "wafarena").mkdir()
    (repo / "wafarena" / "a.py").write_text("1")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "i"], check=True)
    (repo / "wafarena" / "a.py").write_text("2")
    with pytest.raises(DirtyTreeError):
        runner.run_experiment(
            config(),
            results_root=tmp_path / "out",
            repo=repo,
            allow_dirty=False,
            backend=FakeBackend(),
        )
    assert not (tmp_path / "out").exists()


def test_dirty_runs_are_marked_in_meta(tmp_path):
    go(tmp_path)
    meta = yaml.safe_load((tmp_path / "EXP-D1" / "toy" / "s0" / "meta.yaml").read_text())
    assert meta["allow_dirty"] is True


def test_defender_environment_is_not_runnable_yet(tmp_path):
    raw = config()
    raw["env"] = {"id": "WafArena/Defender-v0"}
    raw["eval"] = {"suites": ["defender-eval-v1"]}
    with pytest.raises(NotImplementedError, match="Phase 3"):
        go(tmp_path, raw)
