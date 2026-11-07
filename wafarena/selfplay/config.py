"""Validation for generation-based self-play configs."""

from pathlib import Path

import yaml


class SelfPlayConfigError(ValueError):
    """An incomplete or unsafe self-play protocol."""


ATTACKER_DEFENDERS = {"modsec-pl1", "modsec-pl2", "modsec-pl3", "modsec-pl4", "DEF-REF-1"}
DEFENDER_ATTACKERS = {"corpus-replay", "random-mutation", "ATK-REF-0", "ATK-REF-1"}


def _positive(value, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise SelfPlayConfigError(f"{name} must be a positive integer")


def _safe_name(value) -> bool:
    return (
        isinstance(value, str) and bool(value) and value.replace("-", "").replace("_", "").isalnum()
    )


def validate_config(raw: dict, *, repo: Path = Path(".")) -> dict:
    """Check the full protocol before the runner creates any output."""
    try:
        if not _safe_name(raw["exp_id"]) or not _safe_name(raw["run_name"]):
            raise SelfPlayConfigError("exp_id and run_name must be safe nonempty names")
        seeds = raw["seeds"]
        if (
            not isinstance(seeds, list)
            or not seeds
            or any(type(s) is not int or s < 0 for s in seeds)
        ):
            raise SelfPlayConfigError("seeds must be non-negative integers")
        if len(set(seeds)) != len(seeds):
            raise SelfPlayConfigError("seeds must be unique")
        if raw["backend"] != "fast":
            raise SelfPlayConfigError("F4-T05 self-play uses the fast backend")
        _positive(raw["generations"], "generations")
        attacker, defender = raw["attacker"], raw["defender"]
        if attacker["iterations_per_generation"] != 3:
            raise SelfPlayConfigError("attacker_iterations must be 3 per defender iteration")
        _positive(attacker["steps_per_iteration"], "attacker steps")
        _positive(defender["steps_per_generation"], "defender steps")
        for name, section in (("attacker", attacker), ("defender", defender)):
            if section["env"]["split"] != "train":
                raise SelfPlayConfigError(f"{name} must train only on the train split")
            path = repo / section["initial_checkpoint"]
            if not (path / "meta.yaml").is_file():
                raise SelfPlayConfigError(f"{name} initial checkpoint missing: {path}")
            checkpoint_meta = yaml.safe_load((path / "meta.yaml").read_text())
            if checkpoint_meta.get("role") != name:
                raise SelfPlayConfigError(f"{name} initial checkpoint has wrong role: {path}")
        probability = raw["pool"]["current_probability"]
        if type(probability) not in (int, float) or not 0 <= probability <= 1:
            raise SelfPlayConfigError("current_probability must be a probability in [0, 1]")
        if not 0 < defender["env"]["attack_ratio"] <= 1:
            raise SelfPlayConfigError("defender attack_ratio must be in (0, 1]")
        for key in ("attacker_episodes", "defender_sessions"):
            _positive(raw["validation"][key], key)
        for key in ("attacker_defenders", "defender_attackers"):
            if not raw["validation"][key] or not all(
                isinstance(item, str) and item for item in raw["validation"][key]
            ):
                raise SelfPlayConfigError(f"validation.{key} must be a nonempty list of names")
            if len(set(raw["validation"][key])) != len(raw["validation"][key]):
                raise SelfPlayConfigError(f"validation.{key} must not repeat references")
        if set(raw["validation"]["attacker_defenders"]) != ATTACKER_DEFENDERS:
            raise SelfPlayConfigError("validation must include all fixed attacker defenders")
        if set(raw["validation"]["defender_attackers"]) != DEFENDER_ATTACKERS:
            raise SelfPlayConfigError("validation must include all fixed defender attackers")
        if type(raw["logging"]["tensorboard"]) is not bool:
            raise SelfPlayConfigError("logging.tensorboard must be boolean")
    except (KeyError, TypeError, AttributeError) as exc:
        raise SelfPlayConfigError(f"missing or malformed self-play config: {exc}") from exc
    return raw


def load_config(path: Path, *, repo: Path = Path(".")) -> dict:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise SelfPlayConfigError("self-play config must be a mapping")
    return validate_config(raw, repo=repo)
