"""Policy-gradient attackers in one readable file, CleanRL style (ADR-0006): REINFORCE with a
learned baseline, A2C and PPO with GAE (EXP-G1, G2, G3, G4), adapted to the callback `Agent`
protocol over the 288-dim observation of `Attacker-v0`.

The three methods share an actor (MLP -> logits over the 17 actions), a critic (MLP -> V(s)) and
one rollout buffer; they differ only in when they update and how they estimate the advantage:

- `reinforce`: updates once per finished episode; the advantage is G_t - V(s_t) (lambda = 1,
  Monte Carlo returns), with V(s) as the learned baseline (Sutton & Barto 13.4).
- `a2c`: updates every `n_steps` steps (or at the end of an episode) with n-step returns
  bootstrapped on V (lambda = 1, one gradient step).
- `ppo`: collects `n_steps` steps, estimates advantages with GAE(lambda) and runs `update_epochs`
  epochs of minibatches on the clipped surrogate objective (Schulman et al., 2017).

All three use GAE with their own lambda: delta_t = r_t + gamma * (1 - terminated_t) * V(s_{t+1})
- V(s_t), A_t = delta_t + gamma * lambda * (1 - done_t) * A_{t+1}. A time-limit truncation ends
the recursion but still bootstraps V(s_{t+1}); only a true termination cuts it.

The loss is the policy loss + `vf_coef` * value loss - `ent_coef` * entropy; `ent_coef` is the
knob of EXP-G4. Gradients are clipped to `max_grad_norm`.

`explore=False` (evaluation) follows `eval_policy`: `sample` (default) draws from the stochastic
policy with a generator of its own, so an evaluation never disturbs the training stream and a
reloaded checkpoint replays the same evaluation; `greedy` takes the argmax.
"""

from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from torch import nn

from wafarena.agents.base import META_FILE, Transition, register_agent

METHODS = ("reinforce", "a2c", "ppo")
EVAL_POLICIES = ("sample", "greedy")
WEIGHTS_FILE = "pg.pt"
EVAL_SEED_OFFSET = 1_000_003


def mlp(sizes: list[int]) -> nn.Sequential:
    layers: list[nn.Module] = []
    for i in range(len(sizes) - 1):
        layers.append(nn.Linear(sizes[i], sizes[i + 1]))
        if i < len(sizes) - 2:
            layers.append(nn.Tanh())
    return nn.Sequential(*layers)


class RolloutBuffer:
    """Steps since the last update: everything GAE and the losses need."""

    def __init__(self) -> None:
        self.obs: list[np.ndarray] = []
        self.next_obs: list[np.ndarray] = []
        self.actions: list[int] = []
        self.logprobs: list[float] = []
        self.rewards: list[float] = []
        self.terminated: list[bool] = []
        self.done: list[bool] = []

    def __len__(self) -> int:
        return len(self.rewards)

    def add(self, obs, action, logprob, reward, next_obs, terminated, truncated) -> None:
        self.obs.append(obs)
        self.actions.append(action)
        self.logprobs.append(logprob)
        self.rewards.append(reward)
        self.next_obs.append(next_obs)
        self.terminated.append(terminated)
        self.done.append(terminated or truncated)


def gae(rewards, values, next_values, terminated, done, gamma: float, lam: float) -> np.ndarray:
    """Generalized advantage estimation over one buffer (arrays of the same length)."""
    advantages = np.zeros(len(rewards), dtype=np.float64)
    running = 0.0
    for t in reversed(range(len(rewards))):
        delta = rewards[t] + gamma * (1.0 - terminated[t]) * next_values[t] - values[t]
        running = delta + gamma * lam * (1.0 - done[t]) * running
        advantages[t] = running
    return advantages


