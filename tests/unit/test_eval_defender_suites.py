"""F2-T04: defender evaluation suites are fixed and reproducible (metricas.md, Suites)."""

import json

import pytest

from wafarena.defenders.base import Action
from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs.backends.fake import FakeBackend
from wafarena.eval import harness, metrics
from wafarena.splits.builder import SPLITS_PATH

SPLITS = json.loads(SPLITS_PATH.read_text())


def plan_of(name: str) -> list[harness.SessionPlan]:
    return harness.build_session_plan(harness.DEFENDER_SUITES[name])


def attacks(plan):
    return [p.ref for p in plan if p.is_attack]


def benign(plan):
    return [p.ref for p in plan if not p.is_attack]


class FixedDefender:
    """Agent-style defender that always takes one action and records what it saw."""

    agent_id = "fixed"
    role = "defender"

    def __init__(self, action: int):
        self._action = action
        self.seen_info_keys: set[str] = set()

    def act(self, obs, info, *, explore):
        assert explore is False
        self.seen_info_keys |= set(info)
        return self._action

    def observe(self, t):
        raise AssertionError("evaluation must not train the agent")


def test_defender_eval_v1_plan_has_2000_sessions_with_10_percent_attacks():
    plan = plan_of("defender-eval-v1")
    assert len(plan) == 2000 and len(attacks(plan)) == 200
    assert set(attacks(plan)) <= set(SPLITS["payloads"]["test"])
    assert set(benign(plan)) <= set(SPLITS["benign"]["test"])


def test_hard_plan_uses_every_test_hard_session_and_the_v1_attacks():
    hard, v1 = plan_of("defender-eval-hard-v1"), plan_of("defender-eval-v1")
    assert sorted(benign(hard)) == sorted(SPLITS["benign"]["test-hard"])
    assert sorted(attacks(hard)) == sorted(attacks(v1))


def test_family_plan_keeps_v1_benign_sessions_and_attacks_unseen_families():
    family, v1 = plan_of("defender-eval-family-v1"), plan_of("defender-eval-v1")
    assert sorted(benign(family)) == sorted(benign(v1))
    assert len(attacks(family)) == 200
    assert set(attacks(family)) <= set(SPLITS["payloads"]["test-family"])


def test_plans_are_deterministic_and_have_distinct_env_seeds():
    for name in harness.DEFENDER_SUITES:
        plan = plan_of(name)
        assert plan == plan_of(name)
        assert len({p.seed for p in plan}) == len(plan)


def test_suite_attackers_include_the_scripted_references():
    assert {"corpus-replay", "random-mutation"} <= set(
        harness.DEFENDER_SUITES["defender-eval-v1"].attackers
    )


def run(defender, suite="defender-eval-hard-v1", attacker="corpus-replay"):
    return harness.run_defender_suite(defender, suite, attacker=attacker, backend=FakeBackend())


def test_suite_run_is_reproducible():
    assert run(ModSecDefender(1)) == run(ModSecDefender(1))


def test_every_defender_sees_the_same_sessions():
    sessions = lambda records: [r.session_id for r in records]  # noqa: E731
    assert sessions(run(ModSecDefender(1))) == sessions(run(ModSecDefender(3)))


def test_records_cover_all_planned_sessions():
    plan = plan_of("defender-eval-hard-v1")
    records = run(ModSecDefender(1))
    attack_sessions = {r.session_id for r in records if r.is_attack}
    benign_sessions = {r.session_id for r in records if not r.is_attack}
    assert attack_sessions == {f"atk-{ref}" for ref in attacks(plan)}
    assert benign_sessions == set(benign(plan))


def test_always_block_defender_has_full_tpr_and_fpr():
    records = run(FixedDefender(Action.BLOCK))
    assert metrics.tpr(records) == 1.0 and metrics.fpr(records) == 1.0


def test_always_allow_defender_detects_nothing_and_never_blocks_benign_traffic():
    records = run(FixedDefender(Action.ALLOW))
    assert metrics.tpr(records) == 0.0 and metrics.fpr(records) == 0.0


def test_agent_style_defender_never_sees_ground_truth_keys():
    defender = FixedDefender(Action.ALLOW)
    run(defender)
    assert defender.seen_info_keys
    assert not any(key.startswith("gt_") for key in defender.seen_info_keys)


def test_unknown_suite_and_wrong_role_are_rejected():
    with pytest.raises(KeyError, match="no-such-suite"):
        run(ModSecDefender(1), suite="no-such-suite")
    attacker_like = FixedDefender(Action.ALLOW)
    attacker_like.role = "attacker"
    with pytest.raises(ValueError, match="defender"):
        run(attacker_like)


@pytest.mark.parametrize("suite", sorted(harness.DEFENDER_SUITES))
@pytest.mark.parametrize("attacker", ["corpus-replay", "random-mutation"])
def test_every_suite_runs_with_every_scripted_attacker(suite, attacker):
    records = run(ModSecDefender(2), suite=suite, attacker=attacker)
    assert any(r.is_attack for r in records) and any(not r.is_attack for r in records)


def test_attacker_outside_the_suite_is_rejected():
    with pytest.raises(ValueError, match="ATK-REF-0"):
        run(ModSecDefender(1), attacker="ATK-REF-0")
