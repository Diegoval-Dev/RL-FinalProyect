"""EXP-I3–I5 runner rejects incompatible experiment inputs."""

import csv

import pytest
import yaml

from scripts.run_i345 import discover_pool_defenders, load_modsec_baseline, load_spec


def test_spec_rejects_short_i5_session_plan(tmp_path):
    source = yaml.safe_load(open("configs/selfplay/exp_i345.yaml"))
    path = tmp_path / "spec.yaml"
    source["i5_sessions"] = 200
    path.write_text(yaml.safe_dump(source))
    with pytest.raises(ValueError, match="2000"):
        load_spec(path)


def test_modsec_baseline_requires_matching_suite_and_pl2(tmp_path):
    path = tmp_path / "baseline.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["defender", "suite", "requests", "attack_requests", "tpr", "fpr", "er_d"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "defender": "modsec-pl2",
                "suite": "defender-eval-family-v1",
                "requests": "11066",
                "attack_requests": "812",
                "tpr": "0.9",
                "fpr": "0.0",
                "er_d": "0.0",
            }
        )
    row = load_modsec_baseline(path, "defender-eval-family-v1")
    assert (row["tpr"], row["fpr"], row["er_d"]) == (0.9, 0.0, 0.0)
    assert row["sessions"] == 4000
    assert (row["requests"], row["attack_requests"]) == (11066, 812)
    assert (row["split"], row["attack_split"]) == ("test", "test-family")
    with pytest.raises(ValueError, match="modsec-pl2"):
        load_modsec_baseline(path, "defender-eval-hard-v1")


def test_pool_discovery_rejects_wrong_checkpoint_seed(tmp_path):
    root = tmp_path / "checkpoints"
    for seed in range(3):
        run_id = f"EXP-I1__pool__s{seed}__eea6f78"
        checkpoint = root / run_id / "def-gen-08"
        checkpoint.mkdir(parents=True)
        (checkpoint / "dqn.pt").write_bytes(f"weights-{seed}".encode())
        (checkpoint / "meta.yaml").write_text(
            yaml.safe_dump(
                {
                    "role": "defender",
                    "train": {
                        "exp_id": "EXP-I1",
                        "run_id": run_id,
                        "seed": seed if seed != 2 else 1,
                        "git_sha": "eea6f78",
                        "generation": 8,
                    },
                }
            )
        )
    with pytest.raises(ValueError, match="provenance"):
        discover_pool_defenders(root, "eea6f78")
