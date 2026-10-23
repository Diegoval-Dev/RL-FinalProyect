"""F2-T05: end-to-end bandit experiment runs (catalogo.md EXP-A1/EXP-A2, experimentos.md output)."""

import copy
import csv
import json
from pathlib import Path

import pytest

from wafarena import bandit_run
from wafarena.envs.backends.fake import FakeBackend
from wafarena.eval.arm_means import defender_label

REPO = Path(__file__).parents[2]
PL1 = {"type": "modsec", "paranoia_level": 1}
PL3 = {"type": "modsec", "paranoia_level": 3}

CONFIG = {
    "exp_id": "EXP-A1",
    "run_name": "toy",
    "seeds": [0, 1],
    "env": {"id": "WafArena/AttackerBandit-v0", "defender": PL1, "query_budget": 10},
    "agent": {"algo": "bandit", "params": {"policy": "eps_greedy", "epsilon": 0.2}},
    "train": {"total_steps": 60},
    "eval": {"suites": ["attacker-eval-v1"]},
}


def write_arm_means(path: Path, pl1=0.0, pl3=0.0) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["defender", "arm", "operator", "mu", "pulls", "seed", "git_sha"])
        for arm in range(16):
            writer.writerow([defender_label(PL1), arm, f"op{arm}", pl1, 10, 0, "x"])
            writer.writerow([defender_label(PL3), arm, f"op{arm}", pl3, 10, 0, "x"])


def go(tmp_path: Path, raw=None, **kwargs):
    tmp_path.mkdir(parents=True, exist_ok=True)
    means = tmp_path / "means.csv"
    if not means.exists():
        write_arm_means(means)
    return bandit_run.run_experiment(
        raw or copy.deepcopy(CONFIG),
        results_root=tmp_path / "results",
        repo=REPO,
        allow_dirty=True,
        backend=FakeBackend(),
        arm_means_path=means,
        **kwargs,
    )


@pytest.fixture(scope="module")
def finished(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("bandit")
    go(root)
    return root / "results" / "EXP-A1" / "toy" / "s0"


def test_run_produces_the_documented_output_tree(finished):
    for name in ("config.resolved.yaml", "meta.yaml", "pulls.csv", "final_eval.json", "checkpoint"):
        assert (finished / name).exists(), name
    assert (finished.parent / "s1").is_dir()


def read_pulls(path: Path) -> list[dict]:
    with (path / "pulls.csv").open() as handle:
        return list(csv.DictReader(handle))


def test_pulls_csv_has_one_row_per_pull_with_arm_reward_and_regret(finished):
    rows = read_pulls(finished)
    assert [int(r["step"]) for r in rows] == list(range(1, 61))
    assert {"arm", "reward", "regret_instant", "regret_cumulative"} <= set(rows[0])
    assert all(0 <= int(r["arm"]) < 16 for r in rows)


def test_cumulative_regret_is_nondecreasing_and_matches_the_running_sum(finished):
    rows = read_pulls(finished)
    cumulative = [float(r["regret_cumulative"]) for r in rows]
    assert cumulative == sorted(cumulative)
    running = 0.0
    for row, total in zip(rows, cumulative, strict=True):
        running += float(row["regret_instant"])
        assert total == pytest.approx(running)


def test_final_eval_deploys_the_bandits_learned_policy(finished):
    final = json.loads((finished / "final_eval.json").read_text())
    assert set(final["suites"]) == {"attacker-eval-v1"}
    assert final["suites"]["attacker-eval-v1"]["episodes"] == 200


def test_same_seed_gives_identical_pulls(tmp_path):
    go(tmp_path / "a")
    go(tmp_path / "b")
    a = (tmp_path / "a" / "results" / "EXP-A1" / "toy" / "s0" / "pulls.csv").read_text()
    b = (tmp_path / "b" / "results" / "EXP-A1" / "toy" / "s0" / "pulls.csv").read_text()
    assert a == b


def test_different_seeds_pull_differently(finished):
    first = (finished / "pulls.csv").read_text()
    assert first != (finished.parent / "s1" / "pulls.csv").read_text()


def test_nonstationary_switch_uses_the_post_switch_means_after_the_switch(tmp_path):
    means = tmp_path / "means.csv"
    with means.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["defender", "arm", "operator", "mu", "pulls", "seed", "git_sha"])
        for arm in range(16):
            writer.writerow([defender_label(PL1), arm, f"op{arm}", arm / 100, 10, 0, "x"])
            writer.writerow([defender_label(PL3), arm, f"op{arm}", (15 - arm) / 100, 10, 0, "x"])
    raw = copy.deepcopy(CONFIG)
    raw["run_name"] = "switch"
    raw["seeds"] = [0]
    raw["env"]["switch_at"] = 20
    raw["env"]["switch_defender"] = PL3
    raw["train"]["total_steps"] = 40
    bandit_run.run_experiment(
        raw,
        results_root=tmp_path / "out",
        repo=REPO,
        allow_dirty=True,
        backend=FakeBackend(),
        arm_means_path=means,
    )
    rows = read_pulls(tmp_path / "out" / "EXP-A1" / "switch" / "s0")
    for i, row in enumerate(rows):
        arm = int(row["arm"])
        mu = [a / 100 for a in range(16)] if i < 20 else [(15 - a) / 100 for a in range(16)]
        expected = max(mu) - mu[arm]
        assert float(row["regret_instant"]) == pytest.approx(expected), i


def test_existing_run_is_not_overwritten(tmp_path):
    go(tmp_path)
    with pytest.raises(FileExistsError):
        go(tmp_path)
    go(tmp_path, overwrite=True)


def test_non_bandit_environment_is_rejected(tmp_path):
    raw = copy.deepcopy(CONFIG)
    raw["env"]["id"] = "WafArena/Attacker-v0"
    with pytest.raises(NotImplementedError, match="Bandit"):
        go(tmp_path, raw)
