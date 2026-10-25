"""Selects and publishes DEF-REF-1 (fase-3 plan, «Regla de selección de DEF-REF-1»; ADR-0010).

Among every defender trained in EXP-F5 (results/EXP-F5/<run_name>/s<seed>/), the one with the
highest TPR on `val` subject to FPR on `val` <= FPR of modsec-pl2 on `val` (`fpr_cap`, measured
by the runner); if none qualifies, the one with the lowest FPR. Only `val` decides: the order is
the runner's selection rule followed by the tie-break of ADR-0010, all on `val`:

    1. feasible (fpr <= fpr_cap) before infeasible
    2. higher TPR if feasible, lower FPR if not
    3. lower FPR, 4. higher F1
    5. higher mean val TPR of the checkpoint's run_name over its seeds (the steadier configuration)
    6. lower seed

Writes results/summary/DEF-REF-1_selection.csv (every candidate, in rank order) and copies the
winner to checkpoints/refs/DEF-REF-1/ with `agent_id: DEF-REF-1` and the selection in
`eval_summary`; the training provenance (`train.run_id`, `train.git_sha`) is kept as it was.

Usage: uv run python scripts/select_def_ref.py [--results DIR] [--refs DIR]
"""

import argparse
import csv
import json
import shutil
import statistics
from pathlib import Path

import yaml

REF_ID = "DEF-REF-1"
SOURCE_EXP = "EXP-F5"
OUTPUT = Path("results/summary/DEF-REF-1_selection.csv")


def candidates(results: Path) -> list[dict]:
    rows = []
    for final in sorted((results / SOURCE_EXP).glob("*/s*/final_eval.json")):
        data = json.loads(final.read_text())
        rows.append(
            {
                "run_name": final.parent.parent.name,
                "seed": int(final.parent.name[1:]),
                "val_tpr": data["val"]["tpr"],
                "val_fpr": data["val"]["fpr"],
                "val_f1": data["val"]["f1"],
                "fpr_cap": data["fpr_cap"],
                "best_step": data["best_step"],
                "checkpoint": str(final.parent / "checkpoint"),
            }
        )
    for row in rows:
        same = [r["val_tpr"] for r in rows if r["run_name"] == row["run_name"]]
        row["run_name_mean_val_tpr"] = statistics.mean(same)
        row["feasible"] = int(row["val_fpr"] <= row["fpr_cap"])
    return rows


def rank_key(row: dict) -> tuple:
    feasible = bool(row["feasible"])
    return (
        feasible,
        row["val_tpr"] if feasible else -row["val_fpr"],
        -row["val_fpr"],
        row["val_f1"],
        row["run_name_mean_val_tpr"],
        -row["seed"],
    )


def publish(winner: dict, refs: Path) -> Path:
    target = refs / REF_ID
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(winner["checkpoint"], target)
    meta_path = target / "meta.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["agent_id"] = REF_ID
    meta["eval_summary"] = {
        "suite": "defender-val-v1",
        "tpr": winner["val_tpr"],
        "fpr": winner["val_fpr"],
        "f1": winner["val_f1"],
        "fpr_cap": winner["fpr_cap"],
        "selected_from": f"{SOURCE_EXP}/{winner['run_name']}/s{winner['seed']}",
        "selection": "scripts/select_def_ref.py (fase-3 plan rule + ADR-0010 tie-break, val only)",
    }
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False))
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--refs", type=Path, default=Path("checkpoints/refs"))
    args = parser.parse_args()
    ranked = sorted(candidates(args.results), key=rank_key, reverse=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as handle:
        columns = ["rank", *[k for k in ranked[0] if k != "checkpoint"]]
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({"rank": i + 1, **row} for i, row in enumerate(ranked))
    target = publish(ranked[0], args.refs)
    print(f"{REF_ID} = {ranked[0]['run_name']} s{ranked[0]['seed']} -> {target}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
