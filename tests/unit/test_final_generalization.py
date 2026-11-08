"""F4-T08 selects checkpoints on validation evidence only."""

import pytest

from wafarena.eval.final_generalization import (
    aggregate_generalization,
    cached_cell,
    i5_plan,
    rank_dyna,
    select_pool_champion,
)


def _history():
    return [
        {
            "condition": "pool",
            "seed": str(seed),
            "run_id": f"EXP-I1__pool__s{seed}__eea6f78",
            "git_sha": "eea6f78",
            "defender_generation": "8",
            "attacker_generation": str(attacker),
            "split": "val",
            "sessions": "40",
            "fpr": str(fpr),
            "tpr": str(tpr),
        }
        for seed, fpr, tpr in ((0, 1 / 60, 0.99), (1, 2 / 60, 0.98), (2, 1 / 60, 0.95))
        for attacker in range(1, 8)
    ]


def test_pool_champion_falls_back_to_lowest_fpr_then_highest_tpr():
    result = select_pool_champion(_history(), source_sha="eea6f78", fpr_cap=0.0)
    assert result["winner_seed"] == 0
    assert result["feasible_count"] == 0
    assert result["candidates"][0]["mean_tpr"] == pytest.approx(0.99)
    assert [row["seed"] for row in result["candidates"]] == [0, 2, 1]


def test_pool_champion_rejects_missing_historical_opponent():
    with pytest.raises(ValueError, match="seven historical"):
        select_pool_champion(_history()[:-1], source_sha="eea6f78", fpr_cap=0.0)


def test_pool_champion_rejects_test_rows():
    rows = _history()
    rows[0]["split"] = "test"
    with pytest.raises(ValueError, match="val"):
        select_pool_champion(rows, source_sha="eea6f78", fpr_cap=0.0)


def test_dyna_tie_prefers_fewer_planning_steps_then_seed():
    candidates = [
        {"method": "dyna-20", "seed": 0, "val_er": 0.0, "planning_steps": 20},
        {"method": "dyna-5", "seed": 1, "val_er": 0.0, "planning_steps": 5},
        {"method": "dyna-5", "seed": 0, "val_er": 0.0, "planning_steps": 5},
    ]
    assert rank_dyna(candidates)[0] == candidates[2]


def test_i5_plan_matches_fixed_defender_test_sessions():
    from wafarena.eval.harness import DEFENDER_SUITES, build_session_plan

    plan = i5_plan()
    expected = build_session_plan(DEFENDER_SUITES["defender-eval-v1"])
    assert plan == expected
    assert len(plan) == 2000
    assert sum(item.is_attack for item in plan) == 200


def test_generalization_table_keeps_three_seed_ci_and_fixed_baselines():
    cells = [
        {
            "defender": "selfplay",
            "seed": seed,
            "tpr": tpr,
            "fpr": fpr,
            "er_d": 0.0,
            "eval_run_id": f"EXP-I3__selfplay__s{seed}__abc1234",
        }
        for seed, tpr, fpr in ((0, 0.8, 0.1), (1, 0.9, 0.2), (2, 1.0, 0.3))
    ]
    cells.extend(
        [
            {
                "defender": "DEF-REF-1",
                "seed": None,
                "tpr": 0.95,
                "fpr": 0.0,
                "er_d": 0.0,
                "eval_run_id": "EXP-I3__DEF-REF-1__abc1234",
            },
            {
                "defender": "modsec-pl2",
                "seed": None,
                "tpr": 0.85,
                "fpr": 0.0,
                "er_d": 0.0,
                "eval_run_id": "modsec-defender-suites__d9d7d49",
            },
        ]
    )
    rows = aggregate_generalization(cells, exp_id="EXP-I3", champion_seed=0)
    by_name = {row["defender"]: row for row in rows}
    assert by_name["selfplay-cohort"]["tpr"] == pytest.approx(0.9)
    assert by_name["selfplay-cohort"]["tpr_low"] <= 0.9 <= by_name["selfplay-cohort"]["tpr_high"]
    assert by_name["selfplay-champion"]["tpr"] == 0.8
    assert by_name["selfplay-champion"]["tpr_low"] is None
    assert by_name["DEF-REF-1"]["tpr_low"] is None
    assert by_name["modsec-pl2"]["tpr"] == 0.85


def test_generalization_rejects_missing_selfplay_seed():
    cells = [
        {"defender": "selfplay", "seed": seed, "tpr": 0.9, "fpr": 0.0, "er_d": 0.0}
        for seed in (0, 1)
    ]
    cells += [
        {"defender": name, "seed": None, "tpr": 0.9, "fpr": 0.0, "er_d": 0.0}
        for name in ("DEF-REF-1", "modsec-pl2")
    ]
    with pytest.raises(ValueError, match="three self-play seeds"):
        aggregate_generalization(cells, exp_id="EXP-I3", champion_seed=0)


def test_cached_cell_refuses_changed_checkpoint_hash(tmp_path):
    path = tmp_path / "cell.json"
    expected = {"eval_run_id": "EXP-I3__selfplay__s0__abc1234", "defender_sha256": "abc"}
    calls = []

    def compute():
        calls.append(1)
        return {"sessions": 2000, "tpr": 0.9, "fpr": 0.1, "er_d": 0.0}

    row = cached_cell(path, expected, compute)
    assert row["sessions"] == 2000
    assert cached_cell(path, expected, compute) == row
    assert len(calls) == 1
    with pytest.raises(ValueError, match="stale"):
        cached_cell(path, {**expected, "defender_sha256": "changed"}, compute)
    assert len(calls) == 1


def test_incomplete_cell_is_not_persisted(tmp_path):
    path = tmp_path / "cell.json"
    with pytest.raises(ValueError, match="incomplete"):
        cached_cell(
            path,
            {"eval_run_id": "EXP-I3__selfplay__s0__abc1234"},
            lambda: {"sessions": 1999, "tpr": 1.0, "fpr": 0.0, "er_d": 0.0},
        )
    assert not path.exists()


def test_cached_cell_records_undefined_extra_metric_as_null(tmp_path):
    path = tmp_path / "cell.json"
    row = cached_cell(
        path,
        {"eval_run_id": "EXP-I5__modsec-pl2__abc1234"},
        lambda: {
            "sessions": 2000,
            "tpr": 0.9,
            "fpr": 0.0,
            "er_d": 0.0,
            "q_allow_attack": float("nan"),
        },
    )
    assert row["q_allow_attack"] is None


def test_cached_cell_accepts_pooled_family_suite_session_count(tmp_path):
    row = cached_cell(
        tmp_path / "cell.json",
        {"eval_run_id": "EXP-I3__selfplay__s0__abc1234", "sessions": 4000},
        lambda: {"tpr": 1.0, "fpr": 0.0, "er_d": 0.0},
    )
    assert row["sessions"] == 4000
