"""F4-T05: a completed generation has two checkpoints and can be resumed."""

import copy
import json
from pathlib import Path

import pytest
import torch
import yaml

from wafarena.agents import build_agent, load_checkpoint, save_checkpoint
from wafarena.envs.attacker_env import N_ACTIONS as ATTACKER_ACTIONS
from wafarena.envs.attacker_obs import OBS_SIZE as ATTACKER_OBS
from wafarena.envs.backends.fake import FakeBackend
from wafarena.envs.defender_env import N_ACTIONS as DEFENDER_ACTIONS
from wafarena.envs.defender_env import OBS_SIZE as DEFENDER_OBS
from wafarena.selfplay.orchestrator import run_selfplay
from wafarena.selfplay.state import load_training_state

ROOT = Path(__file__).parents[2]
GOOD = yaml.safe_load((ROOT / "configs/selfplay/f4_t05_smoke.yaml").read_text())


def test_two_generation_smoke_and_resume(tmp_path):
    config = copy.deepcopy(GOOD)
    config["attacker"]["steps_per_iteration"] = 4
    config["defender"]["steps_per_generation"] = 4
    config["validation"]["attacker_episodes"] = 1
    config["validation"]["defender_sessions"] = 2
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
    assert (checkpoint_dir / "atk-gen-01" / "training_state.pt").is_file()
    assert (output / "gen-01" / "attacker" / "train.csv").is_file()
    assert [row["iteration"] for row in first["attacker_training"]] == [1, 2, 3]
    assert first["defender_training"]["steps"] == 4
    assert first["defender_training"]["current_opponent"] == str(checkpoint_dir / "atk-gen-01")
    assert first["defender_training"]["historical_opponents"] == ["checkpoints/refs/ATK-REF-1"]
    assert set(first["validation"]["attacker"]) == {
        "modsec-pl1",
        "modsec-pl2",
        "modsec-pl3",
        "modsec-pl4",
        "DEF-REF-1",
    }
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
    attacker = load_checkpoint(checkpoint_dir / "atk-gen-02")
    defender = load_checkpoint(checkpoint_dir / "def-gen-02")
    load_training_state(attacker, checkpoint_dir / "atk-gen-02")
    load_training_state(defender, checkpoint_dir / "def-gen-02")
    assert len(attacker._buffer) == 24
    assert defender._steps == 8
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


def test_resume_replays_only_interrupted_generation(tmp_path, monkeypatch):
    from wafarena.selfplay import orchestrator

    config = copy.deepcopy(GOOD)
    config["attacker"]["steps_per_iteration"] = 4
    config["defender"]["steps_per_generation"] = 4
    config["validation"]["attacker_episodes"] = 1
    config["validation"]["defender_sessions"] = 2
    options = {
        "results_root": tmp_path / "results",
        "checkpoint_root": tmp_path / "checkpoints",
        "repo": ROOT,
        "backend": FakeBackend(),
        "allow_dirty": True,
    }
    output = run_selfplay(config, **options, max_generations=1)[0]
    original = (output / "generation-01.json").read_bytes()
    evaluate = orchestrator.evaluate_generation

    def interrupt(*args, **kwargs):
        raise RuntimeError("interrupted during generation validation")

    monkeypatch.setattr(orchestrator, "evaluate_generation", interrupt)
    with pytest.raises(RuntimeError, match="interrupted"):
        run_selfplay(config, **options, resume=True)
    assert not (output / "generation-02.json").exists()
    monkeypatch.setattr(orchestrator, "evaluate_generation", evaluate)
    run_selfplay(config, **options, resume=True)
    assert (output / "generation-01.json").read_bytes() == original
    assert (output / "generation-02.json").is_file()


def test_resume_rejects_corrupt_completed_marker(tmp_path):
    config = copy.deepcopy(GOOD)
    config["attacker"]["steps_per_iteration"] = 4
    config["defender"]["steps_per_generation"] = 4
    config["validation"]["attacker_episodes"] = 1
    config["validation"]["defender_sessions"] = 2
    options = {
        "results_root": tmp_path / "results",
        "checkpoint_root": tmp_path / "checkpoints",
        "repo": ROOT,
        "backend": FakeBackend(),
        "allow_dirty": True,
    }
    output = run_selfplay(config, **options, max_generations=1)[0]
    (output / "generation-01.json").write_text("{}")
    with pytest.raises(ValueError, match="marker"):
        run_selfplay(config, **options, resume=True)


