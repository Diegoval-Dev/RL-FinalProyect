"""F3-T07: evaluation-only experiments re-evaluate trained checkpoints (EXP-F6, EXP-F7)."""

import copy
import dataclasses
import json
from pathlib import Path

import pytest
import yaml

from wafarena import evaluate
from wafarena import run as runner
from wafarena.envs.backends.fake import FakeBackend
from wafarena.eval import harness
from wafarena.runconfig import ConfigError
from wafarena.summarize import summarize_experiment

REPO = Path(__file__).parents[2]
TRAIN = {
    "exp_id": "EXP-F5",
    "run_name": "toy",
    "seeds": [0, 1],
    "env": {"id": "WafArena/Defender-v0", "attacker": "corpus_replay", "attack_ratio": 0.3},
    "agent": {"algo": "linear", "params": {"alpha": 0.05}},
    "train": {"total_steps": 100},
    "eval": {"suites": ["defender-eval-v1"], "every_steps": 100},
    "logging": {"tensorboard": False},
}
EVAL = {
    "exp_id": "EXP-F6",
    "run_name": "toy",
    "seeds": [0, 1],
    "evaluate": {
        "checkpoints": {"exp_id": "EXP-F5", "run_name": "toy"},
        "suites": ["defender-eval-family-v1"],
    },
}


@pytest.fixture(scope="module")
def trained(tmp_path_factory) -> Path:
    patch = pytest.MonkeyPatch()
    for suites in (harness.DEFENDER_SUITES, harness.DEFENDER_VALIDATION_SUITES):
        for name, suite in list(suites.items()):
            patch.setitem(suites, name, dataclasses.replace(suite, n_sessions=30))
    patch.setattr(runner, "_fpr_caps", {})
    root = tmp_path_factory.mktemp("results")
    runner.run_experiment(
        copy.deepcopy(TRAIN), results_root=root, repo=REPO, allow_dirty=True, backend=FakeBackend()
    )
    yield root
    patch.undo()


def go(root, raw=None):
    return evaluate.run_evaluation(
        copy.deepcopy(raw or EVAL),
        results_root=root,
        repo=REPO,
        backend=FakeBackend(),
        allow_dirty=True,
    )


def test_evaluation_writes_the_runner_tree_with_the_source_run(trained):
    (directory, _) = go(trained)
    final = json.loads((directory / "final_eval.json").read_text())
    meta = yaml.safe_load((directory / "meta.yaml").read_text())
    source = yaml.safe_load((trained / "EXP-F5" / "toy" / "s0" / "meta.yaml").read_text())
    assert final["source_run_id"] == source["run_id"] == meta["source_run_id"]
    assert meta["run_id"].startswith("EXP-F6__toy__s0__")
    assert {"tpr", "fpr", "f1"} <= set(final["suites"]["defender-eval-family-v1"])


def test_summarize_works_on_evaluation_only_experiments(trained, tmp_path):
    go(trained)
    out = summarize_experiment("EXP-F6", trained, tmp_path)
    rows = out.read_text().splitlines()
    assert rows[1].startswith("toy,defender-eval-family-v1,2,")


def test_missing_checkpoint_is_an_error(trained):
    raw = copy.deepcopy(EVAL)
    raw["seeds"] = [7]
    with pytest.raises(FileNotFoundError):
        go(trained, raw)


@pytest.mark.parametrize(
    "change",
    [
        {"evaluate": {**EVAL["evaluate"], "suites": ["defender-val-v1"]}},  # never reported
        {"evaluate": {**EVAL["evaluate"], "suites": ["defender-eval-v1", "attacker-eval-v1"]}},
        {"exp_id": "EXP-NOPE"},
        {"evaluate": {**EVAL["evaluate"], "checkpoints": {"exp_id": "EXP-F5"}}},
        {"surprise": 1},
    ],
)
def test_invalid_evaluation_configs_are_rejected(change):
    with pytest.raises(ConfigError):
        evaluate.resolve_eval_config({**EVAL, **change})
