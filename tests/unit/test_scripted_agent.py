"""F2-T09: Agent wrappers reproducing the F1 scripted references (RQ1 table), for attacker-eval-v1.

`corpus_replay` sends the base payload unmutated (CorpusReplayAttacker); `random_mutation`
samples a 1..5 mutation budget once per episode and applies that many uniformly random
operators before sending (RandomMutationAttacker) — the same policy, expressed as discrete
mutate/SEND actions instead of returning whole payloads.
"""

import numpy as np
import pytest

from wafarena.agents.scripted import ScriptedAgent
from wafarena.attackers.random_mutation import DEFAULT_MAX_MUTATIONS
from wafarena.envs.attacker_env import N_ACTIONS, SEND_ACTION

OBS = np.zeros(288)


def make(variant: str, seed: int = 0) -> ScriptedAgent:
    return ScriptedAgent.from_config(
        params={"variant": variant}, obs_dim=288, n_actions=N_ACTIONS, seed=seed, agent_id="t"
    )


def play_episode(agent: ScriptedAgent) -> list[int]:
    actions, mutations = [], 0
    while True:
        action = agent.act(OBS, {"mutations": mutations}, explore=False)
        actions.append(action)
        if action == SEND_ACTION:
            return actions
        mutations += 1


def test_corpus_replay_always_sends_immediately():
    agent = make("corpus_replay")
    for _ in range(5):
        assert play_episode(agent) == [SEND_ACTION]


def test_random_mutation_sends_after_one_to_five_mutations():
    agent = make("random_mutation", seed=1)
    budgets = {len(play_episode(agent)) - 1 for _ in range(200)}
    assert budgets <= set(range(1, DEFAULT_MAX_MUTATIONS + 1))
    assert len(budgets) > 1  # the budget really varies across episodes


def test_random_mutation_actions_are_uniform_over_the_operator_registry():
    agent = make("random_mutation", seed=2)
    seen = set()
    for _ in range(500):
        for action in play_episode(agent)[:-1]:  # every action but the final SEND
            seen.add(action)
    assert seen == set(range(SEND_ACTION))


def test_random_mutation_resamples_the_budget_every_episode():
    agent = make("random_mutation", seed=3)
    lengths = [len(play_episode(agent)) for _ in range(50)]
    assert len(set(lengths)) > 1


def test_deterministic_given_seed():
    def run(seed):
        agent = make("random_mutation", seed=seed)
        return [play_episode(agent) for _ in range(10)]

    assert run(7) == run(7)
    assert run(7) != run(8)


def test_does_not_learn():
    agent = make("corpus_replay")
    assert agent.observe(None) == {}


def test_unknown_variant_is_rejected():
    with pytest.raises(ValueError, match="no-such-variant"):
        make("no-such-variant")
