"""Hyperparameter schedules read from the experiment YAML (experimentos.md).

A schedule is either a constant (`epsilon: 0.1`) or a linear decay
(`epsilon: {start: 1.0, end: 0.05, decay_steps: 50000}`), evaluated at the agent's own step count.
"""

from collections.abc import Callable
from typing import Any


def linear_schedule(spec: Any) -> Callable[[int], float]:
    if isinstance(spec, int | float):
        value = float(spec)
        return lambda step: value
    start, end, decay_steps = float(spec["start"]), float(spec["end"]), int(spec["decay_steps"])
    if decay_steps <= 0:
        raise ValueError("decay_steps must be positive")

    def value_at(step: int) -> float:
        fraction = min(max(step, 0) / decay_steps, 1.0)
        return start + fraction * (end - start)

    return value_at
