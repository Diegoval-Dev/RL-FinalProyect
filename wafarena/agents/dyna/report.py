"""Aggregate EXP-H1 validation curves on the cumulative real-query axis."""

import csv
from pathlib import Path

import numpy as np
import yaml

DEFENDERS = ("pl1", "defref1")
METHODS = ("qlearning", "dyna-5", "dyna-20", "dyna-50", "ppo")


def _run_rows(path: Path, *, expected_seed: int) -> list[dict]:
    meta = yaml.safe_load((path / "meta.yaml").read_text())
    if meta["dirty"] or meta["seed"] != expected_seed or meta["exp_id"] != "EXP-H1":
        raise ValueError(f"invalid EXP-H1 provenance: {path}")
    with (path / "eval.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or any(row["suite"] != "attacker-val-v1" for row in rows):
        raise ValueError(f"missing attacker validation rows: {path}")
    queries = [int(row["real_queries"]) for row in rows]
    if any(right < left for left, right in zip(queries, queries[1:], strict=False)):
        raise ValueError(f"real queries decrease: {path}")
    return rows


def _interpolate(rows: list[dict], field: str, grid: np.ndarray) -> np.ndarray:
    latest = {int(row["real_queries"]): float(row[field]) for row in rows}
    x = np.array(sorted(latest), dtype=float)
    y = np.array([latest[int(query)] for query in x], dtype=float)
    return np.interp(grid, x, y)


def _interval(values: np.ndarray, *, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = np.mean(values, axis=0)
    rng = np.random.default_rng(seed)
    indices = rng.integers(len(values), size=(2000, len(values)))
    boot = values[indices].mean(axis=1)
    low, high = np.quantile(boot, [0.025, 0.975], axis=0)
    return mean, low, high


def summarize_h1(results_root: Path) -> list[dict]:
    """Require all planned seeds and interpolate each method over shared real-query support."""
    output: list[dict] = []
    for defender in DEFENDERS:
        for method in METHODS:
            run_name = f"{method}-{defender}"
            expected = 5 if method == "ppo" else 10
            paths = [results_root / "EXP-H1" / run_name / f"s{seed}" for seed in range(expected)]
            runs = [_run_rows(path, expected_seed=seed) for seed, path in enumerate(paths)]
            metas = [yaml.safe_load((path / "meta.yaml").read_text()) for path in paths]
            run_ids = " ".join(meta["run_id"] for meta in metas)
            git_shas = " ".join(sorted({meta["git_sha"] for meta in metas}))
            start = max(int(rows[0]["real_queries"]) for rows in runs)
            end = min(int(rows[-1]["real_queries"]) for rows in runs)
            if end < start:
                raise ValueError(f"no shared query range: {run_name}")
            grid = np.linspace(start, end, 21)
            er = np.vstack([_interpolate(rows, "evasion_rate", grid) for rows in runs])
            er_mean, er_low, er_high = _interval(er, seed=0)
            if method == "ppo":
                accuracy = np.full(len(grid), np.nan)
                minority_recall = np.full(len(grid), np.nan)
            else:
                accuracy = np.vstack(
                    [_interpolate(rows, "surrogate_accuracy", grid) for rows in runs]
                ).mean(axis=0)
                per_seed_recall = np.vstack(
                    [_interpolate(rows, "surrogate_minority_recall", grid) for rows in runs]
                )
                counts = np.isfinite(per_seed_recall).sum(axis=0)
                minority_recall = np.divide(
                    np.nansum(per_seed_recall, axis=0),
                    counts,
                    out=np.full(len(grid), np.nan),
                    where=counts > 0,
                )
            for index, query in enumerate(grid):
                output.append(
                    {
                        "defender": defender,
                        "method": method,
                        "seeds": expected,
                        "real_queries": float(query),
                        "er_mean": float(er_mean[index]),
                        "er_ci_low": float(er_low[index]),
                        "er_ci_high": float(er_high[index]),
                        "surrogate_accuracy_mean": float(accuracy[index]),
                        "surrogate_minority_recall_mean": float(minority_recall[index]),
                        "run_ids": run_ids,
                        "git_shas": git_shas,
                    }
                )
    return output


def write_summary(path: Path, rows: list[dict]) -> None:
    """Write the versioned EXP-H1 summary with stable columns and LF endings."""
    if not rows:
        raise ValueError("empty EXP-H1 summary")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
