"""Resolve the declarative constructor arguments of the environments (env-* contracts).

`gymnasium.make` passes plain data (`backend="fast"`, `defender={"type": "modsec", ...}`); direct
construction passes ready objects. Both forms are accepted.
"""

from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs.backends import make_backend
from wafarena.envs.backends.base import Backend


def resolve_backend(backend: Backend | str) -> Backend:
    return make_backend(backend) if isinstance(backend, str) else backend


def resolve_defender(defender):
    """None → ModSecurity PL1; a `{"type": ...}` spec → the policy it names; objects pass."""
    if defender is None:
        return ModSecDefender(1)
    if not isinstance(defender, dict):
        return defender
    kind = defender.get("type")
    if kind == "modsec":
        return ModSecDefender(int(defender["paranoia_level"]))
    if kind == "checkpoint":
        raise NotImplementedError("defender type 'checkpoint' needs load_checkpoint (F2-T02)")
    raise ValueError(f"unknown defender type {kind!r}")


def resolve_attacker_type(attacker) -> str:
    """Name of a built-in scripted attacker from `"name"`, `{"type": "name"}` or None."""
    if attacker is None:
        return "corpus_replay"
    kind = attacker if isinstance(attacker, str) else attacker.get("type")
    if kind in ("checkpoint", "pool"):
        raise NotImplementedError(f"attacker type {kind!r} needs load_checkpoint (F2-T02/T10)")
    return kind
