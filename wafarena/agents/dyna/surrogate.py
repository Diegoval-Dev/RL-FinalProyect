"""Incremental model of the attacker-visible response to a SEND action (F4-T02)."""

import numpy as np
import torch
from torch import nn

from wafarena.attackers.base import Response
from wafarena.envs.attacker_obs import NGRAM_SIZE, OBS_SIZE

SEND_CLASSES = 5  # Response values 1..5; NONE is not a SEND outcome.


def _features(obs: np.ndarray) -> torch.Tensor:
    values = np.asarray(obs, dtype=np.float32)
    if values.ndim != 1 or values.size not in (NGRAM_SIZE, OBS_SIZE):
        raise ValueError(f"observation must be a {NGRAM_SIZE}- or {OBS_SIZE}-element vector")
    if not np.isfinite(values).all():
        raise ValueError("observation must contain only finite values")
    return torch.from_numpy(values[:NGRAM_SIZE].copy())


class SurrogateModel:
    """Linear softmax model or small MLP, updated after each real SEND.

    Inputs are the 256 payload ngram features. A full 288-element attacker observation is accepted
    for convenience, but its response history, counters, and family block are discarded.
    """

    def __init__(self, *, hidden_dim: int | None, learning_rate: float, seed: int) -> None:
        if hidden_dim is not None and hidden_dim <= 0:
            raise ValueError("hidden_dim must be positive or None")
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            if hidden_dim is None:
                self._network: nn.Module = nn.Linear(NGRAM_SIZE, SEND_CLASSES)
            else:
                self._network = nn.Sequential(
                    nn.Linear(NGRAM_SIZE, hidden_dim),
                    nn.Tanh(),
                    nn.Linear(hidden_dim, SEND_CLASSES),
                )
        self._optimizer = torch.optim.SGD(self._network.parameters(), lr=learning_rate)

    def predict_proba(self, obs: np.ndarray) -> np.ndarray:
        """Return probabilities for PASS_EFFECT through RATE_LIMITED, in enum order."""
        with torch.no_grad():
            logits = self._network(_features(obs))
            return torch.softmax(logits, dim=0).numpy()

    def predict_response(self, obs: np.ndarray) -> Response:
        """Return the most likely attacker-visible SEND response."""
        return Response(int(np.argmax(self.predict_proba(obs))) + 1)

    def update(self, obs: np.ndarray, response: int | Response) -> float:
        """Take one SGD step on a labeled real SEND and return its cross-entropy loss."""
        label = int(response)
        if not 1 <= label <= SEND_CLASSES:
            raise ValueError("response must be a SEND class in 1..5")
        logits = self._network(_features(obs)).unsqueeze(0)
        target = torch.tensor([label - 1], dtype=torch.long)
        loss = nn.functional.cross_entropy(logits, target)
        self._optimizer.zero_grad()
        loss.backward()
        self._optimizer.step()
        return float(loss.item())


def calibration_metrics(
    probabilities: np.ndarray, responses: np.ndarray, *, bins: int = 10
) -> dict[str, float]:
    """Compute accuracy, confidence ECE, and multiclass Brier score on held-out SENDs."""
    probs = np.asarray(probabilities, dtype=np.float64)
    labels = np.asarray(responses, dtype=np.int64)
    if probs.ndim != 2 or probs.shape[1] != SEND_CLASSES or probs.shape[0] != labels.size:
        raise ValueError("probabilities must have shape (n, 5) matching responses")
    if labels.size == 0:
        raise ValueError("empty validation set")
    if bins <= 0:
        raise ValueError("bins must be positive")
    if np.any((labels < 1) | (labels > SEND_CLASSES)):
        raise ValueError("responses must be SEND classes in 1..5")
    if not np.isfinite(probs).all() or np.any(probs < 0) or not np.allclose(probs.sum(1), 1):
        raise ValueError("probabilities must be finite, nonnegative, and sum to one")

    predicted = probs.argmax(axis=1) + 1
    correct = predicted == labels
    confidence = probs.max(axis=1)
    bin_ids = np.minimum((confidence * bins).astype(int), bins - 1)
    ece = 0.0
    for bin_id in range(bins):
        in_bin = bin_ids == bin_id
        if in_bin.any():
            ece += float(in_bin.mean() * abs(correct[in_bin].mean() - confidence[in_bin].mean()))
    one_hot = np.eye(SEND_CLASSES)[labels - 1]
    brier = np.square(probs - one_hot).sum(axis=1).mean()
    return {"accuracy": float(correct.mean()), "ece": ece, "brier": float(brier)}
