"""F4-T05: each generation is judged on fixed validation opponents."""

from pathlib import Path

from wafarena.agents import load_checkpoint
from wafarena.envs.backends.fake import FakeBackend
from wafarena.selfplay.evaluation import evaluate_generation

ROOT = Path(__file__).parents[2]


def test_evaluation_reports_each_fixed_reference_on_val():
    backend = FakeBackend()
    attacker = load_checkpoint(ROOT / "checkpoints/refs/ATK-REF-1")
    defender = load_checkpoint(ROOT / "checkpoints/refs/DEF-REF-1")
    result = evaluate_generation(
        attacker,
        defender,
        backend,
        attacker_episodes=2,
        defender_sessions=4,
        attacker_defenders=["modsec-pl1", "DEF-REF-1"],
        defender_attackers=["corpus-replay", "ATK-REF-0"],
    )
    assert result["split"] == "val"
    assert set(result["attacker"]) == {"modsec-pl1", "DEF-REF-1"}
    assert set(result["defender"]) == {"corpus-replay", "ATK-REF-0"}
    assert all(row["episodes"] == 2 for row in result["attacker"].values())
    assert all(row["requests"] >= 4 for row in result["defender"].values())
