"""Collect public SEND responses and score the Phase 4 surrogate on held-out val data."""

import csv
import time
from pathlib import Path

import numpy as np
import yaml

from wafarena import runmeta
from wafarena.agents.dyna.surrogate import SurrogateModel, calibration_metrics
from wafarena.envs.attacker_env import N_ACTIONS, SEND_ACTION, AttackerEnv
from wafarena.envs.attacker_obs import NGRAM_SIZE
from wafarena.envs.backends import make_backend
from wafarena.envs.backends.base import Backend
from wafarena.envs.resolve import resolve_defender


def collect_send_examples(
    backend: Backend, defender, *, split: str, episodes: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Collect (pre-SEND ngrams, public response) using seeded random actions."""
    if split not in ("train", "val"):
        raise ValueError("split must be train or val")
    if episodes <= 0:
        raise ValueError("episodes must be positive")
    env = AttackerEnv(backend, defender=defender, split=split)
    rng = np.random.default_rng(seed)
    examples: list[np.ndarray] = []
    responses: list[int] = []
    for episode in range(episodes):
        obs, _info = env.reset(seed=seed + episode)
        done = False
        while not done:
            action = int(rng.integers(N_ACTIONS))
            before = obs[:NGRAM_SIZE].copy() if action == SEND_ACTION else None
            obs, _reward, terminated, truncated, info = env.step(action)
            if before is not None:
                examples.append(before)
                responses.append(int(info["response"]))
            done = terminated or truncated
    env.close()
    if not examples:
        raise ValueError("no SEND examples collected")
    return np.stack(examples), np.asarray(responses, dtype=np.int64)


def _class_counts(labels: np.ndarray) -> str:
    classes, counts = np.unique(labels, return_counts=True)
    return " ".join(
        f"{int(label)}:{int(count)}" for label, count in zip(classes, counts, strict=True)
    )


def evaluate_variants(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    *,
    variants: list[dict],
    epochs: int,
    seed: int,
    defender: str,
    run_id: str,
    git_sha: str,
) -> list[dict]:
    """Fit each configured variant on train SENDs and score only on val SENDs."""
    if not len(train_y) or not len(val_y):
        raise ValueError("empty train or validation set")
    if epochs <= 0:
        raise ValueError("epochs must be positive")
    rows = []
    for variant in variants:
        model = SurrogateModel(
            hidden_dim=variant["hidden_dim"], learning_rate=variant["learning_rate"], seed=seed
        )
        for _ in range(epochs):
            for obs, response in zip(train_x, train_y, strict=True):
                model.update(obs, response)
        probabilities = np.stack([model.predict_proba(obs) for obs in val_x])
        rows.append(
            {
                "run_id": run_id,
                "git_sha": git_sha,
                "seed": seed,
                "defender": defender,
                "variant": variant["name"],
                "split": "val",
                "train_samples": len(train_y),
                "val_samples": len(val_y),
                "train_class_counts": _class_counts(train_y),
                "val_class_counts": _class_counts(val_y),
                **calibration_metrics(probabilities, val_y),
            }
        )
    return rows


def write_validation_csv(path: Path, rows: list[dict]) -> None:
    """Write validation rows with one stable column order."""
    if not rows:
        raise ValueError("empty validation rows")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate_surrogate(
    config_path: Path, *, results_root: Path, repo: Path = Path("."), backend: Backend | None = None
) -> Path:
    """Run the configured train/val diagnostic and return its raw result directory."""
    config = yaml.safe_load(Path(config_path).read_text())
    runmeta.ensure_clean(repo, allow_dirty=False)
    seed = int(config["seed"])
    directory = runmeta.run_dir(results_root, config["exp_id"], config["run_name"], seed)
    if (directory / runmeta.META_FILE).exists():
        raise FileExistsError(f"surrogate run already exists: {directory}")
    meta = runmeta.build_meta(config, seed=seed, repo=repo, allow_dirty=False)
    runmeta.write_meta(directory, meta)
    (directory / "config.resolved.yaml").write_text(yaml.safe_dump(config, sort_keys=False))

    started = time.monotonic()
    active_backend = backend if backend is not None else make_backend(config.get("backend", "fast"))
    rows: list[dict] = []
    try:
        for name, spec in config["defenders"].items():
            defender = resolve_defender(spec)
            train_x, train_y = collect_send_examples(
                active_backend,
                defender,
                split="train",
                episodes=int(config["train_episodes"]),
                seed=seed,
            )
            val_x, val_y = collect_send_examples(
                active_backend,
                defender,
                split="val",
                episodes=int(config["val_episodes"]),
                seed=seed + 10_000,
            )
            rows.extend(
                evaluate_variants(
                    train_x,
                    train_y,
                    val_x,
                    val_y,
                    variants=config["variants"],
                    epochs=int(config["epochs"]),
                    seed=seed,
                    defender=name,
                    run_id=meta["run_id"],
                    git_sha=meta["git_sha"],
                )
            )
    finally:
        active_backend.close()
    write_validation_csv(directory / "validation.csv", rows)
    runmeta.finalize_meta(directory, duration_s=time.monotonic() - started)
    return directory
