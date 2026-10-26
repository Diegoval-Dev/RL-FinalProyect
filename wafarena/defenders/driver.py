"""DefenderDriver: wraps a trained Defender-v0 Agent as a DefenderPolicy (agentes-y-checkpoints).

Lets a defender checkpoint (DEF-REF-1, a Phase 3 candidate, ...) stand as the defender inside
`Attacker-v0` or the proxy, exactly like `ModSecDefender`. The agent acts greedily
(`explore=False`) and never learns here; it receives no `info` (a deployed defender has no
ground truth to strip).
"""

import numpy as np

from wafarena.agents.base import Agent


class DefenderDriver:
    def __init__(self, agent: Agent):
        if agent.role != "defender":
            raise ValueError(f"DefenderDriver needs a defender agent, got role {agent.role!r}")
        self._agent = agent

    @property
    def agent(self) -> Agent:
        return self._agent

    def reset_session(self, session_id: str) -> None:
        reset = getattr(self._agent, "reset_session", None)
        if callable(reset):
            reset(session_id)

    def act(self, obs: np.ndarray) -> int:
        return int(self._agent.act(obs, {}, explore=False))
