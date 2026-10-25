"""F3-T05/F3-T11: the selection rules that publish DEF-REF-1 (ADR-0010) and ATK-REF-1."""

import importlib
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[2] / "scripts"


def script(name: str):
    sys.path.insert(0, str(SCRIPTS))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(str(SCRIPTS))


def cand(**kw):
    base = {"val_tpr": 1.0, "val_fpr": 0.0, "val_f1": 1.0, "fpr_cap": 0.0, "seed": 0}
    row = {**base, **kw}
    row["feasible"] = int(row["val_fpr"] <= row["fpr_cap"])
    row.setdefault("run_name_mean_val_tpr", row["val_tpr"])
    return row


def test_def_ref_rule_prefers_feasible_then_tpr():
    select = script("select_def_ref")
    feasible = cand(val_tpr=0.9)
    infeasible = cand(val_tpr=1.0, val_fpr=0.1)
    assert select.rank_key(feasible) > select.rank_key(infeasible)


@pytest.mark.parametrize(
    ("better", "worse"),
    [
        ({"val_f1": 1.0}, {"val_f1": 0.9}),
        ({"run_name_mean_val_tpr": 0.999}, {"run_name_mean_val_tpr": 0.99}),
        ({"seed": 0}, {"seed": 3}),
    ],
)
def test_def_ref_tie_break_of_adr_0010_uses_val_only(better, worse):
    select = script("select_def_ref")
    assert select.rank_key(cand(**better)) > select.rank_key(cand(**worse))


def test_atk_ref_rule_is_er_then_qfe_c_then_seed():
    select = script("select_atk_ref")
    row = {"val_evasion_rate": 0.005, "val_qfe_c": 49.8, "seed": 2}
    assert select.rank_key(row) > select.rank_key({**row, "val_evasion_rate": 0.0})
    assert select.rank_key(row) > select.rank_key({**row, "val_qfe_c": 49.9})
    assert select.rank_key({**row, "seed": 1}) > select.rank_key(row)


def test_published_references_load():
    from wafarena.agents import load_checkpoint

    refs = Path(__file__).parents[2] / "checkpoints" / "refs"
    for ref, role in (("DEF-REF-1", "defender"), ("ATK-REF-1", "attacker")):
        agent = load_checkpoint(refs / ref)
        assert agent.agent_id == ref and agent.role == role
