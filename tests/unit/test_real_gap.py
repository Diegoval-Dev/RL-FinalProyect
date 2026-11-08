"""EXP-R1 uses fixed reduced plans and paired, absolute mode gaps."""

import pytest
import yaml

from wafarena.eval.real_gap import (
    aggregate_gaps,
    attacker_episode_seeds,
    cached_r1_cell,
    defender_plans,
    load_spec,
    plan_sha256,
)


def test_attacker_episode_blocks_are_fifty_disjoint_test_seeds():
    blocks = [attacker_episode_seeds(start) for start in (1000, 1050, 1100)]
    assert [len(block) for block in blocks] == [50, 50, 50]
    assert blocks[0][0] == 1000 and blocks[-1][-1] == 1149
    assert len(set().union(*map(set, blocks))) == 150
    with pytest.raises(ValueError, match="attacker-eval-v1"):
        attacker_episode_seeds(1190)


def test_spec_rejects_changed_reduced_suite_size(tmp_path):
    source = yaml.safe_load(open("configs/eval/EXP-R1/real-validation.yaml"))
    assert load_spec("configs/eval/EXP-R1/real-validation.yaml")["defender_sessions"] == 500
    source["defender_sessions"] = 200
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(source))
    with pytest.raises(ValueError, match="defender_sessions"):
        load_spec(path)


def test_defender_plan_has_five_hundred_sessions_and_is_reproducible():
    first = defender_plans(7000, 10000)
    second = defender_plans(7000, 10000)
    assert first == second
    assert set(first) == {"ATK-REF-0", "ATK-REF-1"}
    assert [len(items) for items in first.values()] == [250, 250]
    assert [sum(item.is_attack for item in items) for items in first.values()] == [25, 25]
    assert len({item.seed for items in first.values() for item in items}) == 500
    assert plan_sha256(first) == plan_sha256(second)
    assert plan_sha256(first) != plan_sha256(defender_plans(8000, 10500))


def test_plan_fingerprint_covers_attacker_episode_seeds():
    first = {"split": "test", "seeds": attacker_episode_seeds(1000), "query_budget": 50}
    second = {**first, "seeds": attacker_episode_seeds(1050)}
    assert plan_sha256(first) == plan_sha256(dict(reversed(list(first.items()))))
    assert plan_sha256(first) != plan_sha256(second)


def test_gap_aggregation_pairs_modes_by_seed_and_uses_absolute_difference():
    cells = []
    for seed, (fast, real) in enumerate(((0.2, 0.1), (0.4, 0.3), (0.6, 0.5))):
        for mode, value in (("fast", fast), ("real", real)):
            cells.append(
                {
                    "role": "attacker",
                    "agent": "ATK-REF-0",
                    "mode": mode,
                    "seed": seed,
                    "plan_sha256": f"plan-{seed}",
                    "source_run_id": "source",
                    "weight_sha256": "weights",
                    "opponent_run_ids": "opponent-run",
                    "opponent_sha256": "opponent-weights",
                    "eval_run_id": f"run-{seed}-{mode}",
                    "evasion_rate": value,
                    "qfe": None,
                    "qfe_c": 50.0,
                    "diversity": None,
                    "uniqueness": None,
                    "break_rate": 0.1,
                }
            )
    rows = aggregate_gaps(cells)
    er = next(row for row in rows if row["metric"] == "evasion_rate")
    assert er["n_seeds"] == er["n_defined"] == 3
    assert er["gap_mean"] == pytest.approx(0.1)
    assert er["gap_low"] == pytest.approx(0.1)
    assert er["gap_high"] == pytest.approx(0.1)
    qfe = next(row for row in rows if row["metric"] == "qfe")
    assert qfe["n_defined"] == 0
    assert qfe["gap_mean"] is None
    cells[-1]["plan_sha256"] = "wrong"
    with pytest.raises(ValueError, match="plan"):
        aggregate_gaps(cells)
    cells[-1]["plan_sha256"] = "plan-2"
    cells[-1]["opponent_sha256"] = "different"
    with pytest.raises(ValueError, match="checkpoint"):
        aggregate_gaps(cells)


def test_cached_cell_rejects_changed_plan_without_recomputing(tmp_path):
    path = tmp_path / "cell.json"
    expected = {
        "role": "attacker",
        "agent": "ATK-REF-0",
        "seed": 0,
        "mode": "fast",
        "plan_sha256": "first",
        "weight_sha256": "weights",
        "planned_episodes": 50,
    }
    metrics = {
        "episodes": 50,
        "evasion_rate": 0.0,
        "qfe": float("nan"),
        "qfe_c": 50.0,
        "diversity": float("nan"),
        "uniqueness": float("nan"),
        "break_rate": 0.0,
    }
    first = cached_r1_cell(path, expected, lambda: metrics)
    assert first["qfe"] is None
    assert cached_r1_cell(path, expected, lambda: pytest.fail("cache was recomputed")) == first
    with pytest.raises(ValueError, match="stale"):
        cached_r1_cell(path, {**expected, "plan_sha256": "second"}, lambda: metrics)
