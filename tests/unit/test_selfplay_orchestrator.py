"""F4-T05: a completed generation has two checkpoints and can be resumed."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from wafarena.envs.backends.fake import FakeBackend
from wafarena.selfplay.orchestrator import run_selfplay

ROOT = Path(__file__).parents[2]
GOOD = yaml.safe_load((ROOT / "configs/selfplay/f4_t05_smoke.yaml").read_text())


def test_two_generation_smoke_and_resume(tmp_path):
    config = copy.deepcopy(GOOD)
    config["attacker"]["steps_per_iteration"] = 4
    config["defender"]["steps_per_generation"] = 4
    config["validation"]["attacker_episodes"] = 1
    config["validation"]["defender_sessions"] = 2
    config["validation"]["attacker_defenders"] = ["modsec-pl1", "DEF-REF-1"]
    config["validation"]["defender_attackers"] = ["corpus-replay", "ATK-REF-0"]
    output = run_selfplay(
        config,
        results_root=tmp_path / "results",
        checkpoint_root=tmp_path / "checkpoints",
        repo=ROOT,
        backend=FakeBackend(),
        allow_dirty=True,
        max_generations=1,
    )[0]
    first = json.loads((output / "generation-01.json").read_text())
    checkpoint_dir = tmp_path / "checkpoints" / first["run_id"]
    assert (checkpoint_dir / "atk-gen-01" / "meta.yaml").is_file()
    assert (checkpoint_dir / "def-gen-01" / "meta.yaml").is_file()
    assert (output / "gen-01" / "attacker" / "train.csv").is_file()
    assert [row["iteration"] for row in first["attacker_training"]] == [1, 2, 3]
    assert first["defender_training"]["steps"] == 4
    assert first["defender_training"]["current_opponent"] == str(checkpoint_dir / "atk-gen-01")
    assert first["defender_training"]["historical_opponents"] == ["checkpoints/refs/ATK-REF-1"]
    assert set(first["validation"]["attacker"]) == {"modsec-pl1", "DEF-REF-1"}
    first_bytes = (output / "generation-01.json").read_bytes()

    resumed = run_selfplay(
        config,
        results_root=tmp_path / "results",
        checkpoint_root=tmp_path / "checkpoints",
        repo=ROOT,
        backend=FakeBackend(),
        allow_dirty=True,
        resume=True,
    )[0]
    assert resumed == output
    assert (output / "generation-01.json").read_bytes() == first_bytes
    second = json.loads((output / "generation-02.json").read_text())
    assert (checkpoint_dir / "atk-gen-02" / "meta.yaml").is_file()
    assert (checkpoint_dir / "def-gen-02" / "meta.yaml").is_file()
    assert second["attacker_training"][0]["current_opponent"] == str(checkpoint_dir / "def-gen-01")
    assert second["defender_training"]["current_opponent"] == str(checkpoint_dir / "atk-gen-02")
    assert second["defender_training"]["historical_opponents"] == [
        "checkpoints/refs/ATK-REF-1",
        str(checkpoint_dir / "atk-gen-01"),
    ]


def test_resume_rejects_changed_config(tmp_path):
    config = copy.deepcopy(GOOD)
    config["attacker"]["steps_per_iteration"] = 4
    config["defender"]["steps_per_generation"] = 4
    config["validation"]["attacker_episodes"] = 1
    config["validation"]["defender_sessions"] = 2
    run_selfplay(
        config,
        results_root=tmp_path / "results",
        checkpoint_root=tmp_path / "checkpoints",
        repo=ROOT,
        backend=FakeBackend(),
        allow_dirty=True,
        max_generations=1,
    )
    changed = copy.deepcopy(config)
    changed["attacker"]["steps_per_iteration"] = 5
    with pytest.raises(ValueError, match="config"):
        run_selfplay(
            changed,
            results_root=tmp_path / "results",
            checkpoint_root=tmp_path / "checkpoints",
            repo=ROOT,
            backend=FakeBackend(),
            allow_dirty=True,
            resume=True,
        )
