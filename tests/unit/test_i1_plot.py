"""EXP-I1 figure must render even when a seed has undefined TPR."""

from scripts.summarize_i1 import plot_tpr


def test_tpr_figure_handles_undefined_seed_values(tmp_path):
    curve = []
    for reference in ("ATK-REF-0", "ATK-REF-1"):
        for condition in ("naive", "pool"):
            for generation in range(1, 9):
                undefined = condition == "pool" and reference == "ATK-REF-1" and generation == 3
                curve.append(
                    {
                        "role": "defender",
                        "reference": reference,
                        "condition": condition,
                        "generation": generation,
                        "metric": "tpr",
                        "mean": None if undefined else 0.8,
                        "ci_low": None if undefined else 0.7,
                        "ci_high": None if undefined else 0.9,
                        "n_defined": 0 if undefined else 3,
                    }
                )
    figure = tmp_path / "EXP-I1_tpr.png"
    plot_tpr(curve, figure)
    assert figure.is_file()
    assert figure.stat().st_size > 1000
