"""F2-T04: attacker evaluation suites are fixed and reproducible (metricas.md, Suites)."""

import numpy as np
import pytest

from wafarena.envs.attacker_env import SEND_ACTION
from wafarena.envs.backends.fake import FakeBackend
from wafarena.eval import harness
from wafarena.eval.metrics import evasion_rate


class CycleAgent:
    """Deterministic attacker: mutates with a fixed operator cycle, then sends."""

    agent_id = "cycle"
    role = "attacker"

    def __init__(self, cycle=(0, 3, 5, SEND_ACTION)):
        self._cycle = cycle
        self._step = 0
        self.seen_info_keys: set[str] = set()

    def act(self, obs, info, *, explore):
        assert explore is False
        self.seen_info_keys |= set(info)
        action = self._cycle[self._step % len(self._cycle)]
        self._step += 1
        return action

    def observe(self, t):
        raise AssertionError("evaluation must not train the agent")


def run(agent, suite="attacker-eval-v1", pl=1):
    return harness.run_attacker_suite(
        agent, suite, defender={"type": "modsec", "paranoia_level": pl}, backend=FakeBackend()
    )


def test_attacker_suites_match_the_contract():
    v1 = harness.ATTACKER_SUITES["attacker-eval-v1"]
    assert (v1.split, v1.query_budget) == ("test", 50)
    assert list(v1.seeds) == list(range(1000, 1200))
    family = harness.ATTACKER_SUITES["attacker-eval-family-v1"]
    assert (family.split, len(family.seeds)) == ("test-family", 200)


def test_suite_runs_one_result_per_seed():
    results = run(CycleAgent())
    assert [r.seed for r in results] == list(range(1000, 1200))


def test_suite_is_reproducible_across_runs():
    assert run(CycleAgent()) == run(CycleAgent())


def test_suite_shows_every_agent_the_same_episodes():
    always_send = CycleAgent(cycle=(SEND_ACTION,))
    assert [r.base_id for r in run(CycleAgent())] == [r.base_id for r in run(always_send)]


def test_family_suite_draws_from_a_different_split():
    assert {r.base_id for r in run(CycleAgent())} != {
        r.base_id for r in run(CycleAgent(), suite="attacker-eval-family-v1")
    }


def test_agent_never_sees_ground_truth_keys():
    agent = CycleAgent()
    run(agent)
    assert agent.seen_info_keys
    assert not any(key.startswith("gt_") for key in agent.seen_info_keys)


def test_always_send_agent_records_no_mutations():
    results = run(CycleAgent(cycle=(SEND_ACTION,)))
    assert all(r.mutation_attempts == 0 and r.broken == 0 for r in results)
    assert all(r.queries_used >= 1 for r in results)


def test_mutation_attempts_count_non_send_actions():
    results = run(CycleAgent())
    assert any(r.mutation_attempts > 0 for r in results)
    assert all(r.broken <= r.mutation_attempts for r in results)


def test_evasion_rate_is_computable_from_suite_results():
    assert 0.0 <= evasion_rate(run(CycleAgent())) <= 1.0


def test_unknown_suite_is_rejected():
    with pytest.raises(KeyError, match="no-such-suite"):
        run(CycleAgent(), suite="no-such-suite")


def test_non_attacker_agent_is_rejected():
    agent = CycleAgent()
    agent.role = "defender"
    with pytest.raises(ValueError, match="attacker"):
        run(agent)


def test_numpy_scalar_actions_are_accepted():
    agent = CycleAgent(cycle=(np.int64(SEND_ACTION),))
    assert run(agent)


def test_validation_suite_uses_val_and_is_not_a_reportable_suite():
    val = harness.VALIDATION_SUITES["attacker-val-v1"]
    assert val.split == "val" and len(val.seeds) == 200
    assert not set(val.seeds) & set(harness.EVAL_SEEDS)
    assert "attacker-val-v1" not in harness.ATTACKER_SUITES
    assert all(s.split.startswith("test") for s in harness.ATTACKER_SUITES.values())


def test_validation_suite_can_be_run():
    results = run(CycleAgent(), suite="attacker-val-v1")
    assert [r.seed for r in results] == list(harness.VALIDATION_SUITES["attacker-val-v1"].seeds)


def test_summarize_attacker_reports_every_attacker_metric():
    results = run(CycleAgent())
    summary = harness.summarize_attacker(results, query_budget=50)
    assert summary["episodes"] == 200
    assert summary["evasion_rate"] == evasion_rate(results)
    assert {"qfe", "qfe_c", "diversity", "uniqueness", "break_rate"} <= summary.keys()
    assert summary["evasions"] == sum(r.evaded for r in results)
