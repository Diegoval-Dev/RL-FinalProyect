"""The EXP-I2 matrix figure must render all 64 generation pairs."""

import warnings

from scripts.run_crossplay import plot_heatmap


def test_crossplay_heatmap_renders_complete_matrix(tmp_path):
    matrix = [
        {
            "defender_generation": defender,
            "attacker_generation": attacker,
            "mean_er": 0.1 if (defender, attacker) == (8, 8) else 0.0,
            "n_seeds": 3,
        }
        for defender in range(1, 9)
        for attacker in range(1, 9)
    ]
    figure = tmp_path / "EXP-I2_crossplay.png"
    with warnings.catch_warnings():
        warnings.simplefilter("error", PendingDeprecationWarning)
        plot_heatmap(matrix, figure)
    assert figure.is_file()
    assert figure.stat().st_size > 1000


def test_crossplay_heatmap_marks_undefined_rate(tmp_path):
    matrix = [
        {
            "defender_generation": defender,
            "attacker_generation": attacker,
            "mean_er": None if (defender, attacker) == (2, 3) else 0.0,
            "n_seeds": 0 if (defender, attacker) == (2, 3) else 3,
        }
        for defender in range(1, 9)
        for attacker in range(1, 9)
    ]
    figure = tmp_path / "undefined.png"
    plot_heatmap(matrix, figure)
    assert figure.is_file()
