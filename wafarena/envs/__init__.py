"""Gymnasium environment registration for WafArena."""

from gymnasium.envs.registration import register

from wafarena.envs.attacker_env import AttackerEnv
from wafarena.envs.defender_env import DefenderEnv

register(id="WafArena/Attacker-v0", entry_point="wafarena.envs.attacker_env:AttackerEnv")
register(id="WafArena/Defender-v0", entry_point="wafarena.envs.defender_env:DefenderEnv")

__all__ = ["AttackerEnv", "DefenderEnv"]
