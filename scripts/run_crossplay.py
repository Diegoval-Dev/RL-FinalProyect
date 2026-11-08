"""Run and summarize EXP-I2 cross-play from three EXP-I1 pool checkpoint runs."""

import argparse
import math
from datetime import UTC, datetime
from pathlib import Path

import matplotlib
import numpy as np
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from wafarena.envs.resolve import resolve_backend  # noqa: E402
from wafarena.eval.crossplay import (  # noqa: E402
    aggregate_cells,
    discover_runs,
    evaluate_cell,
    load_config,
    pair_cells,
)
from wafarena.runmeta import (  # noqa: E402
    DirtyTreeError,
    build_meta,
    git_info,
    run_dir,
    run_id,
    uncommitted_changes,
    write_meta,
)
from wafarena.selfplay.report import write_csv  # noqa: E402

CONFIG = Path("configs/selfplay/exp_i2_crossplay_pool.yaml")


def plot_heatmap(matrix: list[dict], path: Path) -> None:
    """Render the three-seed mean episode ER for every generation pair."""
    if len(matrix) != 64:
        raise ValueError(f"EXP-I2 heatmap needs 64 cells, got {len(matrix)}")
    values = [[math.nan for _ in range(8)] for _ in range(8)]
    seen = set()
    for row in matrix:
        defender, attacker = row["defender_generation"], row["attacker_generation"]
        if not 1 <= defender <= 8 or not 1 <= attacker <= 8:
            raise ValueError("EXP-I2 heatmap generation outside 1–8")
        if (defender, attacker) in seen:
            raise ValueError("duplicate EXP-I2 heatmap cell")
        seen.add((defender, attacker))
        values[defender - 1][attacker - 1] = (
            math.nan if row["mean_er"] is None else 100 * row["mean_er"]
        )
    if len(seen) != 64:
        raise ValueError("EXP-I2 heatmap has missing cells")
    defined = [value for line in values for value in line if not math.isnan(value)]
    max_rate = max(defined, default=0)
    fig, ax = plt.subplots(figsize=(9, 7.5))
    cmap = plt.get_cmap("YlOrRd").with_extremes(bad="#dddddd")
    image = ax.imshow(np.ma.masked_invalid(values), cmap=cmap, vmin=0, vmax=max(5, max_rate))
    for defender in range(8):
        for attacker in range(8):
            value = values[defender][attacker]
            label = "NA" if math.isnan(value) else f"{value:.1f}"
            ax.text(attacker, defender, label, ha="center", va="center", fontsize=8)
    ax.set_xticks(range(8), range(1, 9))
    ax.set_yticks(range(8), range(1, 9))
    ax.set_xlabel("Attacker generation")
    ax.set_ylabel("Defender generation")
    ax.set_title("EXP-I2: self-play pool cross-play (mean ER, %)")
    fig.colorbar(image, ax=ax, label="Attacker evasion rate (%)")
    fig.text(
        0.5,
        0.02,
        "Three pool seeds; 200 attacker-eval-v1 test episodes per pair and seed.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _prepare_run(root: Path, config: dict, source, repo: Path, eval_sha: str) -> Path:
    directory = run_dir(root, config["exp_id"], config["run_name"], source.seed)
    expected_id = run_id(config["exp_id"], config["run_name"], source.seed, eval_sha)
    resolved = {
        **config,
        "source_run_id": source.source_run_id,
        "source_git_sha": source.source_git_sha,
    }
    meta_path = directory / "meta.yaml"
    config_path = directory / "config.resolved.yaml"
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text())
        if (
            any(
                meta.get(key) != value
                for key, value in (
                    ("run_id", expected_id),
                    ("git_sha", eval_sha),
                    ("seed", source.seed),
                    ("source_run_id", source.source_run_id),
                    ("source_git_sha", source.source_git_sha),
                    ("dirty", False),
                )
            )
            or yaml.safe_load(config_path.read_text()) != resolved
        ):
            raise ValueError(f"stale EXP-I2 run metadata: {directory}")
    else:
        meta = build_meta(config, seed=source.seed, repo=repo, allow_dirty=False)
        meta.update(
            {
                "source_run_id": source.source_run_id,
                "source_git_sha": source.source_git_sha,
                "suite": config["suite"],
                "split": "test",
            }
        )
        write_meta(directory, meta)
        config_path.write_text(yaml.safe_dump(resolved, sort_keys=False))
    return directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="one EXP-I1 pool checkpoint run")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--summary-dir", type=Path, default=Path("results/summary"))
    parser.add_argument("--figure", type=Path, default=Path("report/figuras/EXP-I2_crossplay.png"))
    args = parser.parse_args()
    repo = Path.cwd()
    changes = uncommitted_changes(repo, ("wafarena", "configs", "scripts", "Makefile"))
    if changes:
        raise DirtyTreeError(f"refusing EXP-I2 with uncommitted evaluation code: {changes}")
    config = load_config(args.config)
    eval_sha = git_info(repo).sha
    root = args.results or Path("results") / f"_i2_final_{eval_sha}"
    sources = discover_runs(args.run, config)
    directories = {
        source.seed: _prepare_run(root, config, source, repo, eval_sha) for source in sources
    }
    backend = resolve_backend(config["backend"])
    cells = []
    try:
        for pair in pair_cells(sources):
            directory = directories[pair.seed]
            cell = (
                directory
                / f"def-{pair.defender_generation:02d}_atk-{pair.attacker_generation:02d}.json"
            )
            cells.append(
                evaluate_cell(
                    pair,
                    config,
                    cell,
                    run_id(config["exp_id"], config["run_name"], pair.seed, eval_sha),
                    eval_sha,
                    backend,
                )
            )
            if pair.defender_generation == 8 and pair.attacker_generation == 8:
                meta_path = directory / "meta.yaml"
                meta = yaml.safe_load(meta_path.read_text())
                meta["completed_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                meta_path.write_text(yaml.safe_dump(meta, sort_keys=False))
                print(f"Completed EXP-I2 pool seed {pair.seed}: 64/64 cells", flush=True)
    finally:
        backend.close()
    matrix = aggregate_cells(cells, config)
    write_csv(args.summary_dir / "EXP-I2_cells.csv", cells)
    write_csv(args.summary_dir / "EXP-I2_matrix.csv", matrix)
    plot_heatmap(matrix, args.figure)
    print(f"EXP-I2 {eval_sha}: {len(cells)} cells, {len(matrix)} matrix positions")
    print(f"Wrote {args.summary_dir / 'EXP-I2_matrix.csv'} and {args.figure}")


if __name__ == "__main__":
    main()