def test_resume_rejects_incomplete_validation_marker(tmp_path):
    config = copy.deepcopy(GOOD)
    config["attacker"]["steps_per_iteration"] = 4
    config["defender"]["steps_per_generation"] = 4
    config["validation"]["attacker_episodes"] = 1
    config["validation"]["defender_sessions"] = 2
    options = {
        "results_root": tmp_path / "results",
        "checkpoint_root": tmp_path / "checkpoints",
        "repo": ROOT,
        "backend": FakeBackend(),
        "allow_dirty": True,
    }
    output = run_selfplay(config, **options, max_generations=1)[0]
    marker = output / "generation-01.json"
    record = json.loads(marker.read_text())
    record["validation"]["attacker"].pop("modsec-pl4")
    marker.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="marker"):
        run_selfplay(config, **options, resume=True)


def test_two_generations_continue_learning_with_small_trainable_agents(tmp_path):
    attacker_params = {
        "method": "ppo",
        "hidden": [8],
        "n_steps": 4,
        "minibatch_size": 4,
        "update_epochs": 1,
        "threads": 1,
    }
    defender_params = {
        "hidden": [8],
        "buffer_size": 16,
        "batch_size": 2,
        "learning_starts": 2,
        "train_freq": 1,
        "target_update": 4,
        "threads": 1,
    }
    atk_path, def_path = tmp_path / "initial-atk", tmp_path / "initial-def"
    attacker = build_agent(
        "pg",
        attacker_params,
        obs_dim=ATTACKER_OBS,
        n_actions=ATTACKER_ACTIONS,
        seed=3,
        agent_id="initial-atk",
    )
    defender = build_agent(
        "dqn",
        defender_params,
        obs_dim=DEFENDER_OBS,
        n_actions=DEFENDER_ACTIONS,
        seed=3,
        agent_id="initial-def",
    )
    save_checkpoint(
        attacker,
        atk_path,
        algo="pg",
        obs_dim=ATTACKER_OBS,
        n_actions=ATTACKER_ACTIONS,
        train={"seed": 3, "agent_params": attacker_params},
    )
    save_checkpoint(
        defender,
        def_path,
        algo="dqn",
        obs_dim=DEFENDER_OBS,
        n_actions=DEFENDER_ACTIONS,
        train={"seed": 3, "agent_params": defender_params},
    )
    config = copy.deepcopy(GOOD)
    config["run_name"] = "trainable-smoke"
    config["attacker"]["initial_checkpoint"] = str(atk_path)
    config["defender"]["initial_checkpoint"] = str(def_path)
    config["attacker"]["steps_per_iteration"] = 4
    config["defender"]["steps_per_generation"] = 4
    config["validation"]["attacker_episodes"] = 1
    config["validation"]["defender_sessions"] = 2
    output = run_selfplay(
        config,
        results_root=tmp_path / "results",
        checkpoint_root=tmp_path / "checkpoints",
        repo=ROOT,
        backend=FakeBackend(),
        allow_dirty=True,
    )[0]
    run_id = json.loads((output / "generation-02.json").read_text())["run_id"]
    final = tmp_path / "checkpoints" / run_id
    learned_attacker = load_checkpoint(final / "atk-gen-02")
    learned_defender = load_checkpoint(final / "def-gen-02")
    assert any(
        not torch.allclose(before, after)
        for before, after in zip(
            attacker.actor.parameters(), learned_attacker.actor.parameters(), strict=True
        )
    )
    assert any(
        not torch.allclose(before, after)
        for before, after in zip(
            defender.q_net.parameters(), learned_defender.q_net.parameters(), strict=True
        )
    )
    load_training_state(learned_defender, final / "def-gen-02")
    assert learned_defender._steps == 8
