"""F4-T02: incremental surrogate and validation calibration."""

import numpy as np
import pytest

from wafarena.agents.dyna.surrogate import SurrogateModel, calibration_metrics
from wafarena.attackers.base import Response


def _two_class_examples() -> tuple[np.ndarray, np.ndarray]:
    features = np.zeros((2, 256), dtype=np.float32)
    features[0, 0] = 1.0
    features[1, 1] = 1.0
    return features, np.array([Response.PASS_NO_EFFECT, Response.BLOCKED])


@pytest.mark.parametrize("hidden_dim", [None, 16])
def test_separable_send_responses_are_learned_incrementally(hidden_dim):
    """F4-T02: both model variants learn separable synthetic SEND labels."""
    features, labels = _two_class_examples()
    model = SurrogateModel(hidden_dim=hidden_dim, learning_rate=0.1, seed=7)
    for _ in range(200):
        for feature, label in zip(features, labels, strict=True):
            loss = model.update(feature, label)
            assert np.isfinite(loss)
    assert [model.predict_response(x) for x in features] == list(labels)
    assert all(model.predict_proba(x).max() > 0.95 for x in features)


def test_predictions_use_only_ngram_features_and_are_normalized():
    """F4-T02: session features cannot enter the 256-feature surrogate."""
    model = SurrogateModel(hidden_dim=None, learning_rate=0.1, seed=2)
    obs = np.zeros(288, dtype=np.float32)
    obs[0] = 1.0
    obs[256:] = 1.0
    probabilities = model.predict_proba(obs)
    assert probabilities.shape == (5,)
    assert np.all(np.isfinite(probabilities))
    assert np.all(probabilities >= 0.0)
    assert probabilities.sum() == pytest.approx(1.0)
    np.testing.assert_allclose(probabilities, model.predict_proba(obs[:256]))


def test_seed_reproduces_initial_probabilities():
    """F4-T02: seeded construction is reproducible."""
    obs = np.ones(256, dtype=np.float32)
    first = SurrogateModel(hidden_dim=16, learning_rate=0.1, seed=5)
    second = SurrogateModel(hidden_dim=16, learning_rate=0.1, seed=5)
    np.testing.assert_allclose(first.predict_proba(obs), second.predict_proba(obs))


@pytest.mark.parametrize("label", [Response.NONE, -1, 6])
def test_update_rejects_non_send_response_labels(label):
    """F4-T02: NONE and out-of-range labels are not SEND outcomes."""
    model = SurrogateModel(hidden_dim=None, learning_rate=0.1, seed=0)
    with pytest.raises(ValueError, match="response"):
        model.update(np.zeros(256, dtype=np.float32), label)


def test_predict_rejects_wrong_observation_shape():
    """F4-T02: malformed features fail before inference."""
    model = SurrogateModel(hidden_dim=None, learning_rate=0.1, seed=0)
    with pytest.raises(ValueError, match="observation"):
        model.predict_proba(np.zeros(255, dtype=np.float32))


def test_calibration_metrics_match_hand_calculation():
    """F4-T02: accuracy, ECE, and multiclass Brier use val probabilities."""
    probabilities = np.array([[0.8, 0.2, 0, 0, 0], [0.4, 0.6, 0, 0, 0]])
    metrics = calibration_metrics(probabilities, np.array([1, 2]), bins=2)
    assert metrics["accuracy"] == pytest.approx(1.0)
    assert metrics["ece"] == pytest.approx(0.3)
    assert metrics["brier"] == pytest.approx(0.2)


def test_calibration_rejects_empty_validation_set():
    """F4-T02: no validation observations cannot produce calibration scores."""
    with pytest.raises(ValueError, match="empty"):
        calibration_metrics(np.empty((0, 5)), np.empty(0))


def test_calibration_rejects_column_shaped_labels():
    """A label column must not broadcast against one-dimensional predictions."""
    probabilities = np.array([[0.8, 0.2, 0, 0, 0], [0.4, 0.6, 0, 0, 0]])
    with pytest.raises(ValueError, match="one-dimensional"):
        calibration_metrics(probabilities, np.array([[1], [2]]))
