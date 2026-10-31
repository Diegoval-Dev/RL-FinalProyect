"""Experiment YAML: validation and default expansion (experimentos.md)."""

import copy
import re
from pathlib import Path
from typing import Any

import yaml

from wafarena.eval.harness import ATTACKER_SUITES, DEFENDER_SUITES

CATALOG_PATH = Path(__file__).parents[1] / "docs" / "07-experimentos" / "catalogo.md"
ENVIRONMENTS = ("WafArena/Attacker-v0", "WafArena/AttackerBandit-v0", "WafArena/Defender-v0")
BACKENDS = ("fast", "real")
TRAIN_SPLIT = "train"
RUN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SUITES_BY_ENV = {
    "WafArena/Attacker-v0": ATTACKER_SUITES,
    "WafArena/AttackerBandit-v0": ATTACKER_SUITES,  # bandits deploy their policy on Attacker-v0
    "WafArena/Defender-v0": DEFENDER_SUITES,
}
DEFAULT_SUITE = {
    "WafArena/Attacker-v0": "attacker-eval-v1",
    "WafArena/AttackerBandit-v0": "attacker-eval-v1",
    "WafArena/Defender-v0": "defender-eval-v1",
}

DEFAULTS: dict[str, Any] = {
    "owner": None,
    "rq": [],
    "env": {
        "backend": "fast",
        "split": TRAIN_SPLIT,
        "defender": {"type": "modsec", "paranoia_level": 1},
        "query_budget": 50,
    },
    "agent": {"params": {}},
    "eval": {"every_steps": 10000, "final": True},
    "logging": {"tensorboard": True, "wandb": False},
    "checkpoint": {"save_best_on": "val"},
}
REQUIRED = ("exp_id", "run_name", "seeds", "env", "agent", "train")
SECTION_KEYS = {
    "env": {
        "id",
        "backend",
        "split",
        "defender",
        "attacker",
        "query_budget",
        "ban_threshold",
        "max_steps",
        "families",
        "switch_at",
        "switch_defender",
        "attack_ratio",
        "reward",
        "benign_abandon_prob",
    },
    "agent": {"algo", "params"},
    "train": {"total_steps"},
    "eval": {"suites", "every_steps", "final", "surrogate_val_episodes"},
    "logging": {"tensorboard", "wandb"},
    "checkpoint": {"save_best_on"},
}
TOP_LEVEL_KEYS = {"exp_id", "run_name", "owner", "rq", "seeds", *SECTION_KEYS}


class ConfigError(ValueError):
    """The experiment YAML breaks the contract."""


def catalog_ids() -> set[str]:
    """Experiment ids declared in the catalog's summary table."""
    text = CATALOG_PATH.read_text()
    return set(re.findall(r"^\| ((?:EXP|ABL)-[A-Z0-9]+) \|", text, flags=re.MULTILINE))


def load_config(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: the YAML must be a mapping")
    return resolve_config(raw)


def _merge_defaults(raw: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(raw)
    for key, default in DEFAULTS.items():
        if isinstance(default, dict):
            section = merged.setdefault(key, {})
            if not isinstance(section, dict):
                raise ConfigError(f"{key} must be a mapping")
            for name, value in default.items():
                section.setdefault(name, copy.deepcopy(value))
        else:
            merged.setdefault(key, copy.deepcopy(default))
    return merged


def _check_keys(raw: dict[str, Any]) -> None:
    for key in raw.keys() - TOP_LEVEL_KEYS:
        raise ConfigError(f"unknown key {key!r}")
    for section, allowed in SECTION_KEYS.items():
        value = raw.get(section)
        if isinstance(value, dict):
            for key in value.keys() - allowed:
                raise ConfigError(f"unknown key {key!r} in {section}")


def _check_seeds(seeds: Any) -> None:
    valid = isinstance(seeds, list) and seeds and all(type(s) is int for s in seeds)
    if not valid or len(set(seeds)) != len(seeds):
        raise ConfigError("seeds must be a non-empty list of distinct integers")


def resolve_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate `raw` and return a copy with every default expanded."""
    for key in REQUIRED:
        if key not in raw:
            raise ConfigError(f"missing required key {key!r}")
    _check_keys(raw)
    config = _merge_defaults(raw)

    if config["exp_id"] not in catalog_ids():
        raise ConfigError(f"exp_id {config['exp_id']!r} is not in the experiment catalog")
    if not isinstance(config["run_name"], str) or not RUN_NAME_PATTERN.match(config["run_name"]):
        raise ConfigError("run_name must be a slug of letters, digits, '.', '_' or '-'")
    _check_seeds(config["seeds"])

    env = config["env"]
    if env.get("id") not in ENVIRONMENTS:
        raise ConfigError(f"env.id must be one of {ENVIRONMENTS}, got {env.get('id')!r}")
    if env["backend"] not in BACKENDS:
        raise ConfigError(f"env.backend must be one of {BACKENDS}, got {env['backend']!r}")
    if ("switch_at" in env) != ("switch_defender" in env):
        raise ConfigError("env.switch_at and env.switch_defender must be given together")
    if env["split"] != TRAIN_SPLIT:
        raise ConfigError(
            f"env.split must be {TRAIN_SPLIT!r} for training, got {env['split']!r}: "
            "val is for model selection and test splits are never trained on"
        )

    if "algo" not in config["agent"]:
        raise ConfigError("missing required key 'algo' in agent")
    steps = config["train"].get("total_steps")
    if type(steps) is not int or steps <= 0:
        raise ConfigError("train.total_steps must be a positive integer")

    eval_cfg = config["eval"]
    eval_cfg.setdefault("suites", [DEFAULT_SUITE[env["id"]]])
    for suite in eval_cfg["suites"]:
        if suite not in SUITES_BY_ENV[env["id"]]:
            raise ConfigError(f"eval suite {suite!r} does not apply to {env['id']}")
    if type(eval_cfg["every_steps"]) is not int or eval_cfg["every_steps"] <= 0:
        raise ConfigError("eval.every_steps must be a positive integer")
    if "surrogate_val_episodes" in eval_cfg and (
        type(eval_cfg["surrogate_val_episodes"]) is not int
        or eval_cfg["surrogate_val_episodes"] <= 0
    ):
        raise ConfigError("eval.surrogate_val_episodes must be a positive integer")
    if config["agent"]["algo"] == "dyna" and "surrogate_val_episodes" not in eval_cfg:
        raise ConfigError("dyna runs require eval.surrogate_val_episodes")
    if config["checkpoint"]["save_best_on"] != "val":
        raise ConfigError("checkpoint.save_best_on must be 'val': never select on test")
    if config["logging"]["wandb"]:
        raise ConfigError("logging.wandb is not supported yet")
    return config
