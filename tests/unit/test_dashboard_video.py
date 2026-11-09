from dashboard.make_video import video_frames


def test_video_frames_only_use_recorded_generations():
    rows = [
        {
            "condition": "naive",
            "generation": "1",
            "role": "defender",
            "reference": "ATK-REF-1",
            "metric": "tpr",
            "mean": "0.5",
        },
        {
            "condition": "pool",
            "generation": "1",
            "role": "defender",
            "reference": "ATK-REF-1",
            "metric": "tpr",
            "mean": "0.6",
        },
        {
            "condition": "naive",
            "generation": "2",
            "role": "defender",
            "reference": "ATK-REF-1",
            "metric": "tpr",
            "mean": "0.4",
        },
        {
            "condition": "pool",
            "generation": "2",
            "role": "defender",
            "reference": "ATK-REF-1",
            "metric": "tpr",
            "mean": "0.7",
        },
    ]
    assert video_frames(rows, "ATK-REF-1") == [
        {"generation": 1, "naive": 0.5, "pool": 0.6},
        {"generation": 2, "naive": 0.4, "pool": 0.7},
    ]
