"""Generates results/summary/modsec_defender_suites.csv: ModSecurity PL1-PL4 on every defender
suite, the fixed reference of EXP-F5 (Pareto), EXP-F6/F7 (generalization) and the DEF-REF-1
selection rule (FPR of modsec-pl2 on defender-val-v1).

ModSecurity does not learn and the suites are fixed (metricas.md), so one evaluation per paranoia
level is the whole result: there are no seeds to aggregate. Runs inside the lab runner
(`make modsec-defender-suites`).
"""

import csv
from pathlib import Path

from wafarena.defenders.modsec_defender import ModSecDefender
from wafarena.envs.resolve import resolve_backend
from wafarena.eval import harness

OUTPUT = Path("results/summary/modsec_defender_suites.csv")
SUITES = ("defender-val-v1", "defender-eval-v1", "defender-eval-hard-v1", "defender-eval-family-v1")
PARANOIA_LEVELS = (1, 2, 3, 4)


def main() -> None:
    backend = resolve_backend("fast")
    rows = []
    try:
        for suite in SUITES:
            for pl in PARANOIA_LEVELS:
                summary = harness.evaluate_defender(ModSecDefender(pl), suite, backend=backend)
                rows.append({"defender": f"modsec-pl{pl}", "suite": suite, **summary})
                print(f"{suite} modsec-pl{pl}: tpr={summary['tpr']:.4f} fpr={summary['fpr']:.4f}")
    finally:
        backend.close()
    columns = list(dict.fromkeys(key for row in rows for key in row))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, restval="")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
