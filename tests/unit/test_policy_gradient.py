"""F3-T08: policy-gradient attackers (REINFORCE, A2C, PPO), DefenderDriver and learned defenders
inside Attacker-v0."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from wafarena import run as runner
from wafarena.agents import load_checkpoint, save_checkpoint
from wafarena.agents.base import Transition
from wafarena.agents.linear import LinearAgent
from wafarena.agents.pg import PolicyGradientAgent, gae
from wafarena.defenders.driver import DefenderDriver
from wafarena.envs.attacker_env import SEND_ACTION, AttackerEnv
from wafarena.envs.backends.fake import FakeBackend
from wafarena.envs.resolve import resolve_defender

OBS_DIM, N_ACTIONS = 6, 3
REPO = Path(__file__).parents[2]


def agent(method="ppo", **params) -> PolicyGradientAgent:
    defaults = {"hidden": [16], "n_steps": 8 if method != "reinforce" else None}
    defaults.update(params)
    return PolicyGradientAgent(
        "pg",
        0,
        obs_dim=OBS_DIM,
        n_actions=N_ACTIONS,
        method=method,
        **{k: v for k, v in defaults.items() if v is not None},
    )


def bandit_step(a: PolicyGradientAgent, rng, *, done_every=4, t=0):
    """A one-state task: action 1 pays +1, the others 0. Episodes last `done_every` steps."""
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    action = a.act(obs, {}, explore=True)
    done = (t + 1) % done_every == 0
    return a.observe(Transition(obs, action, float(action == 1), obs, done, False, {}))


# --- GAE ---------------------------------------------------------------------------------------


def test_gae_with_lambda_one_is_the_discounted_return_minus_the_baseline():
    rewards = np.array([1.0, 0.0, 2.0])
    values = np.array([0.5, 0.5, 0.5])
    next_values = np.array([0.5, 0.5, 9.0])  # bootstrap value of the last next state is ignored:
    terminated = np.array([0.0, 0.0, 1.0])  # the episode terminated there
    done = terminated.copy()
    adv = gae(rewards, values, next_values, terminated, done, gamma=0.5, lam=1.0)
    returns = np.array([1 + 0.5 * 0 + 0.25 * 2, 0 + 0.5 * 2, 2.0])
    np.testing.assert_allclose(adv, returns - values)


def test_gae_truncation_stops_the_recursion_but_still_bootstraps():
    rewards = np.array([0.0, 0.0])
    values = np.zeros(2)
    next_values = np.array([0.0, 4.0])
    terminated = np.zeros(2)
    done = np.array([0.0, 1.0])  # truncated at t = 1
    adv = gae(rewards, values, next_values, terminated, done, gamma=0.5, lam=1.0)
    np.testing.assert_allclose(adv, [0.5 * 0.5 * 4.0, 0.5 * 4.0])


def test_gae_zero_lambda_is_the_one_step_td_error():
    rewards = np.array([1.0, 1.0])
    values = np.array([0.2, 0.4])
    next_values = np.array([0.4, 0.0])
    adv = gae(rewards, values, next_values, np.zeros(2), np.zeros(2), gamma=0.9, lam=0.0)
    np.testing.assert_allclose(adv, rewards + 0.9 * next_values - values)


# --- update schedules --------------------------------------------------------------------------


def test_reinforce_updates_once_per_finished_episode():
    a, rng = agent("reinforce"), np.random.default_rng(0)
    metrics = [bandit_step(a, rng, done_every=4, t=t) for t in range(3)]
    assert metrics == [{}, {}, {}]
    assert "pg_loss" in bandit_step(a, rng, done_every=4, t=3)


def test_a2c_updates_every_n_steps():
    a, rng = agent("a2c", n_steps=5), np.random.default_rng(0)
    metrics = [bandit_step(a, rng, done_every=100, t=t) for t in range(5)]
    assert metrics[3] == {} and "pg_loss" in metrics[4]


def test_ppo_updates_after_a_full_rollout():
    a, rng = agent("ppo", n_steps=8, minibatch_size=4, update_epochs=2), np.random.default_rng(0)
    metrics = [bandit_step(a, rng, done_every=3, t=t) for t in range(8)]
    assert metrics[6] == {} and {"pg_loss", "v_loss", "entropy", "kl"} <= set(metrics[7])


@pytest.mark.parametrize("method", ["reinforce", "a2c", "ppo"])
def test_every_method_learns_the_rewarding_action(method):
    a, rng = agent(method, lr=0.01, ent_coef=0.0), np.random.default_rng(0)
    before = a.action_probabilities(np.zeros(OBS_DIM))[1]
    for t in range(600):
        bandit_step(a, rng, done_every=4, t=t)
    after = a.action_probabilities(np.zeros(OBS_DIM))[1]
    assert after > max(before, 0.8)


def test_entropy_bonus_keeps_the_policy_more_stochastic():
    probs = {}
    for coef in (0.0, 0.5):
        a, rng = agent("ppo", lr=0.01, ent_coef=coef), np.random.default_rng(0)
        for t in range(400):
            bandit_step(a, rng, done_every=4, t=t)
        probs[coef] = a.action_probabilities(np.zeros(OBS_DIM)).max()
    assert probs[0.5] < probs[0.0]


# --- evaluation policy and determinism ---------------------------------------------------------


def test_evaluation_never_disturbs_the_training_stream():
    plain, interleaved = agent("ppo"), agent("ppo")
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    a_plain, a_inter = [], []
    for _ in range(20):
        a_plain.append(plain.act(obs, {}, explore=True))
        plain.observe(Transition(obs, a_plain[-1], 0.0, obs, False, False, {}))
        interleaved.act(obs, {}, explore=False)  # an evaluation in between
        a_inter.append(interleaved.act(obs, {}, explore=True))
        interleaved.observe(Transition(obs, a_inter[-1], 0.0, obs, False, False, {}))
    assert a_plain == a_inter


def test_greedy_eval_policy_is_the_argmax():
    a = agent("ppo", eval_policy="greedy")
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    best = int(np.argmax(a.action_probabilities(obs)))
    assert {a.act(obs, {}, explore=False) for _ in range(20)} == {best}


def test_checkpoint_round_trip_replays_the_same_evaluation(tmp_path):
    a = agent("ppo", ent_coef=0.05)
    rng = np.random.default_rng(0)
    for t in range(16):
        bandit_step(a, rng, t=t)
    save_checkpoint(
        a,
        tmp_path,
        algo="pg",
        obs_dim=OBS_DIM,
        n_actions=N_ACTIONS,
        train={"seed": 0, "agent_params": {"method": "ppo", "hidden": [16], "n_steps": 8}},
    )
    first, second = load_checkpoint(tmp_path), load_checkpoint(tmp_path)
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    np.testing.assert_allclose(first.action_probabilities(obs), a.action_probabilities(obs))
    assert [first.act(obs, {}, explore=False) for _ in range(10)] == [
        second.act(obs, {}, explore=False) for _ in range(10)
    ]


@pytest.mark.parametrize("bad", [{"method": "nope"}, {"eval_policy": "nope"}])
def test_rejects_unknown_options(bad):
    with pytest.raises(ValueError):
        PolicyGradientAgent("pg", 0, obs_dim=OBS_DIM, n_actions=N_ACTIONS, **bad)


# --- learned defenders inside Attacker-v0 ------------------------------------------------------


@pytest.fixture
def defender_checkpoint(tmp_path) -> Path:
    """A linear defender that blocks everything: Q(s, BLOCK) = 1, the rest 0."""
    d = LinearAgent("block-all", 0, obs_dim=37, n_actions=5)
    d.weights[1, -1] = 1.0
    save_checkpoint(d, tmp_path / "def", algo="linear", obs_dim=37, n_actions=5)
    return tmp_path / "def"


def test_defender_driver_needs_a_defender():
    with pytest.raises(ValueError, match="defender"):
        DefenderDriver(agent("ppo"))


def test_attacker_env_takes_a_checkpoint_defender(defender_checkpoint):
    defender = resolve_defender({"type": "checkpoint", "path": str(defender_checkpoint)})
    assert isinstance(defender, DefenderDriver)
    env = AttackerEnv(
        FakeBackend(), defender={"type": "checkpoint", "path": str(defender_checkpoint)}
    )
    env.reset(seed=0)
    *_, info = env.step(SEND_ACTION)
    assert info["gt_defender_action"] == 1 and info["blocks"] == 1


def test_the_learned_defender_sees_the_session_of_the_episode(defender_checkpoint):
    seen = []

    class Recorder:
        def reset_session(self, session_id):
            pass

        def act(self, obs):
            seen.append(obs.copy())
            return 1

    env = AttackerEnv(FakeBackend(), defender=Recorder())
    env.reset(seed=0)
    env.step(SEND_ACTION)
    env.step(SEND_ACTION)
    assert not seen[0][16:37].any()  # first request: no history yet
    assert seen[1][16:37].any()  # second request: the first one is in the session features
    assert ((0 <= seen[1]) & (seen[1] <= 1)).all()


def test_modsec_decisions_in_attacker_env_ignore_the_session_features():
    env_a = AttackerEnv(FakeBackend(), defender={"type": "modsec", "paranoia_level": 1})
    env_b = AttackerEnv(FakeBackend(), defender={"type": "modsec", "paranoia_level": 1})
    env_a.reset(seed=4)
    env_b.reset(seed=4)
    for _ in range(5):
        assert env_a.step(SEND_ACTION)[1] == env_b.step(SEND_ACTION)[1]


# --- runner, end to end ------------------------------------------------------------------------


def test_policy_gradient_attacker_runs_end_to_end(tmp_path, defender_checkpoint, monkeypatch):
    import dataclasses

    from wafarena.eval import harness

    for suites in (harness.ATTACKER_SUITES, harness.VALIDATION_SUITES):
        for name, suite in list(suites.items()):
            short = range(suite.seeds.start, suite.seeds.start + 5)
            monkeypatch.setitem(suites, name, dataclasses.replace(suite, seeds=short))
    config = {
        "exp_id": "EXP-G3",
        "run_name": "toy-ppo",
        "seeds": [0],
        "env": {
            "id": "WafArena/Attacker-v0",
            "defender": {"type": "checkpoint", "path": str(defender_checkpoint)},
            "query_budget": 10,
            "max_steps": 30,
        },
        "agent": {"algo": "pg", "params": {"method": "ppo", "hidden": [16], "n_steps": 32}},
        "train": {"total_steps": 128},
        "eval": {"suites": ["attacker-eval-v1"], "every_steps": 64},
        "logging": {"tensorboard": False},
    }
    runner.run_experiment(
        copy.deepcopy(config),
        results_root=tmp_path / "r",
        repo=REPO,
        allow_dirty=True,
        backend=FakeBackend(),
    )
    run = tmp_path / "r" / "EXP-G3" / "toy-ppo" / "s0"
    final = json.loads((run / "final_eval.json").read_text())
    assert final["suites"]["attacker-eval-v1"]["episodes"] == 5
    meta = (run / "checkpoint" / "meta.yaml").read_text()
    assert str(defender_checkpoint) in meta
