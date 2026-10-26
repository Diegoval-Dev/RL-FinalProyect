"""Selects and publishes ATK-REF-1 (fase-3 plan, F3-T11): the best PPO attacker by evasion rate on
`val` against DEF-REF-1.

Candidates are the 5 seeds of EXP-G3 `ppo-defref1` (PPO trained against DEF-REF-1). Each run's
`final_eval.json` holds its best point on `attacker-val-v1`; the order is the runner's own
selection rule for attackers (experimentos.md): higher `evasion_rate`, then lower `qfe_c`, and,
as a last deterministic tie-break, the lower seed. Only `val` decides.

Writes results/summary/ATK-REF-1_selection.csv and copies the winner to
checkpoints/refs/ATK-REF-1/ with `agent_id: ATK-REF-1` and the selection in `eval_summary`; the
training provenance (`train.run_id`, `train.git_sha`) is kept as it was.

Usage: uv run python scripts/select_atk_ref.py [--results DIR] [--refs DIR]
"""

import argparse
import csv
import json
import shutil
from pathlib import Path

import yaml

REF_ID = "ATK-REF-1"
SOURCE = ("EXP-G3", "ppo-defref1")
OUTPUT = Path("results/summary/ATK-REF-1_selection.csv")


def candidates(results: Path) -> list[dict]:
    rows = []
    for final in sorted((results / SOURCE[0] / SOURCE[1]).glob("s*/final_eval.json")):
        val = json.loads(final.read_text())["val"]
        rows.append(
            {
                "run_name": SOURCE[1],
                "seed": int(final.parent.name[1:]),
                "val_evasion_rate": val["evasion_rate"],
                "val_qfe_c": val["qfe_c"],
                "val_diversity": val["diversity"],
                "best_step": json.loads(final.read_text())["best_step"],
                "checkpoint": str(final.parent / "checkpoint"),
            }
        )
    return rows


def rank_key(row: dict) -> tuple:
    return (row["val_evasion_rate"], -row["val_qfe_c"], -row["seed"])


def publish(winner: dict, refs: Path) -> Path:
    target = refs / REF_ID
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(winner["checkpoint"], target)
    meta_path = target / "meta.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["agent_id"] = REF_ID
    meta["eval_summary"] = {
        "suite": "attacker-val-v1",
        "defender": "DEF-REF-1",
        "evasion_rate": winner["val_evasion_rate"],
        "qfe_c": winner["val_qfe_c"],
        "selected_from": f"{SOURCE[0]}/{SOURCE[1]}/s{winner['seed']}",
        "selection": "scripts/select_atk_ref.py (max ER on val, then min QFE-c, then lower seed)",
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
    print(f"{REF_ID} = {SOURCE[0]}/{SOURCE[1]} s{ranked[0]['seed']} -> {target}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
