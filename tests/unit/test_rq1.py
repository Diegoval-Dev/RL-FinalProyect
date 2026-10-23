"""F2-T09: the RQ1 vulnerability table (catalogo.md: ER, QFE, DIV per method and PL, with CIs)."""

import csv
import dataclasses
from pathlib import Path

import pytest

from wafarena import rq1
from wafarena.agents.base import save_checkpoint
from wafarena.agents.random_agent import RandomAgent
from wafarena.envs.attacker_env import N_ACTIONS
from wafarena.envs.attacker_obs import OBS_SIZE
from wafarena.envs.backends.fake import FakeBackend
from wafarena.eval import harness

REPO = Path(__file__).parents[2]
EPISODES = 20  # suites are shortened here; their real definitions are tested in test_eval_harness


@pytest.fixture(autouse=True)
def short_suites():
    patch = pytest.MonkeyPatch()
    suite = harness.ATTACKER_SUITES[rq1.SUITE]
    short = range(suite.seeds.start, suite.seeds.start + EPISODES)
    patch.setitem(harness.ATTACKER_SUITES, rq1.SUITE, dataclasses.replace(suite, seeds=short))
    yield
    patch.undo()


def fake_checkpoints(root: Path, exp_id: str, run_name: str, n_seeds: int = 3) -> None:
    for seed in range(n_seeds):
        agent = RandomAgent(f"{run_name}-s{seed}", N_ACTIONS, seed)
        save_checkpoint(
            agent,
            root / exp_id / run_name / f"s{seed}" / "checkpoint",
            algo="random",
            obs_dim=OBS_SIZE,
            n_actions=N_ACTIONS,
        )


METHODS = {
    "my-method": {"kind": "checkpoint", "exp_id": "EXP-X", "run_name": "toy"},
    "corpus-replay": {"kind": "scripted", "variant": "corpus_replay"},
}


def test_table_has_one_row_per_method_and_pl(tmp_path):
    fake_checkpoints(tmp_path, "EXP-X", "toy")
    rows = rq1.build_rq1_table(
        METHODS, results_root=tmp_path, backend=FakeBackend(), pls=(1, 2), n_seeds=3
    )
    assert {(r["method"], r["pl"]) for r in rows} == {
        ("my-method", 1),
        ("my-method", 2),
        ("corpus-replay", 1),
        ("corpus-replay", 2),
    }


def test_row_has_er_qfe_div_with_bootstrap_ci(tmp_path):
    fake_checkpoints(tmp_path, "EXP-X", "toy")
    rows = rq1.build_rq1_table(
        METHODS, results_root=tmp_path, backend=FakeBackend(), pls=(1,), n_seeds=3
    )
    row = next(r for r in rows if r["method"] == "my-method")
    for metric in ("evasion_rate", "qfe", "diversity"):
        assert f"{metric}_mean" in row and f"{metric}_low" in row and f"{metric}_high" in row
    assert row["n_seeds"] == 3


def test_each_seed_loads_its_own_checkpoint(tmp_path):
    """A different checkpoint per seed must actually be used, not the same one 3 times."""
    loaded_ids = []
    original = rq1.load_checkpoint

    def spy(path):
        agent = original(path)
        loaded_ids.append(agent.agent_id)
        return agent

    fake_checkpoints(tmp_path, "EXP-X", "toy", n_seeds=3)
    import wafarena.rq1 as rq1_module

    real = rq1_module.load_checkpoint
    rq1_module.load_checkpoint = spy
    try:
        rq1.build_rq1_table(
            METHODS, results_root=tmp_path, backend=FakeBackend(), pls=(1,), n_seeds=3
        )
    finally:
        rq1_module.load_checkpoint = real
    assert sorted(loaded_ids) == ["toy-s0", "toy-s1", "toy-s2"]


def test_scripted_method_builds_a_fresh_agent_per_seed(tmp_path):
    rows = rq1.build_rq1_table(
        {"random-mutation": {"kind": "scripted", "variant": "random_mutation"}},
        results_root=tmp_path,
        backend=FakeBackend(),
        pls=(1,),
        n_seeds=5,
    )
    assert rows[0]["n_seeds"] == 5


def test_unknown_method_kind_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="no-such-kind"):
        rq1.build_rq1_table(
            {"bad": {"kind": "no-such-kind"}},
            results_root=tmp_path,
            backend=FakeBackend(),
            pls=(1,),
        )


def test_write_rq1_table_produces_a_csv(tmp_path):
    fake_checkpoints(tmp_path, "EXP-X", "toy")
    out = rq1.write_rq1_table(
        METHODS,
        results_root=tmp_path,
        out_path=tmp_path / "RQ1_table.csv",
        backend=FakeBackend(),
        pls=(1, 2),
        n_seeds=3,
    )
    with out.open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert out == tmp_path / "RQ1_table.csv"
