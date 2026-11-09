"""Read only published experiment summaries for the dashboard."""

import csv
from pathlib import Path

REQUIRED = {
    "EXP-I1_curve.csv": {
        "condition",
        "generation",
        "role",
        "reference",
        "metric",
        "mean",
        "git_sha",
    },
    "EXP-H1.csv": {"defender", "method", "real_queries", "er_mean", "git_shas"},
    "EXP-I2_matrix.csv": {
        "defender_generation",
        "attacker_generation",
        "mean_er",
        "source_git_sha",
        "eval_git_sha",
    },
    "RQ5_final.csv": {"exp_id", "attacker", "defender", "tpr", "fpr", "er_d", "eval_run_ids"},
    "EXP-R1_gap.csv": {
        "role",
        "agent",
        "metric",
        "gap_mean",
        "n_defined",
        "fast_run_ids",
        "real_run_ids",
    },
}


def _read(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path.name}: missing required columns")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path.name}: empty summary")
    return rows


def load_results(root: Path) -> dict[str, list[dict[str, str]]]:
    """Load versioned runs; fail closed if the expected sources or matrix are absent."""
    root = Path(root)
    data = {name: _read(root / name, fields) for name, fields in REQUIRED.items()}
    if {r["git_sha"] for r in data["EXP-I1_curve.csv"]} != {"eea6f78"}:
        raise ValueError("EXP-I1 source SHA mismatch")
    matrix = data["EXP-I2_matrix.csv"]
    if any(r["source_git_sha"] != "eea6f78" or r["eval_git_sha"] != "85524f0" for r in matrix):
        raise ValueError("EXP-I2 source SHA mismatch")
    positions = {(int(r["defender_generation"]), int(r["attacker_generation"])) for r in matrix}
    if positions != {(d, a) for d in range(1, 9) for a in range(1, 9)} or len(matrix) != 64:
        raise ValueError("EXP-I2 matrix must have 64 cells")
    if any(
        not r["eval_run_ids"]
        or not (
            "__bf14912" in r["eval_run_ids"]
            or r["eval_run_ids"] == "modsec-defender-suites__d9d7d49"
        )
        for r in data["RQ5_final.csv"]
    ):
        raise ValueError("RQ5 source run mismatch")
    if any(r["git_shas"] not in {"7714621", "9d54cd2"} for r in data["EXP-H1.csv"]):
        raise ValueError("EXP-H1 source SHA mismatch")
    if any(
        "__c1d2f4d" not in r["fast_run_ids"] or "__c1d2f4d" not in r["real_run_ids"]
        for r in data["EXP-R1_gap.csv"]
    ):
        raise ValueError("EXP-R1 source run mismatch")
    return data


def i1_tpr_rows(rows: list[dict[str, str]], reference: str) -> list[dict]:
    """Return observed defender TPR points in generation order."""
    selected = [
        {"condition": r["condition"], "generation": int(r["generation"]), "tpr": float(r["mean"])}
        for r in rows
        if r["role"] == "defender" and r["reference"] == reference and r["metric"] == "tpr"
    ]
    return sorted(selected, key=lambda r: (r["generation"], r["condition"]))
