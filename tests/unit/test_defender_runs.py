"""F3-T02: defender runs end to end (experimentos.md), the opponent pool (env-defensor.md) and the
defender validation suite (metricas.md)."""

import copy
import csv
import dataclasses
import json
from pathlib import Path

import pytest
import yaml

from wafarena import run as runner
from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs.backends.cache import ModSecCache
from wafarena.envs.backends.fake import FakeBackend
from wafarena.envs.defender_env import DefenderEnv
from wafarena.eval import harness

REPO = Path(__file__).parents[2]
SESSIONS = 40  # suites are shortened here; their real definitions are tested elsewhere
POOL = {
    "type": "pool",
    "paths": ["corpus-replay", "random-mutation", "ATK-REF-0"],
    "weights": [1, 1, 1],
}


@pytest.fixture(autouse=True, scope="module")
def short_suites():
    patch = pytest.MonkeyPatch()
    for suites in (harness.DEFENDER_SUITES, harness.DEFENDER_VALIDATION_SUITES):
        for name, suite in list(suites.items()):
            patch.setitem(suites, name, dataclasses.replace(suite, n_sessions=SESSIONS))
    patch.setattr(runner, "_fpr_caps", {})
    yield
    patch.undo()


CONFIG = {
    "exp_id": "EXP-E1",
    "run_name": "toy-linear",
    "seeds": [0, 1],
    "env": {"id": "WafArena/Defender-v0", "attacker": POOL, "attack_ratio": 0.3},
    "agent": {"algo": "linear", "params": {"method": "qlearning", "alpha": 0.05}},
    "train": {"total_steps": 300},
    "eval": {"suites": ["defender-eval-v1"], "every_steps": 150, "final": True},
    "logging": {"tensorboard": False},
}


