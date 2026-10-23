"""F2-T06: end-to-end EXP-B1 runs (catalogo.md: model, VI, PI, convergence, final eval)."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from wafarena import dp_run
from wafarena.envs.abstract_state import N_STATES
from wafarena.envs.backends.fake import FakeBackend

REPO = Path(__file__).parents[2]

CONFIG = {
    "exp_id": "EXP-B1",
    "run_name": "toy",
    "seeds": [0, 1],
    "env": {
        "id": "WafArena/Attacker-v0",
        "defender": {"type": "modsec", "paranoia_level": 1},
        "query_budget": 10,
        "max_steps": 20,
    },
    "agent": {"algo": "dp", "params": {"gamma": 0.9, "theta": 1e-4}},
    "train": {"total_steps": 3000},
    "eval": {"suites": ["attacker-eval-v1"], "final": True},
}


def go(tmp_path: Path, raw=None, **kwargs):
    return dp_run.run_experiment(
        raw or copy.deepcopy(CONFIG),
        results_root=tmp_path,
        repo=REPO,
        allow_dirty=True,
        backend=FakeBackend(),
        **kwargs,
    )


@pytest.fixture(scope="module")
def finished(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("results")
    go(root)
    return root / "EXP-B1" / "toy" / "s0"


def test_run_produces_the_documented_output_tree(finished):
    for name in (
        "config.resolved.yaml",
        "meta.yaml",
        "model_summary.json",
        "final_eval.json",
        "checkpoint",
    ):
        assert (finished / name).exists(), name
    assert (finished.parent / "s1").is_dir()


def test_model_summary_reports_convergence_and_agreement(finished):
    summary = json.loads((finished / "model_summary.json").read_text())
    assert summary["value_iteration"]["iterations"] > 0
    assert summary["policy_iteration"]["iterations"] > 0
    assert "policies_agree" in summary
    assert summary["max_value_diff"] >= 0
    assert summary["n_transitions"] == CONFIG["train"]["total_steps"]


def test_checkpoint_is_a_valid_policy_table(finished):
    import numpy as np

    policy = np.load(finished / "checkpoint" / "policy.npy")
    assert policy.shape == (N_STATES,)
    assert policy.min() >= 0 and policy.max() < 17


def test_final_eval_runs_the_requested_suite(finished):
    final = json.loads((finished / "final_eval.json").read_text())
    assert set(final["suites"]) == {"attacker-eval-v1"}
    assert final["suites"]["attacker-eval-v1"]["episodes"] == 200


def _without_timings(summary: dict) -> dict:
    return {
        key: (
            {k: v for k, v in value.items() if k != "seconds"}
            if key.endswith("iteration")
            else value
        )
        for key, value in summary.items()
    }


def test_same_seed_gives_identical_results(tmp_path):
    go(tmp_path / "a")
    go(tmp_path / "b")
    a = json.loads((tmp_path / "a" / "EXP-B1" / "toy" / "s0" / "model_summary.json").read_text())
    b = json.loads((tmp_path / "b" / "EXP-B1" / "toy" / "s0" / "model_summary.json").read_text())
    assert _without_timings(a) == _without_timings(b)
    a = (tmp_path / "a" / "EXP-B1" / "toy" / "s0" / "final_eval.json").read_text()
    b = (tmp_path / "b" / "EXP-B1" / "toy" / "s0" / "final_eval.json").read_text()
    assert a == b


def test_different_seeds_collect_different_transitions(finished):
    s0 = json.loads((finished / "model_summary.json").read_text())
    s1 = json.loads((finished.parent / "s1" / "model_summary.json").read_text())
    assert s0 != s1 or s0["value_iteration"]["iterations"] != s1["value_iteration"]["iterations"]


def test_existing_run_is_not_overwritten(tmp_path):
    go(tmp_path)
    with pytest.raises(FileExistsError):
        go(tmp_path)
    go(tmp_path, overwrite=True)


def test_cli_runs_a_config_file(tmp_path, monkeypatch):
    path = tmp_path / "exp.yaml"
    path.write_text(yaml.safe_dump(copy.deepcopy(CONFIG) | {"seeds": [0]}))
    monkeypatch.setattr(dp_run, "resolve_backend", lambda kind: FakeBackend())
    dp_run.main(["--config", str(path), "--results", str(tmp_path / "out"), "--allow-dirty"])
    assert (tmp_path / "out" / "EXP-B1" / "toy" / "s0" / "final_eval.json").exists()
