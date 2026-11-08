"""EXP-I1 reporting rejects incomplete evidence and keeps paired seed values."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from wafarena.selfplay.report import (
    aggregate_fixed,
    collect_fixed,
    evaluate_history,
    historical_pairs,
)

ROOT = Path(__file__).parents[2]
BASE = yaml.safe_load((ROOT / "configs/selfplay/exp_i1_pool.yaml").read_text())


def _write_run(root, checkpoints, config, seed, sha, *, generations=2):
    run = root / "EXP-I1" / config["run_name"] / f"s{seed}"
    run.mkdir(parents=True)
    run_id = f"EXP-I1__{config['run_name']}__s{seed}__{sha}"
    meta = {
        "run_id": run_id,
        "exp_id": "EXP-I1",
        "run_name": config["run_name"],
        "seed": seed,
        "git_sha": sha,
        "dirty": False,
    }
    (run / "meta.yaml").write_text(yaml.safe_dump(meta))
    resolved = deepcopy(config)
    resolved["seeds"] = [seed]
    (run / "config.resolved.yaml").write_text(yaml.safe_dump(resolved))
    for generation in range(1, generations + 1):
        for role, weight in (("atk", "pg.pt"), ("def", "dqn.pt")):
            path = checkpoints / run_id / f"{role}-gen-{generation:02d}"
            path.mkdir(parents=True)
            checkpoint_meta = {
                "role": "attacker" if role == "atk" else "defender",
                "train": {
                    "run_id": run_id,
                    "seed": seed,
                    "git_sha": sha,
                    "generation": generation,
                },
            }
            (path / "meta.yaml").write_text(yaml.safe_dump(checkpoint_meta))
            (path / weight).write_bytes(b"checkpoint")
            (path / "training_state.pt").touch()
        record = {
            "run_id": run_id,
            "generation": generation,
            "validation": {
                "split": "val",
                "attacker": {
                    name: {"evasion_rate": 0.0, "episodes": 40}
                    for name in config["validation"]["attacker_defenders"]
                },
                "defender": {
                    name: {
                        "tpr": 0.8 + seed * 0.05,
                        "fpr": 0.0,
                        "attack_requests": 20,
                        "requests": 40,
                        "sessions": config["validation"]["defender_sessions"],
                        "empty_attack_attempts": 0,
                    }
                    for name in config["validation"]["defender_attackers"]
                },
            },
        }
        (run / f"generation-{generation:02d}.json").write_text(json.dumps(record))
    return run


def test_collect_fixed_requires_all_generations_and_matching_code(tmp_path):
    configs = {name: deepcopy(BASE) for name in ("naive", "pool")}
    for name, config in configs.items():
        config["run_name"] = name
        config["generations"] = 2
        config["seeds"] = [0, 1, 2]
        config["pool"]["current_probability"] = 1.0 if name == "naive" else 0.5
    root, checkpoints = tmp_path / "results", tmp_path / "checkpoints"
    for config in configs.values():
        for seed in (0, 1, 2):
            _write_run(root, checkpoints, config, seed, "abc1234")
    fixed, runs, sha = collect_fixed(root, checkpoints, configs)
    assert sha == "abc1234"
    assert len(runs) == 6
    assert len(fixed) == 6 * 2 * (5 * 2 + 4 * 3)
    curve = aggregate_fixed(fixed)
    row = next(
        r
        for r in curve
        if r["condition"] == "pool"
        and r["generation"] == 1
        and r["reference"] == "ATK-REF-1"
        and r["metric"] == "tpr"
    )
    assert row["mean"] == pytest.approx(0.85)
    assert row["n_seeds"] == 3
    assert row["ci_low"] <= row["mean"] <= row["ci_high"]
    assert len(historical_pairs(runs)) == 6

    (root / "EXP-I1/pool/s2/generation-02.json").unlink()
    with pytest.raises(ValueError, match="generation"):
        collect_fixed(root, checkpoints, configs)


def test_collect_fixed_rejects_mixed_sha_and_dirty_runs(tmp_path):
    config = deepcopy(BASE)
    config["seeds"] = [0, 1]
    config["generations"] = 2
    root, checkpoints = tmp_path / "results", tmp_path / "checkpoints"
    _write_run(root, checkpoints, config, 0, "abc1234")
    run = _write_run(root, checkpoints, config, 1, "def5678")
    with pytest.raises(ValueError, match="SHA"):
        collect_fixed(root, checkpoints, {"pool": config})
    meta = yaml.safe_load((run / "meta.yaml").read_text())
    meta["git_sha"] = "abc1234"
    (run / "meta.yaml").write_text(yaml.safe_dump(meta))
    meta["dirty"] = True
    (run / "meta.yaml").write_text(yaml.safe_dump(meta))
    with pytest.raises(ValueError, match="dirty"):
        collect_fixed(root, checkpoints, {"pool": config})


def test_collect_fixed_rejects_partial_validation_and_wrong_checkpoint(tmp_path):
    config = deepcopy(BASE)
    config["seeds"] = [0]
    config["generations"] = 2
    root, checkpoints = tmp_path / "results", tmp_path / "checkpoints"
    run = _write_run(root, checkpoints, config, 0, "abc1234")
    marker = run / "generation-01.json"
    record = json.loads(marker.read_text())
    record["validation"]["attacker"]["DEF-REF-1"]["episodes"] = 1
    marker.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="episodes"):
        collect_fixed(root, checkpoints, {"pool": config})
    record["validation"]["attacker"]["DEF-REF-1"]["episodes"] = 40
    record["validation"]["defender"]["ATK-REF-1"]["sessions"] = 1
    marker.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="sessions"):
        collect_fixed(root, checkpoints, {"pool": config})
    record["validation"]["defender"]["ATK-REF-1"]["sessions"] = 40
    marker.write_text(json.dumps(record))
    checkpoint = checkpoints / "EXP-I1__pool__s0__abc1234" / "def-gen-01/meta.yaml"
    meta = yaml.safe_load(checkpoint.read_text())
    meta["train"]["seed"] = 99
    checkpoint.write_text(yaml.safe_dump(meta))
    with pytest.raises(ValueError, match="checkpoint provenance"):
        collect_fixed(root, checkpoints, {"pool": config})


def test_historical_evaluation_uses_earlier_same_run_attacker_and_caches(tmp_path, monkeypatch):
    from wafarena.eval.metrics import RequestRecord
    from wafarena.selfplay import report

    config = deepcopy(BASE)
    config["seeds"] = [0]
    config["generations"] = 3
    root, checkpoints = tmp_path / "results", tmp_path / "checkpoints"
    _write_run(root, checkpoints, config, 0, "abc1234", generations=3)
    _, runs, _ = collect_fixed(root, checkpoints, {"pool": config})
    seen = []

    def fake_environment(backend, *, attacker, split, attack_split):
        assert split == attack_split == "val"
        seen.append(attacker["path"])
        return type("FakeEnvironment", (), {"empty_attack_attempts": 0})()

    monkeypatch.setattr(report, "DefenderEnv", fake_environment)
    monkeypatch.setattr(report, "load_checkpoint", lambda path: object())
    monkeypatch.setattr(
        report.harness,
        "_play_session",
        lambda defender, env, item: [
            RequestRecord(
                is_attack=item.is_attack,
                action=1,
                effect=False,
                session_id=str(item.seed),
                q_allow=0.0,
            )
        ],
    )
    first = evaluate_history(runs, root, backend=object())
    assert len(first) == 3
    assert [Path(path).name for path in seen] == ["atk-gen-01", "atk-gen-01", "atk-gen-02"]
    assert all(row["split"] == "val" and row["tpr"] == 1.0 for row in first)
    second = evaluate_history(runs, root, backend=object())
    assert second == first
    assert len(seen) == 3
    cell = root / "_history_cells/pool/s0/def-02_atk-01.json"
    record = json.loads(cell.read_text())
    record["split"] = "train"
    cell.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="historical cell"):
        evaluate_history(runs, root, backend=object())
    record["split"] = "val"
    cell.write_text(json.dumps(record))
    record["er_d"] = 2.0
    cell.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="historical cell"):
        evaluate_history(runs, root, backend=object())
    record["er_d"] = first[0]["er_d"]
    cell.write_text(json.dumps(record))
    attacker_weight = checkpoints / "EXP-I1__pool__s0__abc1234/atk-gen-01/pg.pt"
    attacker_weight.write_bytes(b"different checkpoint")
    with pytest.raises(ValueError, match="historical cell"):
        evaluate_history(runs, root, backend=object())
