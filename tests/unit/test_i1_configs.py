"""EXP-I1 conditions must differ only in opponent sampling."""

from copy import deepcopy
from pathlib import Path

import yaml

from wafarena.selfplay.config import load_config

ROOT = Path(__file__).parents[2]


def test_i1_configurations_are_paired_and_trainable():
    naive = load_config(ROOT / "configs/selfplay/exp_i1_naive.yaml", repo=ROOT)
    pool = load_config(ROOT / "configs/selfplay/exp_i1_pool.yaml", repo=ROOT)
    assert naive["exp_id"] == pool["exp_id"] == "EXP-I1"
    assert naive["run_name"] == "naive"
    assert pool["run_name"] == "pool"
    assert naive["pool"]["current_probability"] == 1.0
    assert pool["pool"]["current_probability"] == 0.5
    assert naive["seeds"] == pool["seeds"] == [0, 1, 2]
    assert naive["generations"] == pool["generations"] == 8
    same_naive, same_pool = deepcopy(naive), deepcopy(pool)
    for config in (same_naive, same_pool):
        config.pop("run_name")
        config["pool"].pop("current_probability")
    assert same_naive == same_pool
    attacker_meta = yaml.safe_load(
        (ROOT / naive["attacker"]["initial_checkpoint"] / "meta.yaml").read_text()
    )
    defender_meta = yaml.safe_load(
        (ROOT / naive["defender"]["initial_checkpoint"] / "meta.yaml").read_text()
    )
    assert (
        naive["attacker"]["steps_per_iteration"] * naive["attacker"]["iterations_per_generation"]
        >= attacker_meta["train"]["agent_params"]["n_steps"]
    )
    assert (
        naive["defender"]["steps_per_generation"] * naive["generations"]
        > defender_meta["train"]["agent_params"]["learning_starts"]
    )
