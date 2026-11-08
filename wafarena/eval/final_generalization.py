"""Validation-only selection and final defender generalization helpers."""

import hashlib
import json
import math
import os
import statistics
from pathlib import Path

from wafarena.eval.harness import DEFENDER_SUITES, build_session_plan
from wafarena.eval.stats import bootstrap_ci


def select_pool_champion(rows: list[dict], *, source_sha: str, fpr_cap: float) -> dict:
    """Rank final pool defenders against all seven prior attackers on `val`."""
    grouped = {seed: {} for seed in (0, 1, 2)}
    for row in rows:
        if row.get("condition") != "pool" or int(row["defender_generation"]) != 8:
            continue
        seed = int(row["seed"])
        opponent = int(row["attacker_generation"])
        if (
            seed not in grouped
            or opponent not in range(1, 8)
            or row.get("split") != "val"
            or row.get("git_sha") != source_sha
            or row.get("run_id") != f"EXP-I1__pool__s{seed}__{source_sha}"
            or int(row["sessions"]) != 40
        ):
            raise ValueError("pool champion requires matching val history")
        if opponent in grouped[seed]:
            raise ValueError(f"duplicate historical opponent {opponent} for seed {seed}")
        tpr, fpr = float(row["tpr"]), float(row["fpr"])
        if not all(math.isfinite(value) and 0 <= value <= 1 for value in (tpr, fpr)):
            raise ValueError("invalid val TPR or FPR")
        grouped[seed][opponent] = (tpr, fpr)
    candidates = []
    for seed, matches in grouped.items():
        if set(matches) != set(range(1, 8)):
            raise ValueError(f"seed {seed} needs seven historical val opponents")
        fprs = {item[1] for item in matches.values()}
        if len(fprs) != 1:
            raise ValueError(f"inconsistent val FPR for seed {seed}")
        fpr = fprs.pop()
        candidates.append(
            {
                "seed": seed,
                "run_id": f"EXP-I1__pool__s{seed}__{source_sha}",
                "mean_tpr": statistics.mean(item[0] for item in matches.values()),
                "fpr": fpr,
                "feasible": fpr <= fpr_cap,
            }
        )
    feasible_count = sum(row["feasible"] for row in candidates)
    if feasible_count:
        candidates.sort(
            key=lambda row: (not row["feasible"], -row["mean_tpr"], row["fpr"], row["seed"])
        )
    else:
        candidates.sort(key=lambda row: (row["fpr"], -row["mean_tpr"], row["seed"]))
    return {
        "winner_seed": candidates[0]["seed"],
        "feasible_count": feasible_count,
        "fpr_cap": fpr_cap,
        "candidates": candidates,
    }


def rank_dyna(candidates: list[dict]) -> list[dict]:
    """Rank H1 Dyna checkpoints by validation ER, then compute cost and seed."""
    if not candidates:
        raise ValueError("no Dyna-Q candidates")
    for row in candidates:
        if (
            row["method"] not in {"dyna-5", "dyna-20", "dyna-50"}
            or not 0 <= row["seed"] <= 9
            or row["planning_steps"] != int(row["method"].split("-")[1])
            or not math.isfinite(row["val_er"])
            or not 0 <= row["val_er"] <= 1
        ):
            raise ValueError("invalid Dyna-Q candidate")
    return sorted(
        candidates,
        key=lambda row: (-row["val_er"], row["planning_steps"], row["seed"]),
    )


def i5_plan():
    """Use the existing fixed defender test session plan for unseen attackers."""
    return build_session_plan(DEFENDER_SUITES["defender-eval-v1"])


def aggregate_generalization(
    cells: list[dict], *, exp_id: str, champion_seed: int, attacker_id: str = ""
) -> list[dict]:
    """Report three defender seeds, the selected checkpoint, and fixed baselines."""
    selfplay = [row for row in cells if row["defender"] == "selfplay"]
    if len(selfplay) != 3 or {row["seed"] for row in selfplay} != {0, 1, 2}:
        raise ValueError("generalization requires three self-play seeds")
    references = {}
    for name in ("DEF-REF-1", "modsec-pl2"):
        matching = [row for row in cells if row["defender"] == name]
        if len(matching) != 1 or matching[0]["seed"] is not None:
            raise ValueError(f"generalization requires one fixed {name} baseline")
        references[name] = matching[0]
    if len(cells) != 5:
        raise ValueError("unexpected generalization cell")
    if champion_seed not in (0, 1, 2):
        raise ValueError("champion seed outside the pool")
    champion = next(row for row in selfplay if row["seed"] == champion_seed)

    def report(name: str, source: list[dict]) -> dict:
        result = {
            "exp_id": exp_id,
            "attacker": attacker_id,
            "defender": name,
            "n_seeds": len(source),
            "eval_run_ids": " ".join(str(row.get("eval_run_id", "")) for row in source).strip(),
        }
        for metric in ("tpr", "fpr", "er_d"):
            values = [float(row[metric]) for row in source if row[metric] is not None]
            defined = [value for value in values if math.isfinite(value)]
            if any(not 0 <= value <= 1 for value in defined):
                raise ValueError(f"invalid {metric} in {name}")
            result[f"{metric}_n_defined"] = len(defined)
            result[metric] = statistics.mean(defined) if defined else None
            result[f"{metric}_low"] = None
            result[f"{metric}_high"] = None
            if len(source) == 3 and len(defined) == 3:
                ci = bootstrap_ci(defined)
                result[f"{metric}_low"] = ci.low
                result[f"{metric}_high"] = ci.high
        return result

    return [
        report("selfplay-cohort", sorted(selfplay, key=lambda row: row["seed"])),
        report("selfplay-champion", [champion]),
        report("DEF-REF-1", [references["DEF-REF-1"]]),
        report("modsec-pl2", [references["modsec-pl2"]]),
    ]


def file_sha256(path: Path) -> str:
    """Fingerprint a checkpoint's weight file for cache provenance."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cached_cell(path: Path, expected: dict, compute) -> dict:
    """Read a complete cell or compute and atomically store it once."""
    path = Path(path)
    if path.exists():
        row = json.loads(path.read_text())
    else:
        metrics = compute()
        row = {**expected, **metrics}
        for key, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                row[key] = None
        _validate_cell(row, expected, path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(row, indent=2, allow_nan=False) + "\n")
        os.replace(temporary, path)
    _validate_cell(row, expected, path)
    return row


def _validate_cell(row: dict, expected: dict, path: Path) -> None:
    if any(row.get(key) != value for key, value in expected.items()):
        raise ValueError(f"stale generalization cell: {path}")
    if row.get("sessions") != expected.get("sessions", 2000):
        raise ValueError(f"incomplete generalization cell: {path}")
    for key in ("tpr", "fpr", "er_d"):
        value = row.get(key)
        if value is not None and (
            type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1
        ):
            raise ValueError(f"invalid {key} in generalization cell: {path}")
