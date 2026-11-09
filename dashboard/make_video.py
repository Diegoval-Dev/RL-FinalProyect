"""Render the EXP-I1 arms-race curve as a short, source-labeled MP4."""

from pathlib import Path

from dashboard.data import i1_tpr_rows, load_results

ROOT = Path(__file__).resolve().parents[1]


def video_frames(rows: list[dict], reference: str) -> list[dict]:
    """Use only generations with both recorded naive and pool TPR values."""
    by_generation: dict[int, dict] = {}
    for item in i1_tpr_rows(rows, reference):
        by_generation.setdefault(item["generation"], {"generation": item["generation"]})[
            item["condition"]
        ] = item["tpr"]
    frames = [by_generation[g] for g in sorted(by_generation)]
    if any(set(frame) != {"generation", "naive", "pool"} for frame in frames):
        raise ValueError(f"EXP-I1 has an incomplete TPR generation for {reference}")
    return frames


def main() -> None:
    from matplotlib import pyplot as plt
    from matplotlib.animation import FFMpegWriter

    rows = load_results(ROOT / "results/summary")["EXP-I1_curve.csv"]
    references = ("ATK-REF-0", "ATK-REF-1")
    frames = {ref: video_frames(rows, ref) for ref in references}
    if any(
        [frame["generation"] for frame in frames[ref]] != list(range(1, 9)) for ref in references
    ):
        raise ValueError("EXP-I1 video requires eight recorded generations per reference")
    output = ROOT / "report/video/EXP-I1_arms_race.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)
    fig.patch.set_facecolor("#101b2b")
    writer = FFMpegWriter(fps=2, codec="libx264", bitrate=900, extra_args=["-pix_fmt", "yuv420p"])
    with writer.saving(fig, str(output), dpi=120):
        for generation in range(1, 9):
            for ax, ref in zip(axes, references, strict=True):
                ax.clear()
                ax.set_facecolor("#17263b")
                shown = frames[ref][:generation]
                for condition, color, label in (
                    ("naive", "#ffb86c", "Ingenuo"),
                    ("pool", "#55d6be", "Pool"),
                ):
                    ax.plot(
                        [f["generation"] for f in shown],
                        [f[condition] for f in shown],
                        "-o",
                        color=color,
                        linewidth=2.5,
                        label=label,
                    )
                ax.set(xlim=(1, 8), ylim=(0, 1.05), title=ref, xlabel="Generación")
                ax.grid(alpha=0.2)
                ax.tick_params(colors="white")
                ax.title.set_color("white")
                ax.xaxis.label.set_color("white")
                ax.yaxis.label.set_color("white")
                ax.legend(facecolor="#17263b", labelcolor="white")
            axes[0].set_ylabel("TPR sobre solicitudes de ataque", color="white")
            fig.suptitle(f"Self-play · generación {generation}/8", color="white", fontsize=16)
            fig.text(
                0.5,
                0.01,
                "Fuente: EXP-I1_curve.csv · eea6f78 · media de 3 semillas",
                ha="center",
                color="#a7bdce",
                fontsize=9,
            )
            fig.tight_layout(rect=(0, 0.04, 1, 0.93))
            writer.grab_frame()
            writer.grab_frame()
    plt.close(fig)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
