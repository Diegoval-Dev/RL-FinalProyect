"""BanditAgent: the k-armed bandit methods of EXP-A1/EXP-A2 (catalogo.md), one arm per operator.

Context-free: `act` ignores `obs` and the abstract state, exactly like the bandit wrapper over
Attacker-v0 that it trains against (`WafArena/AttackerBandit-v0`). `explore=True` is the training
selection rule (greedy, ε-greedy, optimistic, UCB or uniform random); `explore=False` deploys the
learned policy — the single best arm, repeated — inside a plain `Attacker-v0` episode by
alternating one mutation with that arm and one `SEND`, which is what "ER final en
attacker-eval-v1 usando la política del bandit" means.
"""

from pathlib import Path
from typing import Any

import numpy as np

from wafarena.agents.base import META_FILE, Transition, register_agent
from wafarena.envs.attacker_env import SEND_ACTION
from wafarena.envs.bandit_env import N_ARMS

POLICIES = ("greedy", "eps_greedy", "ucb", "random")
STEP_MODES = ("sample_average", "constant")
WEIGHTS_FILE = "bandit.npz"


@register_agent("bandit")
class BanditAgent:
    role = "attacker"

    def __init__(
        self,
        agent_id: str,
        seed: int,
        *,
        policy: str = "greedy",
        epsilon: float = 0.0,
        c: float = 2.0,
        q0: float = 0.0,
        step: str = "sample_average",
        alpha: float = 0.1,
    ):
        if policy not in POLICIES:
            raise ValueError(f"unknown bandit policy {policy!r}, expected one of {POLICIES}")
        if step not in STEP_MODES:
            raise ValueError(f"unknown step mode {step!r}, expected one of {STEP_MODES}")
        self.agent_id = agent_id
        self._rng = np.random.default_rng(seed)
        self._policy, self._epsilon, self._c = policy, epsilon, c
        self._step_mode, self._alpha = step, alpha
        self.q = np.full(N_ARMS, float(q0))
        self.counts = np.zeros(N_ARMS, dtype=int)
        self._t = 0
        self._awaiting_mutation = True  # deployment state: next deployed action is a mutation

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id) -> "BanditAgent":
        return cls(agent_id, seed, **params)

    def _best_arm(self) -> int:
        return int(self._rng.choice(np.flatnonzero(self.q == self.q.max())))

    def _select_training_arm(self) -> int:
        if self._policy == "random":
            return int(self._rng.integers(N_ARMS))
        unplayed = np.flatnonzero(self.counts == 0)
        if self._policy == "ucb" and unplayed.size:
            return int(self._rng.choice(unplayed))
        if self._policy == "eps_greedy" and self._rng.random() < self._epsilon:
            return int(self._rng.integers(N_ARMS))
        if self._policy == "ucb":
            bonus = self._c * np.sqrt(np.log(self._t) / self.counts)
            return int(
                self._rng.choice(np.flatnonzero(np.isclose((self.q + bonus).max(), self.q + bonus)))
            )
        return self._best_arm()

    def act(self, obs: np.ndarray, info: dict[str, Any], *, explore: bool) -> int:
        if explore:
            return self._select_training_arm()
        # `mutations` is 0 only once, at the very start of an episode — unlike `queries_used`,
        # it does not stay 0 for as long as every SEND keeps getting blocked, so it cannot get
        # the agent stuck re-arming "mutate next" forever and never reaching SEND (F2-T05).
        if info.get("mutations", 0) == 0:
            self._awaiting_mutation = True
        if self._awaiting_mutation:
            self._awaiting_mutation = False
            return self._best_arm()
        self._awaiting_mutation = True
        return SEND_ACTION

    def observe(self, t: Transition) -> dict[str, float]:
        arm = t.action
        self.counts[arm] += 1
        self._t += 1
        step = self._alpha if self._step_mode == "constant" else 1.0 / self.counts[arm]
        self.q[arm] += step * (t.reward - self.q[arm])
        return {"q_best": float(self.q.max()), "best_arm": float(self.q.argmax())}

    def save(self, path: Path) -> None:
        np.savez(path / WEIGHTS_FILE, q=self.q, counts=self.counts, t=self._t)

    @classmethod
    def load(cls, path: Path) -> "BanditAgent":
        import yaml

        meta = yaml.safe_load((path / META_FILE).read_text())
        params = meta.get("train", {}).get("agent_params", {})
        agent = cls(meta["agent_id"], seed=0, **params)
        data = np.load(path / WEIGHTS_FILE)
        agent.q, agent.counts, agent._t = data["q"], data["counts"], int(data["t"])
        return agent
