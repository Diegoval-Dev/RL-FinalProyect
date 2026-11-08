"""F4-T08 selects checkpoints on validation evidence only."""

import pytest

from wafarena.eval.final_generalization import rank_dyna, select_pool_champion


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
