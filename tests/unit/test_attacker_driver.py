"""F2-T10: AttackerDriver wraps a trained Attacker-v0 Agent as an AttackerPolicy, for Defender-v0
(agentes-y-checkpoints.md). Driven directly (not through DefenderEnv) with a scripted fake
agent, so each case is exact and independent of ModSecurity/the oracle."""

import json
from pathlib import Path

import numpy as np

from wafarena.attackers.base import Response
from wafarena.attackers.driver import AttackerDriver
from wafarena.envs.attacker_env import SEND_ACTION
from wafarena.mutations.payload import Payload

RNG = np.random.default_rng(0)
CORPUS_PATH = Path(__file__).parents[2] / "data" / "payloads" / "corpus.jsonl"


def base_payload(text="' AND 1=1 -- -", location="query"):
    return Payload(text, location, 0)


def text_of_family(family: str) -> str:
    return next(
        entry["text"]
        for entry in (json.loads(line) for line in CORPUS_PATH.read_text().splitlines())
        if entry["family"] == family
    )


class ScriptAgent:
    """Returns actions from a fixed script, one per act() call; records every info it sees."""

    role = "attacker"

    def __init__(self, script):
        self._script = list(script)
        self.seen_infos: list[dict] = []

    def act(self, obs, info, *, explore):
        assert explore is False
        self.seen_infos.append(dict(info))
        return self._script.pop(0)


def test_first_request_is_the_base_payload_when_the_agent_sends_immediately():
    driver = AttackerDriver(ScriptAgent([SEND_ACTION]))
    driver.reset(base_payload(), "catalog", RNG)
    payload = driver.next_request(int(Response.NONE))
    assert payload.text == "' AND 1=1 -- -"


def test_mutates_before_sending_when_the_agent_asks_to():
    agent = ScriptAgent([0, SEND_ACTION])  # operator 0, then SEND
    driver = AttackerDriver(agent)
    driver.reset(base_payload(), "catalog", RNG)
    payload = driver.next_request(int(Response.NONE))
    assert payload.text != "' AND 1=1 -- -"  # case_swap (action 0) must have changed it
    assert agent.seen_infos[-1]["mutations"] == 1


def test_resolves_family_from_the_base_payloads_own_text():
    agent = ScriptAgent([SEND_ACTION])
    driver = AttackerDriver(agent)
    driver.reset(base_payload(text_of_family("tautology")), "catalog", RNG)
    driver.next_request(int(Response.NONE))
    assert agent.seen_infos[0]["family"] == "tautology"


def test_evasion_ends_the_session():
    driver = AttackerDriver(ScriptAgent([SEND_ACTION, SEND_ACTION]))
    driver.reset(base_payload(), "catalog", RNG)
    driver.next_request(int(Response.NONE))
    assert driver.next_request(int(Response.PASS_EFFECT)) is None


def test_abandons_after_ban_threshold_blocks():
    agent = ScriptAgent([SEND_ACTION] * 10)
    driver = AttackerDriver(agent, ban_threshold=3)
    driver.reset(base_payload(), "catalog", RNG)
    driver.next_request(int(Response.NONE))
    assert driver.next_request(int(Response.BLOCKED)) is not None  # block 1
    assert driver.next_request(int(Response.BLOCKED)) is not None  # block 2
    assert driver.next_request(int(Response.BLOCKED)) is None  # block 3: banned


def test_abandons_at_the_query_budget():
    agent = ScriptAgent([SEND_ACTION] * 10)
    driver = AttackerDriver(agent, query_budget=2, ban_threshold=100)
    driver.reset(base_payload(), "catalog", RNG)
    assert driver.next_request(int(Response.NONE)) is not None  # query 1
    assert driver.next_request(int(Response.PASS_NO_EFFECT)) is not None  # query 2
    assert driver.next_request(int(Response.PASS_NO_EFFECT)) is None  # budget exhausted


def test_the_agent_never_sees_a_gt_key():
    agent = ScriptAgent([SEND_ACTION])
    driver = AttackerDriver(agent)
    driver.reset(base_payload(), "catalog", RNG)
    driver.next_request(int(Response.NONE))
    assert not any(k.startswith("gt_") for info in agent.seen_infos for k in info)


def test_a_mutation_that_never_sends_within_max_steps_abandons_safely():
    agent = ScriptAgent([0] * 1000)  # always mutates, never SENDs
    driver = AttackerDriver(agent, max_steps=5)
    driver.reset(base_payload(), "catalog", RNG)
    assert driver.next_request(int(Response.NONE)) is None


def test_abstract_state_matches_attacker_env_for_the_same_history():
    """The driver must compute the identical abstract_state Attacker-v0 itself would, since
    ATK-REF-0 was trained against exactly that encoding."""
    from wafarena.envs.abstract_state import AbstractState
    from wafarena.envs.attacker_obs import family_index

    agent = ScriptAgent([0, 0, SEND_ACTION])
    driver = AttackerDriver(agent)
    driver.reset(base_payload(text_of_family("tautology")), "catalog", RNG)
    driver.next_request(int(Response.NONE))
    last_info = agent.seen_infos[-1]
    expected = AbstractState(family_index("tautology"), int(Response.NONE), 2).encode()
    assert last_info["abstract_state"] == expected
