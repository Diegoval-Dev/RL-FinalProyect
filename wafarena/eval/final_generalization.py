"""Validation-only selection and final defender generalization helpers."""

import math
import statistics


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
