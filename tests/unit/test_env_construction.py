"""F2-T01: environments are constructible as the contracts document (gym.make kwargs)."""

import gymnasium as gym
import pytest

import wafarena.envs  # noqa: F401  (registers the envs)
from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs import resolve
from wafarena.envs.backends.fake import FakeBackend


@pytest.fixture(autouse=True)
def fake_named_backends(monkeypatch):
    monkeypatch.setattr(resolve, "make_backend", lambda kind: FakeBackend())


def test_resolve_backend_passes_objects_through():
    backend = FakeBackend()
    assert resolve.resolve_backend(backend) is backend


def test_resolve_backend_builds_named_backend():
    assert isinstance(resolve.resolve_backend("fast"), FakeBackend)


def test_resolve_defender_defaults_to_pl1():
    assert resolve.resolve_defender(None)._index == ModSecDefender(1)._index


def test_resolve_defender_from_modsec_spec():
    defender = resolve.resolve_defender({"type": "modsec", "paranoia_level": 3})
    assert defender._index == ModSecDefender(3)._index


def test_resolve_defender_passes_objects_through():
    defender = ModSecDefender(2)
    assert resolve.resolve_defender(defender) is defender


def test_resolve_defender_rejects_unknown_type():
    with pytest.raises(ValueError, match="unknown defender type"):
        resolve.resolve_defender({"type": "nope"})


def test_resolve_defender_checkpoint_needs_an_existing_checkpoint():
    """Implemented in F3-T08 (test_policy_gradient.py covers a real one); a bad path fails."""
    with pytest.raises(FileNotFoundError):
        resolve.resolve_defender({"type": "checkpoint", "path": "no/such/checkpoint"})


def test_resolve_attacker_spec_accepts_string_and_dict():
    assert resolve.resolve_attacker_type("random_mutation") == "random_mutation"
    assert resolve.resolve_attacker_type({"type": "corpus_replay"}) == "corpus_replay"
    assert resolve.resolve_attacker_type(None) == "corpus_replay"


@pytest.mark.parametrize("spec", [{"type": "checkpoint", "path": "x"}, {"type": "pool"}])
def test_resolve_attacker_spec_checkpoint_types_not_available_yet(spec):
    with pytest.raises(NotImplementedError):
        resolve.resolve_attacker_type(spec)


def test_attacker_env_from_documented_gym_make_kwargs():
    env = gym.make(
        "WafArena/Attacker-v0",
        backend="fast",
        defender={"type": "modsec", "paranoia_level": 2},
        split="train",
    )
    obs, info = env.reset(seed=0)
    assert obs.shape == (288,)
    assert 0 <= info["abstract_state"] < 120
    env.step(env.action_space.sample())


def test_defender_env_from_documented_gym_make_kwargs():
    env = gym.make(
        "WafArena/Defender-v0",
        backend="fast",
        attacker={"type": "corpus_replay"},
        split="train",
        attack_ratio=0.5,
    )
    obs, _info = env.reset(seed=0)
    assert obs.shape == (37,)
    env.step(0)
