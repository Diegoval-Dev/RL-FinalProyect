"""Estimate each bandit arm's mean reward offline (2 000 pulls per arm, fixed seed).

Writes results/summary/bandit_arm_means.csv: the μ used by R(t) in EXP-A1 and EXP-A2.
Run inside the lab: make bandit-arm-means
"""

import csv
import subprocess
import time
from pathlib import Path

from wafarena.envs.backends import make_backend
from wafarena.eval.arm_means import DEFAULT_PULLS_PER_ARM, estimate_arm_means
from wafarena.features.modsec import PARANOIA_LEVELS
from wafarena.mutations.registry import REGISTRY

OUTPUT = Path("results/summary/bandit_arm_means.csv")
SEED = 0


def git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> None:
    backend = make_backend("fast")
    rows = []
    for pl in PARANOIA_LEVELS:
        started = time.monotonic()
        means = estimate_arm_means(backend, {"type": "modsec", "paranoia_level": pl}, seed=SEED)
        stats = backend.cache_stats()
        print(
            f"modsec-pl{pl}: {time.monotonic() - started:6.1f} s, "
            f"cache hit rate {stats['hit_rate']:.2f}, "
            f"best arm {means.argmax()} mu*={means.max():.4f}"
        )
        for arm, mean in enumerate(means):
            rows.append(
                [
                    f"modsec-pl{pl}",
                    arm,
                    REGISTRY[arm].name,
                    f"{mean:.6f}",
                    DEFAULT_PULLS_PER_ARM,
                    SEED,
                    git_sha(),
                ]
            )
    backend.close()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["defender", "arm", "operator", "mu", "pulls", "seed", "git_sha"])
        writer.writerows(rows)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
