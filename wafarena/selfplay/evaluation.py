"""Small, fixed validation comparisons after each self-play generation."""

from pathlib import Path

from wafarena.agents import load_checkpoint
from wafarena.envs.attacker_env import AttackerEnv
from wafarena.envs.defender_env import DefenderEnv
from wafarena.eval import harness


def _defender_spec(name: str) -> dict:
    if name.startswith("modsec-pl") and name[9:].isdigit():
        return {"type": "modsec", "paranoia_level": int(name[9:])}
    return {"type": "checkpoint", "path": name}


def _attacker_spec(name: str):
    if name in ("corpus-replay", "random-mutation"):
        return name.replace("-", "_")
    return {"type": "checkpoint", "path": f"checkpoints/refs/{name}"}


def evaluate_generation(
    attacker_checkpoint: Path,
    defender,
    backend,
    *,
    attacker_episodes: int,
    defender_sessions: int,
    attacker_defenders: list[str],
    defender_attackers: list[str],
) -> dict:
    """Use the same held-out `val` examples and seeds for every generation."""
    attack_results = {}
    for name in attacker_defenders:
        attacker = load_checkpoint(attacker_checkpoint)
        env = AttackerEnv(backend, defender=_defender_spec(name), split="val")
        episodes = [
            harness._play_episode(attacker, env, seed)
            for seed in range(2000, 2000 + attacker_episodes)
        ]
        attack_results[name] = harness.summarize_attacker(episodes, query_budget=50)

    plan = harness.build_session_plan(
        harness.DefenderSuite(
            "selfplay-val",
            "val",
            "val",
            tuple(defender_attackers),
            n_sessions=defender_sessions,
            attack_ratio=0.5,
        )
    )
    defend_results = {}
    for name in defender_attackers:
        env = DefenderEnv(backend, attacker=_attacker_spec(name), split="val", attack_split="val")
        records = [record for item in plan for record in harness._play_session(defender, env, item)]
        defend_results[name] = {**harness.summarize_defender(records), "sessions": len(plan)}
    return {"split": "val", "attacker": attack_results, "defender": defend_results}
