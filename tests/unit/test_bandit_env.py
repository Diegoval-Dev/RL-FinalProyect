"""F2-T05: bandit wrapper over Attacker-v0 (catalogo.md, EXP-A1: 16 arms, reward 1 on evasion)."""

import gymnasium as gym
import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

import wafarena.envs  # noqa: F401  (registers the envs)
from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs.backends.fake import FakeBackend
from wafarena.envs.bandit_env import N_ARMS, BanditEnv


def make_env(**kwargs) -> BanditEnv:
    return BanditEnv(backend=FakeBackend(), split="train", **kwargs)


def pull_until_done(env: BanditEnv, arm: int = 0):
    rewards, infos, done = [], [], False
    while not done:
        _obs, reward, terminated, truncated, info = env.step(arm)
        rewards.append(reward)
        infos.append(info)
        done = terminated or truncated
    return rewards, infos


def test_has_one_arm_per_mutation_operator():
    env = make_env()
    assert N_ARMS == 16 and env.action_space.n == 16
    assert env.observation_space.shape == (288,)


def test_passes_the_gymnasium_checker():
    check_env(make_env(), skip_render_check=True)


def test_reward_is_one_exactly_when_the_pull_evades():
    env = make_env()
    env.reset(seed=3)
    rewards, infos = pull_until_done(env, arm=5)
    assert set(rewards) <= {0.0, 1.0}
    assert [r == 1.0 for r in rewards] == [i["evaded"] for i in infos]


def test_every_pull_sends_exactly_one_query():
    env = make_env(query_budget=50)
    env.reset(seed=1)
    _obs, _r, _t, _tr, info = env.step(0)
    assert info["queries_used"] == 1
    _obs, _r, _t, _tr, info = env.step(1)
    assert info["queries_used"] == 2


def test_pull_info_reports_arm_and_mutation_outcome():
    env = make_env()
    env.reset(seed=2)
    _obs, _r, _t, _tr, info = env.step(7)
    assert info["arm"] == 7
    assert {"broken", "noop", "evaded", "banned", "abstract_state"} <= info.keys()


def test_episode_ends_on_evasion_ban_or_query_budget():
    env = make_env(query_budget=6, ban_threshold=3)
    env.reset(seed=4)
    _rewards, infos = pull_until_done(env)
    last = infos[-1]
    assert last["evaded"] or last["banned"] or last["queries_used"] >= 6


def test_reset_starts_a_new_payload_session():
    env = make_env()
    _obs, first = env.reset(seed=5)
    pull_until_done(env)
    _obs, second = env.reset()
    assert second["queries_used"] == 0 and second["mutations"] == 0


def test_same_seed_gives_the_same_pulls():
    def run():
        env = make_env()
        env.reset(seed=9)
        return pull_until_done(env, arm=3)[0]

    assert run() == run()


def test_defender_switches_after_the_given_number_of_pulls():
    env = make_env(switch_at=4, switch_defender={"type": "modsec", "paranoia_level": 3})
    inner = env.unwrapped._inner
    assert inner._defender._index == ModSecDefender(1)._index
    env.reset(seed=0)
    pulls = 0
    while pulls < 4:
        _o, _r, terminated, truncated, _i = env.step(0)
        pulls += 1
        if terminated or truncated:
            env.reset()
    assert inner._defender._index == ModSecDefender(1)._index  # 4 pulls done under PL1
    env.step(0)
    assert inner._defender._index == ModSecDefender(3)._index  # the 5th pull faces PL3


def test_switch_options_must_come_together():
    with pytest.raises(ValueError, match="switch"):
        make_env(switch_at=10)


def test_registered_for_gym_make():
    env = gym.make("WafArena/AttackerBandit-v0", backend=FakeBackend(), split="train")
    obs, _info = env.reset(seed=0)
    assert obs.shape == (288,)
    assert isinstance(env.action_space.sample(), (int, np.integer))
