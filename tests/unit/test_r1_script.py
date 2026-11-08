"""EXP-R1 rejects incompatible checkpoint sources before live evaluation."""

import json

import pytest

from scripts.run_r1 import discover_sources
from wafarena.eval.real_gap import load_spec


def test_discovery_rejects_tampered_champion_selection(tmp_path, monkeypatch):
    selection = json.loads(open("results/summary/EXP-I3_selection.json").read())
    selection["winner_seed"] = 2
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(selection))
    config = load_spec("configs/eval/EXP-R1/real-validation.yaml")
    config["champion_selection"] = str(path)
    monkeypatch.setattr(
        "scripts.run_r1.discover_pool_defenders",
        lambda root, sha: [
            {"seed": seed, "path": tmp_path / str(seed), "source_run_id": f"pool-s{seed}"}
            for seed in range(3)
        ],
    )
    with pytest.raises(ValueError, match="champion"):
        discover_sources(config)
