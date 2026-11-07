"""Generation-boundary self-play over the existing Gym environments and checkpoints."""

import json
import math
import os
import shutil
import time
from pathlib import Path

import yaml

from wafarena import runmeta
from wafarena.agents import load_checkpoint, save_checkpoint
from wafarena.envs.attacker_env import N_ACTIONS as ATTACKER_ACTIONS
from wafarena.envs.attacker_obs import OBS_SIZE as ATTACKER_OBS
from wafarena.envs.defender_env import N_ACTIONS as DEFENDER_ACTIONS
from wafarena.envs.defender_env import OBS_SIZE as DEFENDER_OBS
from wafarena.envs.defender_env import DefenderEnv
from wafarena.envs.resolve import resolve_backend
from wafarena.selfplay.config import validate_config
from wafarena.selfplay.evaluation import evaluate_generation
from wafarena.selfplay.pool import PoolAttackerEnv
from wafarena.selfplay.state import load_training_state, save_training_state
from wafarena.trainer import DefenderEpisode, train

PROJECT_ROOT = Path(__file__).parents[2]
RESULTS_ROOT = PROJECT_ROOT / "results"
CHECKPOINT_ROOT = PROJECT_ROOT / "checkpoints/selfplay"


def _json_ready(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _checkpoint_info(path: str | Path) -> dict:
    return yaml.safe_load((Path(path) / "meta.yaml").read_text())


def _opponents(config: dict, checkpoint_dir: Path, generation: int, role: str):
    initial = config[role]["initial_checkpoint"]
    prefix = "atk" if role == "attacker" else "def"
    if generation == 1:
        return initial, []
    current = str(checkpoint_dir / f"{prefix}-gen-{generation - 1:02d}")
    history = [initial] + [
        str(checkpoint_dir / f"{prefix}-gen-{i:02d}") for i in range(1, generation - 1)
    ]
    return current, history


def _save_agent(agent, path: Path, source: str, config: dict, meta: dict, generation: int) -> None:
    source_meta = _checkpoint_info(source)
    is_attacker = agent.role == "attacker"
    save_checkpoint(
        agent,
        path,
        algo=source_meta["algo"],
        obs_dim=ATTACKER_OBS if is_attacker else DEFENDER_OBS,
        n_actions=ATTACKER_ACTIONS if is_attacker else DEFENDER_ACTIONS,
        train={
            "exp_id": config["exp_id"],
            "run_id": meta["run_id"],
            "seed": meta["seed"],
            "git_sha": meta["git_sha"],
            "generation": generation,
            "source_checkpoint": source,
            "agent_params": source_meta["train"]["agent_params"],
        },
    )
    save_training_state(agent, path)


def _completed_generation(
    run_dir: Path, checkpoint_dir: Path, count: int, run_id: str, config: dict
) -> int:
    completed = 0
    for generation in range(1, count + 1):
        marker = run_dir / f"generation-{generation:02d}.json"
        if not marker.exists():
            break
        record = json.loads(marker.read_text())
        validation = record.get("validation")
        if (
            record.get("run_id") != run_id
            or record.get("generation") != generation
            or not isinstance(validation, dict)
            or set(validation) != {"split", "attacker", "defender"}
            or validation["split"] != "val"
            or not isinstance(validation["attacker"], dict)
            or not isinstance(validation["defender"], dict)
            or set(validation["attacker"]) != set(config["validation"]["attacker_defenders"])
            or set(validation["defender"]) != set(config["validation"]["defender_attackers"])
        ):
            raise ValueError(f"completed generation {generation} has an invalid marker")
        for role in ("atk", "def"):
            path = checkpoint_dir / f"{role}-gen-{generation:02d}"
            if not (path / "meta.yaml").is_file() or not (path / "training_state.pt").is_file():
                raise ValueError(
                    f"completed generation {generation} is missing its {role} checkpoint"
                )
            agent = load_checkpoint(path)
            load_training_state(agent, path)
        completed = generation
    markers = list(run_dir.glob("generation-*.json"))
    if len(markers) != completed:
        raise ValueError("self-play generation markers are not contiguous")
    return completed


def _prepare_run(config, seed, results_root, checkpoint_root, repo, allow_dirty, resume):
    run_dir = runmeta.run_dir(results_root, config["exp_id"], config["run_name"], seed)
    config_path = run_dir / "config.resolved.yaml"
    meta_path = run_dir / "meta.yaml"
    if resume:
        if not meta_path.is_file() or not config_path.is_file():
            raise ValueError(f"cannot resume missing self-play run {run_dir}")
        if yaml.safe_load(config_path.read_text()) != config:
            raise ValueError("self-play config changed since the run began")
        meta = yaml.safe_load(meta_path.read_text())
        if meta["git_sha"] != runmeta.git_info(repo).sha:
            raise ValueError("self-play code revision changed since the run began")
    else:
        if run_dir.exists():
            raise FileExistsError(f"self-play run already exists: {run_dir}; use --resume")
        meta = runmeta.build_meta(config, seed=seed, repo=repo, allow_dirty=allow_dirty)
        runmeta.write_meta(run_dir, meta)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    return run_dir, Path(checkpoint_root) / meta["run_id"], meta


def _run_generation(config, generation, seed, run_dir, checkpoint_dir, meta, backend):
    attacker_source, historical_attackers = _opponents(
        config, checkpoint_dir, generation, "attacker"
    )
    defender_source, historical_defenders = _opponents(
        config, checkpoint_dir, generation, "defender"
    )
    attacker = load_checkpoint(attacker_source)
    defender = load_checkpoint(defender_source)
    if generation > 1:
        load_training_state(attacker, attacker_source)
        load_training_state(defender, defender_source)
    probability = config["pool"]["current_probability"]
    env = PoolAttackerEnv(
        backend,
        current_defender=defender_source,
        historical_defenders=historical_defenders,
        current_probability=probability,
        **config["attacker"]["env"],
    )
    train_dir = run_dir / f"gen-{generation:02d}"
    attacker_training = []

    def record_attacker_iteration(step: int) -> None:
        attacker_training.append(
            {
                "iteration": step // steps,
                "steps": steps,
                "current_opponent": defender_source,
                "historical_opponents": historical_defenders,
            }
        )

    steps = config["attacker"]["steps_per_iteration"]
    train(
        attacker,
        env,
        total_steps=steps * config["attacker"]["iterations_per_generation"],
        seed=seed + 10_000 * generation + 1,
        out_dir=train_dir / "attacker",
        eval_every=steps,
        on_eval=record_attacker_iteration,
        tensorboard=config["logging"]["tensorboard"],
    )

    stage = checkpoint_dir / f".gen-{generation:02d}.incomplete"
    current_attacker = stage / "atk"
    _save_agent(attacker, current_attacker, attacker_source, config, meta, generation)
    historical_attackers = [*historical_attackers, attacker_source]
    defender_env = DefenderEnv(
        backend,
        attacker={
            "type": "pool",
            "paths": [str(current_attacker), *historical_attackers],
            "weights": [probability]
            + ([(1.0 - probability) / len(historical_attackers) for _ in historical_attackers]),
        },
        **config["defender"]["env"],
    )
    defender_steps = config["defender"]["steps_per_generation"]
    train(
        defender,
        defender_env,
        total_steps=defender_steps,
        seed=seed + 10_000 * generation + 100,
        out_dir=train_dir / "defender",
        eval_every=defender_steps,
        tensorboard=config["logging"]["tensorboard"],
        episode_stats=DefenderEpisode,
    )

    validation = evaluate_generation(current_attacker, defender, backend, **config["validation"])
    _save_agent(defender, stage / "def", defender_source, config, meta, generation)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    for name in ("atk", "def"):
        os.replace(stage / name, checkpoint_dir / f"{name}-gen-{generation:02d}")
    stage.rmdir()
    record = {
        "run_id": meta["run_id"],
        "generation": generation,
        "attacker_training": attacker_training,
        "defender_training": {
            "steps": defender_steps,
            "current_opponent": str(checkpoint_dir / f"atk-gen-{generation:02d}"),
            "historical_opponents": historical_attackers,
        },
        "validation": validation,
    }
    marker = run_dir / f"generation-{generation:02d}.json"
    temporary = marker.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(_json_ready(record), indent=2, sort_keys=True) + "\n")
    os.replace(temporary, marker)