@register_agent("pg")
class PolicyGradientAgent:
    role = "attacker"

    def __init__(
        self,
        agent_id: str,
        seed: int,
        *,
        obs_dim: int,
        n_actions: int,
        method: str = "ppo",
        hidden: list[int] | None = None,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float | None = None,
        n_steps: int | None = None,
        update_epochs: int = 4,
        minibatch_size: int = 256,
        clip_coef: float = 0.2,
        ent_coef: float = 0.01,
        vf_coef: float = 0.5,
        max_grad_norm: float = 0.5,
        normalize_advantages: bool = True,
        eval_policy: str = "sample",
    ):
        if method not in METHODS:
            raise ValueError(f"unknown policy-gradient method {method!r}, expected {METHODS}")
        if eval_policy not in EVAL_POLICIES:
            raise ValueError(f"unknown eval_policy {eval_policy!r}, expected {EVAL_POLICIES}")
        self.agent_id = agent_id
        torch.manual_seed(seed)
        self._train_gen = torch.Generator().manual_seed(seed)
        self._eval_gen = torch.Generator().manual_seed(seed + EVAL_SEED_OFFSET)
        self._method, self._gamma, self._eval_policy = method, gamma, eval_policy
        self._lambda = gae_lambda if gae_lambda is not None else (0.95 if method == "ppo" else 1.0)
        self._n_steps = n_steps if n_steps is not None else {"ppo": 1024, "a2c": 16}.get(method)
        self._epochs = update_epochs if method == "ppo" else 1
        self._minibatch_size, self._clip = minibatch_size, clip_coef
        self._ent_coef, self._vf_coef, self._max_grad_norm = ent_coef, vf_coef, max_grad_norm
        self._normalize = normalize_advantages
        hidden = list(hidden or [64, 64])
        self.actor = mlp([obs_dim, *hidden, n_actions])
        self.critic = mlp([obs_dim, *hidden, 1])
        params = list(self.actor.parameters()) + list(self.critic.parameters())
        self._optimizer = torch.optim.Adam(params, lr=lr, eps=1e-5)
        self._buffer = RolloutBuffer()
        self._pending: tuple[np.ndarray, int, float] | None = None
        self._last_metrics: dict[str, float] = {}

    @classmethod
    def from_config(cls, *, params, obs_dim, n_actions, seed, agent_id) -> "PolicyGradientAgent":
        torch.set_num_threads(int(params.get("threads", 1)))
        params = {k: v for k, v in params.items() if k != "threads"}
        return cls(agent_id, seed, obs_dim=obs_dim, n_actions=n_actions, **params)

    def _logits(self, obs: np.ndarray) -> torch.Tensor:
        return self.actor(torch.as_tensor(np.asarray(obs, dtype=np.float32)).unsqueeze(0))[0]

    def action_probabilities(self, obs: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            return torch.softmax(self._logits(obs), dim=-1).numpy()

    def act(self, obs: np.ndarray, info, *, explore: bool) -> int:
        with torch.no_grad():
            logits = self._logits(obs)
            probs = torch.softmax(logits, dim=-1)
            if not explore:
                if self._eval_policy == "greedy":
                    return int(torch.argmax(probs))
                return int(torch.multinomial(probs, 1, generator=self._eval_gen))
            action = int(torch.multinomial(probs, 1, generator=self._train_gen))
            logprob = float(torch.log_softmax(logits, dim=-1)[action])
        self._pending = (np.asarray(obs, dtype=np.float32), action, logprob)
        return action

    def observe(self, t: Transition) -> dict[str, float]:
        obs, action, logprob = self._pending
        self._buffer.add(
            obs,
            action,
            logprob,
            float(t.reward),
            np.asarray(t.next_obs, dtype=np.float32),
            bool(t.terminated),
            bool(t.truncated),
        )
        done = t.terminated or t.truncated
        if self._method == "reinforce":
            ready = done
        else:
            ready = len(self._buffer) >= self._n_steps or (self._method == "a2c" and done)
        if ready:
            self._last_metrics = self._update()
        return self._last_metrics

    def _update(self) -> dict[str, float]:
        b = self._buffer
        obs = torch.as_tensor(np.stack(b.obs))
        next_obs = torch.as_tensor(np.stack(b.next_obs))
        actions = torch.as_tensor(b.actions, dtype=torch.int64)
        old_logprobs = torch.as_tensor(b.logprobs, dtype=torch.float32)
        with torch.no_grad():
            values = self.critic(obs).squeeze(1).numpy()
            next_values = self.critic(next_obs).squeeze(1).numpy()
        advantages = gae(
            np.asarray(b.rewards),
            values,
            next_values,
            np.asarray(b.terminated, dtype=float),
            np.asarray(b.done, dtype=float),
            self._gamma,
            self._lambda,
        )
        returns = torch.as_tensor(advantages + values, dtype=torch.float32)
        advantages = torch.as_tensor(advantages, dtype=torch.float32)
        n = len(b)
        batch = self._minibatch_size if self._method == "ppo" else n
        stats: dict[str, list[float]] = {"pg_loss": [], "v_loss": [], "entropy": [], "kl": []}
        for _ in range(self._epochs):
            order = torch.randperm(n, generator=self._train_gen)
            for start in range(0, n, batch):
                idx = order[start : start + batch]
                logits = self.actor(obs[idx])
                log_all = torch.log_softmax(logits, dim=-1)
                new_logprobs = log_all.gather(1, actions[idx].unsqueeze(1)).squeeze(1)
                entropy = -(log_all.exp() * log_all).sum(dim=1).mean()
                adv = advantages[idx]
                if self._normalize and len(idx) > 1:
                    adv = (adv - adv.mean()) / (adv.std() + 1e-8)
                if self._method == "ppo":
                    ratio = (new_logprobs - old_logprobs[idx]).exp()
                    clipped = ratio.clamp(1.0 - self._clip, 1.0 + self._clip)
                    pg_loss = -torch.min(ratio * adv, clipped * adv).mean()
                else:
                    pg_loss = -(new_logprobs * adv).mean()
                v_loss = 0.5 * (self.critic(obs[idx]).squeeze(1) - returns[idx]).pow(2).mean()
                loss = pg_loss + self._vf_coef * v_loss - self._ent_coef * entropy
                self._optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(
                    list(self.actor.parameters()) + list(self.critic.parameters()),
                    self._max_grad_norm,
                )
                self._optimizer.step()
                with torch.no_grad():
                    kl = (old_logprobs[idx] - new_logprobs).mean()
                stats["pg_loss"].append(float(pg_loss.detach()))
                stats["v_loss"].append(float(v_loss.detach()))
                stats["entropy"].append(float(entropy.detach()))
                stats["kl"].append(float(kl))
        self._buffer = RolloutBuffer()
        return {name: float(np.mean(values)) for name, values in stats.items()}

    def save(self, path: Path) -> None:
        torch.save(
            {"actor": self.actor.state_dict(), "critic": self.critic.state_dict()},
            Path(path) / WEIGHTS_FILE,
        )

    @classmethod
    def load(cls, path: Path) -> "PolicyGradientAgent":
        path = Path(path)
        meta = yaml.safe_load((path / META_FILE).read_text())
        params: dict[str, Any] = dict(meta.get("train", {}).get("agent_params", {}))
        params.pop("threads", None)
        seed = int(meta.get("train", {}).get("seed", 0))
        agent = cls(
            meta["agent_id"], seed, obs_dim=meta["obs_dim"], n_actions=meta["n_actions"], **params
        )
        weights = torch.load(path / WEIGHTS_FILE, weights_only=True)
        agent.actor.load_state_dict(weights["actor"])
        agent.critic.load_state_dict(weights["critic"])
        return agent
