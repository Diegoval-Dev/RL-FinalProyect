"""EXP-I2 must pair all pool checkpoints within each source run."""

from pathlib import Path

import pytest
import yaml

from wafarena.eval.crossplay import discover_runs, load_config, pair_cells

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