def go(root: Path, raw=None, **kwargs):
    return runner.run_experiment(
        copy.deepcopy(raw or CONFIG),
        results_root=root,
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
    return root / "EXP-E1" / "toy-linear" / "s0"


# --- the opponent pool -------------------------------------------------------------------------


def attackers_over(env: DefenderEnv, seeds) -> list[str]:
    names = []
    for seed in seeds:
        env.reset(seed=seed, options={"base_id": env._bases[0].base_id})
        names.append(type(env._attacker).__name__)
    return names


def test_pool_samples_every_entry_reproducibly_from_the_env_seed():
    env = DefenderEnv(FakeBackend(), attacker=POOL)
    first = attackers_over(env, range(60))
    assert set(first) == {"CorpusReplayAttacker", "RandomMutationAttacker", "AttackerDriver"}
    assert first == attackers_over(DefenderEnv(FakeBackend(), attacker=POOL), range(60))


def test_pool_weights_decide_the_mix():
    only_replay = {**POOL, "weights": [1, 0, 0]}
    env = DefenderEnv(FakeBackend(), attacker=only_replay)
    assert set(attackers_over(env, range(20))) == {"CorpusReplayAttacker"}


@pytest.mark.parametrize("weights", [[1, 1], [0, 0, 0], [1, -1, 1]])
def test_pool_rejects_bad_weights(weights):
    with pytest.raises(ValueError, match="weight"):
        DefenderEnv(FakeBackend(), attacker={**POOL, "weights": weights})


def test_defender_env_accepts_a_ready_attacker_policy_object():
    from wafarena.attackers.corpus_replay import CorpusReplayAttacker

    policy = CorpusReplayAttacker()
    env = DefenderEnv(FakeBackend(), attacker=policy, attack_ratio=1.0)
    env.reset(seed=0)
    assert env._attacker is policy


def test_non_pool_attackers_do_not_consume_the_env_rng():
    """Adding the pool must not change existing trajectories (smoke.csv stays identical)."""
    env = DefenderEnv(FakeBackend(), attacker="random_mutation", attack_ratio=1.0)
    env.reset(seed=3)
    state = copy.deepcopy(env.np_random.bit_generator.state)
    env._attacker_factory(env.np_random)
    assert env.np_random.bit_generator.state == state


# --- the ModSecurity cache ---------------------------------------------------------------------


def test_cache_flush_is_atomic_and_leaves_no_temporary_file(tmp_path):
    cache = ModSecCache(tmp_path / "cache.json")
    cache.put(1, "GET", "/search?q=x", 3, False)
    cache.flush()
    assert json.loads((tmp_path / "cache.json").read_text())
    assert [p.name for p in tmp_path.iterdir()] == ["cache.json"]
    assert ModSecCache(tmp_path / "cache.json").get(1, "GET", "/search?q=x") == (3, False)


# --- defender evaluation -----------------------------------------------------------------------


def test_defender_val_suite_draws_from_val_only():
    splits = json.loads(harness.SPLITS_PATH.read_text())
    plan = harness.build_session_plan(harness.DEFENDER_VALIDATION_SUITES["defender-val-v1"])
    assert {p.ref for p in plan if p.is_attack} <= set(splits["payloads"]["val"])
    assert {p.ref for p in plan if not p.is_attack} <= set(splits["benign"]["val"])
    assert "defender-val-v1" not in harness.DEFENDER_SUITES  # never a reported suite


def test_evaluate_defender_pools_attackers_and_breaks_attack_metrics_down():
    summary = harness.evaluate_defender(ModSecDefender(2), "defender-val-v1", backend=FakeBackend())
    for metric in ("tpr", "er_d", "fpr", "fpr_h", "fpr_s", "fpr_h_s", "f1"):
        assert metric in summary
    for attacker in ("corpus-replay", "random-mutation", "ATK-REF-0"):
        assert {f"tpr@{attacker}", f"er_d@{attacker}", f"f1@{attacker}"} <= set(summary)
    assert summary["requests"] > summary["attack_requests"] > 0


# --- the selection rule ------------------------------------------------------------------------


def test_selection_prefers_any_feasible_point_then_higher_tpr():
    cap = 0.01
    infeasible_strong = runner.selection_key({"tpr": 0.99, "fpr": 0.2}, cap)
    feasible_weak = runner.selection_key({"tpr": 0.5, "fpr": 0.01}, cap)
    feasible_strong = runner.selection_key({"tpr": 0.9, "fpr": 0.0}, cap)
    assert feasible_strong > feasible_weak > infeasible_strong


def test_selection_without_feasible_points_prefers_lower_fpr():
    cap = 0.0
    assert runner.selection_key({"tpr": 0.1, "fpr": 0.05}, cap) > runner.selection_key(
        {"tpr": 0.9, "fpr": 0.3}, cap
    )


# --- runner, end to end ------------------------------------------------------------------------


def test_defender_run_produces_the_documented_output_tree(finished):
    for name in ("config.resolved.yaml", "meta.yaml", "train.csv", "eval.csv", "final_eval.json"):
        assert (finished / name).exists(), name
    assert (finished / "checkpoint" / "meta.yaml").exists()
    assert (finished.parent / "s1").is_dir()


def test_defender_train_csv_has_one_row_per_session(finished):
    rows = read_csv(finished / "train.csv")
    assert {"return", "length", "attack", "blocked", "allowed_effect", "m_weight_norm"} <= set(
        rows[0]
    )
    assert sum(int(r["length"]) for r in rows) == 300


def test_defender_eval_csv_uses_defender_val(finished):
    rows = read_csv(finished / "eval.csv")
    assert [int(r["step"]) for r in rows] == [150, 300]
    assert {r["suite"] for r in rows} == {"defender-val-v1"}


def test_defender_checkpoint_follows_the_selection_rule(finished):
    final = json.loads((finished / "final_eval.json").read_text())
    rows = read_csv(finished / "eval.csv")
    keys = [
        runner.selection_key({"tpr": float(r["tpr"]), "fpr": float(r["fpr"])}, final["fpr_cap"])
        for r in rows
    ]
    first_best = keys.index(max(keys))  # the runner keeps the earliest of tied points
    assert final["best_step"] == int(rows[first_best]["step"])
    meta = yaml.safe_load((finished / "checkpoint" / "meta.yaml").read_text())
    assert meta["role"] == "defender" and meta["obs_dim"] == 37 and meta["n_actions"] == 5
    assert meta["train"]["agent_params"] == CONFIG["agent"]["params"]
    assert meta["eval_summary"]["fpr_cap"] == final["fpr_cap"]


def test_fpr_cap_is_modsec_pl2_on_defender_val(finished):
    final = json.loads((finished / "final_eval.json").read_text())
    reference = harness.evaluate_defender(
        ModSecDefender(2), "defender-val-v1", backend=FakeBackend()
    )
    assert final["fpr_cap"] == reference["fpr"]


def test_defender_final_eval_reports_every_defender_metric(finished):
    final = json.loads((finished / "final_eval.json").read_text())
    suite = final["suites"]["defender-eval-v1"]
    assert {"tpr", "fpr", "fpr_h", "f1", "tpr@ATK-REF-0"} <= set(suite)


def test_defender_run_is_reproducible(tmp_path):
    raw = {**CONFIG, "seeds": [0]}
    go(tmp_path / "a", raw)
    go(tmp_path / "b", raw)
    for name in ("eval.csv", "train.csv", "final_eval.json"):
        first = (tmp_path / "a" / "EXP-E1" / "toy-linear" / "s0" / name).read_text()
        second = (tmp_path / "b" / "EXP-E1" / "toy-linear" / "s0" / name).read_text()
        assert first == second, name


def test_defender_suites_are_rejected_for_attacker_runs():
    from wafarena.runconfig import ConfigError, resolve_config

    raw = copy.deepcopy(CONFIG)
    raw["eval"]["suites"] = ["attacker-eval-v1"]
    with pytest.raises(ConfigError, match="does not apply"):
        resolve_config(raw)
