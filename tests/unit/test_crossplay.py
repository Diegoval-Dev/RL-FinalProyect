"""EXP-I2 must pair all pool checkpoints within each source run."""

from pathlib import Path

import pytest
import yaml

from wafarena.agents.base import current_contract_versions
from wafarena.eval.crossplay import (
    aggregate_cells,
    discover_runs,
    evaluate_cell,
    load_config,
    pair_cells,
)
from wafarena.eval.metrics import EpisodeResult

CONFIG = {
    "exp_id": "EXP-I2",
    "run_name": "pool-crossplay",
    "source_exp_id": "EXP-I1",
    "source_condition": "pool",
    "source_seeds": [0, 1, 2],
    "generations": 8,
    "suite": "attacker-eval-v1",
    "backend": "fast",
}


def _checkpoint_run(root: Path, seed: int, sha: str = "abc1234") -> Path:
    run_id = f"EXP-I1__pool__s{seed}__{sha}"
    run = root / run_id
    for generation in range(1, 9):
        for prefix, role, weight in (
            ("atk", "attacker", "pg.pt"),
            ("def", "defender", "dqn.pt"),
        ):
            checkpoint = run / f"{prefix}-gen-{generation:02d}"
            checkpoint.mkdir(parents=True)
            (checkpoint / "meta.yaml").write_text(
                yaml.safe_dump(
                    {
                        "role": role,
                        "contract_versions": current_contract_versions(role),
                        "train": {
                            "exp_id": "EXP-I1",
                            "run_id": run_id,
                            "seed": seed,
                            "git_sha": sha,
                            "generation": generation,
                        },
                    }
                )
            )
            (checkpoint / weight).write_bytes(f"{run_id}/{role}/{generation}".encode())
            (checkpoint / "training_state.pt").touch()
    return run


def test_discovers_three_complete_pool_runs_and_192_same_seed_pairs(tmp_path):
    runs = [_checkpoint_run(tmp_path, seed) for seed in range(3)]
    discovered = discover_runs(runs[1], CONFIG)
    assert [run.seed for run in discovered] == [0, 1, 2]
    assert [run.source_run_id for run in discovered] == [path.name for path in runs]
    pairs = pair_cells(discovered)
    assert len(pairs) == 192
    assert len({(p.seed, p.defender_generation, p.attacker_generation) for p in pairs}) == 192
    assert all(p.attacker_checkpoint.parent == p.defender_checkpoint.parent for p in pairs)
    assert {(p.defender_generation, p.attacker_generation) for p in pairs if p.seed == 0} == {
        (i, j) for i in range(1, 9) for j in range(1, 9)
    }


def test_discovery_rejects_missing_seed_and_mismatched_checkpoint_metadata(tmp_path):
    first = _checkpoint_run(tmp_path, 0)
    _checkpoint_run(tmp_path, 1)
    with pytest.raises(ValueError, match="missing.*s2"):
        discover_runs(first, CONFIG)
    third = _checkpoint_run(tmp_path, 2)
    meta_path = third / "atk-gen-03/meta.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["train"]["seed"] = 1
    meta_path.write_text(yaml.safe_dump(meta))
    with pytest.raises(ValueError, match="checkpoint provenance"):
        discover_runs(first, CONFIG)


def test_discovery_rejects_incompatible_contract(tmp_path):
    runs = [_checkpoint_run(tmp_path, seed) for seed in range(3)]
    meta_path = runs[2] / "def-gen-08/meta.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["contract_versions"]["env_defender"] = "99.0"
    meta_path.write_text(yaml.safe_dump(meta))
    with pytest.raises(ValueError, match="contract"):
        discover_runs(runs[0], CONFIG)


def test_config_requires_full_test_suite_and_three_seeds(tmp_path):
    path = tmp_path / "crossplay.yaml"
    path.write_text(yaml.safe_dump(CONFIG))
    assert load_config(path)["source_seeds"] == [0, 1, 2]
    bad = dict(CONFIG, suite="attacker-val-v1")
    path.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match="attacker-eval-v1"):
        load_config(path)
    bad = dict(CONFIG, source_seeds=[0])
    path.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match="source_seeds"):
        load_config(path)