def run_selfplay(
    config: dict,
    *,
    results_root: Path = RESULTS_ROOT,
    checkpoint_root: Path = CHECKPOINT_ROOT,
    repo: Path = PROJECT_ROOT,
    allow_dirty: bool = False,
    resume: bool = False,
    backend=None,
    max_generations: int | None = None,
) -> list[Path]:
    """Train all configured seeds; resume only at completed generation boundaries."""
    config = validate_config(config, repo=repo)
    runmeta.ensure_clean(repo, allow_dirty=allow_dirty)
    if max_generations is not None and not 1 <= max_generations <= config["generations"]:
        raise ValueError("max_generations must be within the configured run")
    owns_backend = backend is None
    backend = backend or resolve_backend(config["backend"])
    outputs = []
    try:
        for seed in config["seeds"]:
            run_dir, checkpoint_dir, meta = _prepare_run(
                config, seed, results_root, checkpoint_root, repo, allow_dirty, resume
            )
            start = time.monotonic()
            completed = _completed_generation(
                run_dir, checkpoint_dir, config["generations"], meta["run_id"], config
            )
            limit = max_generations or config["generations"]
            for generation in range(completed + 1, limit + 1):
                stage = checkpoint_dir / f".gen-{generation:02d}.incomplete"
                if stage.exists():
                    shutil.rmtree(stage)
                for name in ("atk", "def"):
                    stale = checkpoint_dir / f"{name}-gen-{generation:02d}"
                    if stale.exists():
                        shutil.rmtree(stale)
                _run_generation(config, generation, seed, run_dir, checkpoint_dir, meta, backend)
            if limit == config["generations"] and "duration_s" not in yaml.safe_load(
                (run_dir / "meta.yaml").read_text()
            ):
                runmeta.finalize_meta(run_dir, duration_s=round(time.monotonic() - start, 3))
            outputs.append(run_dir)
    finally:
        if owns_backend:
            backend.close()
    return outputs
