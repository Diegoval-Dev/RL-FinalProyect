"""WafArena/AttackerBandit-v0: a k-armed bandit over Attacker-v0 (catalogo.md, EXP-A1).

An arm is a mutation operator. One pull applies it to the current payload and sends the result to
the defender; the reward is 1 when the request evades and 0 otherwise. A pull that evades, gets
the attacker banned or exhausts the query budget ends the episode, and the next `reset` starts
from a fresh base payload.
"""

import gymnasium as gym
from gymnasium import spaces

from wafarena.envs.attacker_env import SEND_ACTION, AttackerEnv

N_ARMS = SEND_ACTION  # one arm per mutation operator; SEND is part of every pull


class BanditEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, *, switch_at: int | None = None, switch_defender=None, **env_kwargs):
        if (switch_at is None) != (switch_defender is None):
            raise ValueError("switch_at and switch_defender must be given together")
        self._inner = AttackerEnv(**env_kwargs)
        self._switch_at = switch_at
        self._switch_defender = switch_defender
        self._pulls = 0
        self.observation_space = self._inner.observation_space
        self.action_space = spaces.Discrete(N_ARMS)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        return self._inner.reset(seed=seed, options=options)

    def step(self, arm: int):
        if self._switch_at is not None and self._pulls == self._switch_at:
            self._inner.set_defender(self._switch_defender)
        self._pulls += 1
        obs, _reward, terminated, truncated, mutation = self._inner.step(int(arm))
        if terminated or truncated:  # the step budget ran out before the payload could be sent
            return obs, 0.0, terminated, truncated, self._pull_info(mutation, arm)
        obs, _reward, terminated, truncated, info = self._inner.step(SEND_ACTION)
        reward = 1.0 if info["evaded"] else 0.0
        return obs, reward, terminated, truncated, self._pull_info(info, arm, mutation)

    @staticmethod
    def _pull_info(info: dict, arm: int, mutation: dict | None = None) -> dict:
        mutation = mutation or info
        return {**info, "arm": int(arm), "broken": mutation["broken"], "noop": mutation["noop"]}