def test_cell_evaluates_fixed_suite_and_rejects_stale_cache(tmp_path, monkeypatch):
    from wafarena.eval import crossplay

    runs = [_checkpoint_run(tmp_path, seed) for seed in range(3)]
    pair = pair_cells(discover_runs(runs[0], CONFIG))[0]
    cell = tmp_path / "output/def-01_atk-01.json"
    monkeypatch.setattr(crossplay, "load_checkpoint", lambda path: Path(path))
    calls = []

    def fake_suite(agent, suite, *, defender, backend):
        calls.append((agent, suite, defender, backend))
        return [
            EpisodeResult(seed, "base", "family", seed < 1002, False, 1, 0, 0, "payload")
            for seed in range(1000, 1200)
        ]

    monkeypatch.setattr(crossplay.harness, "run_attacker_suite", fake_suite)
    row = evaluate_cell(
        pair, CONFIG, cell, "EXP-I2__pool-crossplay__s0__def5678", "def5678", object()
    )
    assert (row["episodes"], row["evasions"], row["evasion_rate"]) == (200, 2, 0.01)
    assert row["split"] == "test"
    assert calls[0][0] == pair.attacker_checkpoint
    assert calls[0][1] == "attacker-eval-v1"
    assert calls[0][2] == {"type": "checkpoint", "path": str(pair.defender_checkpoint)}
    assert cell.is_file()
    assert evaluate_cell(pair, CONFIG, cell, row["eval_run_id"], "def5678", object()) == row
    assert len(calls) == 1
    (pair.attacker_checkpoint / "pg.pt").write_bytes(b"changed weights")
    with pytest.raises(ValueError, match="stale.*cell"):
        evaluate_cell(pair, CONFIG, cell, row["eval_run_id"], "def5678", object())


def test_cell_rejects_incomplete_suite(tmp_path, monkeypatch):
    from wafarena.eval import crossplay

    runs = [_checkpoint_run(tmp_path, seed) for seed in range(3)]
    pair = pair_cells(discover_runs(runs[0], CONFIG))[0]
    monkeypatch.setattr(crossplay, "load_checkpoint", lambda path: Path(path))
    monkeypatch.setattr(
        crossplay.harness,
        "run_attacker_suite",
        lambda *args, **kwargs: [
            EpisodeResult(seed, "base", "family", False, False, 1, 0, 0, "payload")
            for seed in range(1000, 1199)
        ],
    )
    with pytest.raises(ValueError, match="200 episodes"):
        evaluate_cell(
            pair,
            CONFIG,
            tmp_path / "cell.json",
            "EXP-I2__pool-crossplay__s0__def5678",
            "def5678",
            object(),
        )


def test_aggregate_requires_all_three_seed_values_for_every_pair():
    rows = [
        {
            "seed": seed,
            "defender_generation": defender,
            "attacker_generation": attacker,
            "episodes": 200,
            "evasions": 20 * seed if (defender, attacker) == (1, 1) else 0,
            "evasion_rate": 0.1 * seed if (defender, attacker) == (1, 1) else 0.0,
            "source_git_sha": "abc1234",
            "eval_git_sha": "def5678",
        }
        for seed in range(3)
        for defender in range(1, 9)
        for attacker in range(1, 9)
    ]
    matrix = aggregate_cells(rows, CONFIG)
    assert len(matrix) == 64
    first = next(
        x for x in matrix if (x["defender_generation"], x["attacker_generation"]) == (1, 1)
    )
    assert first["mean_er"] == pytest.approx(0.1)
    assert first["n_seeds"] == 3
    assert first["episodes_total"] == 600
    assert first["ci_low"] <= first["mean_er"] <= first["ci_high"]
    with pytest.raises(ValueError, match="192"):
        aggregate_cells(rows[:-1], CONFIG)
    with pytest.raises(ValueError, match="duplicate"):
        aggregate_cells([*rows[:-1], rows[0]], CONFIG)
