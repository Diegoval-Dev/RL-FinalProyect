"""Aggregate EXP-H2 ER curves around the defender switch in real-query space."""

import csv
from pathlib import Path

import numpy as np
import yaml

METHODS = ("dyna-20-switch", "dyna-plus-1e-3-switch", "dyna-plus-1e-2-switch")
SWITCH_STEP = 100_000
TOTAL_STEPS = 200_000
EVAL_STEP = 10_000


def _run_rows(path: Path, *, method: str, seed: int) -> tuple[list[dict], dict]:
    meta = yaml.safe_load((path / "meta.yaml").read_text())
    config = yaml.safe_load((path / "config.resolved.yaml").read_text())
    if (
        meta.get("dirty")
        or "duration_s" not in meta
        or meta.get("exp_id") != "EXP-H2"
        or meta.get("run_name") != method
        or meta.get("seed") != seed
        or meta.get("run_id") != f"EXP-H2__{method}__s{seed}__{meta.get('git_sha')}"
        or config.get("exp_id") != "EXP-H2"
        or config.get("run_name") != method
        or config.get("seeds") != [seed]
        or config.get("train", {}).get("total_steps") != TOTAL_STEPS
        or config.get("env", {}).get("switch_at") != SWITCH_STEP
    ):
        raise ValueError(f"invalid EXP-H2 provenance: {path}")
    with (path / "eval.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if [int(row["step"]) for row in rows] != list(range(EVAL_STEP, TOTAL_STEPS + 1, EVAL_STEP)):
        raise ValueError(f"incomplete EXP-H2 validation curve: {path}")
    if any(
        row["suite"] != "attacker-val-v1"
        or row["defender"] != ("modsec-pl1" if int(row["step"]) <= SWITCH_STEP else "DEF-REF-1")
        or row["phase"] != ("pre" if int(row["step"]) <= SWITCH_STEP else "post")
        for row in rows
    ):
        raise ValueError(f"invalid EXP-H2 defender sequence: {path}")
    queries = [int(row["real_queries"]) for row in rows]
    if any(right < left for left, right in zip(queries, queries[1:], strict=False)):
        raise ValueError(f"real queries decrease: {path}")
    return rows, meta


def _interpolate(rows: list[dict], switch_queries: int, grid: np.ndarray) -> np.ndarray:
    latest = {int(row["real_queries"]) - switch_queries: float(row["evasion_rate"]) for row in rows}
    x = np.array(sorted(latest), dtype=float)
    y = np.array([latest[int(query)] for query in x], dtype=float)
    return np.interp(grid, x, y)


def _interval(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = values.mean(axis=0)
    rng = np.random.default_rng(0)
    indices = rng.integers(len(values), size=(2000, len(values)))
    boot = values[indices].mean(axis=1)
    low, high = np.quantile(boot, [0.025, 0.975], axis=0)
    return mean, low, high


def _recovery(method: str, seed: int, rows: list[dict], meta: dict) -> dict:
    switch_queries = int(rows[9]["real_queries"])
    baseline = float(rows[9]["evasion_rate"])
    post = rows[10:]
    recovered = next((row for row in post if float(row["evasion_rate"]) >= baseline), None)
    if baseline <= 0:
        status, recovery_queries = "baseline_zero", ""
    elif recovered is None:
        status, recovery_queries = "not_recovered", ""
    else:
        status = "recovered"
        recovery_queries = int(recovered["real_queries"]) - switch_queries
    return {
        "method": method,
        "seed": seed,
        "run_id": meta["run_id"],
        "git_sha": meta["git_sha"],
        "switch_queries": switch_queries,
        "pre_switch_er": baseline,
        "first_post_switch_er": float(post[0]["evasion_rate"]),
        "best_post_switch_er": max(float(row["evasion_rate"]) for row in post),
        "status": status,
        "recovery_queries": recovery_queries,
    }


def summarize_h2(results_root: Path) -> tuple[list[dict], list[dict]]:
    """Require all 30 runs, then align each validation curve at its own switch query count."""
    curve: list[dict] = []
    recovery: list[dict] = []
    revisions: set[str] = set()
    for method in METHODS:
        paths = [results_root / "EXP-H2" / method / f"s{seed}" for seed in range(10)]
        loaded = [_run_rows(path, method=method, seed=seed) for seed, path in enumerate(paths)]
        runs = [rows for rows, _ in loaded]
        metas = [meta for _, meta in loaded]
        revisions.update(meta["git_sha"] for meta in metas)
        recovery.extend(
            _recovery(method, seed, rows, meta) for seed, (rows, meta) in enumerate(loaded)
        )
        switches = [int(rows[9]["real_queries"]) for rows in runs]
        run_ids = " ".join(meta["run_id"] for meta in metas)
        for phase, segment, points in (("pre", slice(None, 10), 11), ("post", slice(10, None), 10)):
            phase_rows = [rows[segment] for rows in runs]
            start = max(
                int(rows[0]["real_queries"]) - switch
                for rows, switch in zip(phase_rows, switches, strict=True)
            )
            end = min(
                int(rows[-1]["real_queries"]) - switch
                for rows, switch in zip(phase_rows, switches, strict=True)
            )
            if end < start:
                raise ValueError(f"no shared query range for {method} {phase}")
            grid = np.linspace(start, end, points)
            values = np.vstack(
                [
                    _interpolate(rows, switch, grid)
                    for rows, switch in zip(phase_rows, switches, strict=True)
                ]
            )
            mean, low, high = _interval(values)
            for index, query in enumerate(grid):
                curve.append(
                    {
                        "method": method,
                        "phase": phase,
                        "seeds": 10,
                        "relative_queries": float(query),
                        "er_mean": float(mean[index]),
                        "er_ci_low": float(low[index]),
                        "er_ci_high": float(high[index]),
                        "run_ids": run_ids,
                        "git_sha": metas[0]["git_sha"],
                    }
                )
    if len(revisions) != 1:
        raise ValueError("EXP-H2 runs use different code revisions")
    return curve, recovery


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("empty EXP-H2 report")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
