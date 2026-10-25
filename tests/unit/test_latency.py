"""F3-T10: the proxy can serve a trained defender, and the latency script replays suite traffic."""

import importlib
import sys
from pathlib import Path

import pytest

from wafarena.agents import save_checkpoint
from wafarena.agents.linear import LinearAgent
from wafarena.defenders.driver import DefenderDriver
from wafarena.defenders.modsec_defender import ModSecDefender

ROOT = Path(__file__).parents[2]


def load_entrypoint(monkeypatch, **env):
    for key in ("PROXY_DEFENDER_CHECKPOINT", "PROXY_PARANOIA_LEVEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    sys.modules.pop("proxy.entrypoint", None)
    return importlib.import_module("proxy.entrypoint")


def test_proxy_defaults_to_modsecurity(monkeypatch):
    assert isinstance(load_entrypoint(monkeypatch)._policy(), ModSecDefender)


def test_proxy_serves_a_defender_checkpoint(monkeypatch, tmp_path):
    agent = LinearAgent("lin", 0, obs_dim=37, n_actions=5)
    save_checkpoint(agent, tmp_path / "def", algo="linear", obs_dim=37, n_actions=5)
    entry = load_entrypoint(monkeypatch, PROXY_DEFENDER_CHECKPOINT=str(tmp_path / "def"))
    assert isinstance(entry._policy(), DefenderDriver)


def test_latency_request_sequence_replays_defender_eval_v1_in_order():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        latency = importlib.import_module("defender_latency")
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    first = latency.request_sequence(50)
    assert len(first) == 50
    assert first == latency.request_sequence(50)  # deterministic
    assert all(path.startswith("/") and len(params) == 1 for path, params in first)


@pytest.mark.parametrize("values", [[1.0, 2.0, 3.0, 4.0]])
def test_latency_rows_report_p50_and_p95(values):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        latency = importlib.import_module("defender_latency")
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    row = latency.row("x", values, len(values))
    assert row["p50_ms"] == "2.500" and float(row["p95_ms"]) > 3.5
