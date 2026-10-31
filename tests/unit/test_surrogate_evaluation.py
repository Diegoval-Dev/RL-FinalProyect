"""F4-T02: reproducible surrogate data and validation report."""

import csv
import subprocess

import numpy as np
import pytest
import yaml

from wafarena.agents.dyna.evaluation import (
    collect_send_examples,
    evaluate_surrogate,
    evaluate_variants,
    write_validation_csv,
)
from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs.backends.fake import FakeBackend


def test_collect_send_examples_is_seeded_and_uses_public_responses():
    """F4-T02: the same train episodes produce the same pre-SEND features and labels."""
    kwargs = {"split": "train", "episodes": 6, "seed": 4}
    first_x, first_y = collect_send_examples(FakeBackend(), ModSecDefender(1), **kwargs)
    second_x, second_y = collect_send_examples(FakeBackend(), ModSecDefender(1), **kwargs)
    assert first_x.ndim == 2 and first_x.shape[1] == 256
    assert len(first_x) == len(first_y) > 0
    assert set(first_y).issubset({1, 2, 3, 4, 5})
    np.testing.assert_array_equal(first_x, second_x)
    np.testing.assert_array_equal(first_y, second_y)


@pytest.mark.parametrize("split", ["test", "test-family", "test-hard"])
def test_collect_send_examples_rejects_test_splits(split):
    """F4-T02: frozen test splits cannot supply surrogate fitting or selection data."""
    with pytest.raises(ValueError, match="split"):
        collect_send_examples(FakeBackend(), ModSecDefender(1), split=split, episodes=2, seed=0)


def test_variant_report_has_counts_metrics_and_stable_columns(tmp_path):
    """F4-T02: each variant yields a provenance-bearing val row with class counts."""
    features = np.zeros((4, 256), dtype=np.float32)
    features[:2, 0] = 1.0
    features[2:, 1] = 1.0
    labels = np.array([2, 2, 3, 3])
    variants = [
        {"name": "logistic", "hidden_dim": None, "learning_rate": 0.1},
        {"name": "mlp-16", "hidden_dim": 16, "learning_rate": 0.1},
    ]
    rows = evaluate_variants(
        features,
        labels,
        features,
        labels,
        variants=variants,
        epochs=20,
        seed=0,
        defender="modsec-pl1",
        run_id="F4-T02__surrogate__s0__abc1234",
        git_sha="abc1234",
    )
    assert [row["variant"] for row in rows] == ["logistic", "mlp-16"]
    for row in rows:
        assert row["run_id"] == "F4-T02__surrogate__s0__abc1234"
        assert row["defender"] == "modsec-pl1" and row["split"] == "val"
        assert row["train_samples"] == row["val_samples"] == 4
        assert row["train_class_counts"] == row["val_class_counts"] == "2:2 3:2"
        assert row["train_majority_response"] == 2
        assert row["majority_baseline_accuracy"] == pytest.approx(0.5)
        assert sum(int(part.split(":")[1]) for part in row["pred_class_counts"].split()) == 4
        assert 0 <= row["accuracy"] <= 1
        assert 0 <= row["ece"] <= 1
        assert 0 <= row["brier"] <= 2

    output = tmp_path / "validation.csv"
    write_validation_csv(output, rows)
    with output.open(newline="") as handle:
        written = list(csv.DictReader(handle))
    assert len(written) == 2
    assert list(written[0]) == list(rows[0])


def test_variant_report_rejects_empty_validation_set():
    """F4-T02: metrics are never reported without held-out SEND examples."""
    features = np.zeros((1, 256), dtype=np.float32)
    with pytest.raises(ValueError, match="empty"):
        evaluate_variants(
            features,
            np.array([3]),
            np.empty((0, 256), dtype=np.float32),
            np.empty(0, dtype=int),
            variants=[{"name": "logistic", "hidden_dim": None, "learning_rate": 0.1}],
            epochs=1,
            seed=0,
            defender="modsec-pl1",
            run_id="r",
            git_sha="abc1234",
        )


def test_evaluate_surrogate_writes_provenance_and_validation_csv(tmp_path):
    """F4-T02: the task run has a commit ID and held-out val metrics."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "task"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    (repo / "README.md").write_text("test\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True)

    config = {
        "exp_id": "F4-T02",
        "run_name": "surrogate-validation",
        "seed": 0,
        "train_episodes": 10,
        "val_episodes": 10,
        "epochs": 2,
        "defenders": {"modsec-pl1": {"type": "modsec", "paranoia_level": 1}},
        "variants": [{"name": "logistic", "hidden_dim": None, "learning_rate": 0.1}],
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config))
    run_path = evaluate_surrogate(
        config_path, results_root=tmp_path / "results", repo=repo, backend=FakeBackend()
    )

    with (run_path / "meta.yaml").open() as handle:
        meta = yaml.safe_load(handle)
    with (run_path / "validation.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert meta["run_id"].startswith("F4-T02__surrogate-validation__s0__")
    assert not meta["dirty"] and meta["git_sha"] in meta["run_id"]
    assert meta["duration_s"] >= 0
    assert len(rows) == 1
    assert rows[0]["split"] == "val" and rows[0]["run_id"] == meta["run_id"]
