"""Tabular dynamic programming over the estimated abstract MDP (catalogo.md EXP-B1).

Builds `P(s'|s,a)` and `R(s,a)` over the 120 abstract states from sampled `(s, a, r, s', done)`
transitions, then solves it exactly with value iteration and policy iteration.

An `(s, a)` pair never observed defaults to a zero-reward self-loop. This also gives the right
answer for the states that are genuinely absorbing in `Attacker-v0` (an evasion always ends the
episode, so that abstract state is never the *start* of another transition): their value settles
to 0 at the fixed point, with no separate "terminal" bookkeeping needed. States that are only
*sometimes* terminal (e.g. a block that happens to cross `ban_threshold`) mix terminal and
non-terminal outcomes under one empirical average — a real limitation of this lossy abstraction,
declared in the report rather than special-cased away.
"""

from pathlib import Path
from typing import Any

import numpy as np

from wafarena.agents.base import META_FILE, register_agent

Transition = tuple[int, int, float, int, bool]
POLICY_FILE = "policy.npy"


def estimate_model(
    transitions: list[Transition], *, n_states: int, n_actions: int
) -> tuple[np.ndarray, np.ndarray]:
    """`(P, R)` of shapes `(n_states, n_actions, n_states)` and `(n_states, n_actions)`."""
    counts = np.zeros((n_states, n_actions, n_states))
    reward_sum = np.zeros((n_states, n_actions))
    visits = np.zeros((n_states, n_actions))
    for state, action, reward, next_state, _done in transitions:
        counts[state, action, next_state] += 1
        reward_sum[state, action] += reward
        visits[state, action] += 1

    unvisited = visits == 0
    P = np.divide(
        counts, visits[:, :, None], out=np.zeros_like(counts), where=~unvisited[:, :, None]
    )
    R = np.divide(reward_sum, visits, out=np.zeros_like(reward_sum), where=~unvisited)
    for state in range(n_states):
        P[state, unvisited[state], state] = 1.0  # unvisited (s, a): self-loop, zero reward
    return P, R


def _check_gamma(gamma: float) -> None:
    if not 0.0 <= gamma < 1.0:
        raise ValueError(f"gamma must be in [0, 1), got {gamma}")


def action_values(P: np.ndarray, R: np.ndarray, V: np.ndarray, gamma: float) -> np.ndarray:
    """Q(s, a) = R(s, a) + gamma * sum_s' P(s, a, s') V(s'), shape (n_states, n_actions)."""
    return R + gamma * P @ V


def value_iteration(
    P: np.ndarray, R: np.ndarray, *, gamma: float, theta: float, max_iterations: int = 100_000
) -> tuple[np.ndarray, np.ndarray, int]:
    """`(V*, greedy policy, iterations)`. Converges once the max value update is below `theta`."""
    _check_gamma(gamma)
    n_states = R.shape[0]
    V = np.zeros(n_states)
    for iteration in range(1, max_iterations + 1):
        Q = action_values(P, R, V, gamma)
        new_V = Q.max(axis=1)
        if np.max(np.abs(new_V - V)) < theta:
            return new_V, Q.argmax(axis=1), iteration
        V = new_V
    raise RuntimeError(f"value iteration did not converge in {max_iterations} iterations")


def policy_value(
    P: np.ndarray, R: np.ndarray, policy: np.ndarray, *, gamma: float, theta: float = 1e-10
) -> np.ndarray:
    """Exact state values of a fixed `policy`, by iterative policy evaluation."""
    _check_gamma(gamma)
    n_states = R.shape[0]
    states = np.arange(n_states)
    V = np.zeros(n_states)
    while True:
        new_V = R[states, policy] + gamma * (P[states, policy] @ V)
        if np.max(np.abs(new_V - V)) < theta:
            return new_V
        V = new_V


def policy_iteration(
    P: np.ndarray, R: np.ndarray, *, gamma: float, theta: float, max_iterations: int = 10_000
) -> tuple[np.ndarray, np.ndarray, int]:
    """`(V of the final policy, final policy, iterations)`, by policy iteration."""
    _check_gamma(gamma)
    n_states = R.shape[0]
    policy = np.zeros(n_states, dtype=int)
    for iteration in range(1, max_iterations + 1):
        V = policy_value(P, R, policy, gamma=gamma, theta=theta)
        new_policy = action_values(P, R, V, gamma).argmax(axis=1)
        if np.array_equal(new_policy, policy):
            return V, policy, iteration
        policy = new_policy
    raise RuntimeError(f"policy iteration did not converge in {max_iterations} iterations")


@register_agent("dp")
class DPPolicyAgent:
    """Deploys a policy table solved offline by value or policy iteration; it does not learn."""

    role = "attacker"

    def __init__(self, agent_id: str, policy: np.ndarray):
        self.agent_id = agent_id
        self.policy = policy

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id) -> "DPPolicyAgent":
        from wafarena.envs.abstract_state import N_STATES

        return cls(agent_id, np.zeros(N_STATES, dtype=int))

    def act(self, obs: np.ndarray, info: dict[str, Any], *, explore: bool) -> int:
        return int(self.policy[info["abstract_state"]])

    def observe(self, t) -> dict[str, float]:
        return {}

    def save(self, path: Path) -> None:
        np.save(path / POLICY_FILE, self.policy)

    @classmethod
    def load(cls, path: Path) -> "DPPolicyAgent":
        import yaml

        agent_id = yaml.safe_load((path / META_FILE).read_text())["agent_id"]
        return cls(agent_id, np.load(path / POLICY_FILE))
