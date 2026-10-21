"""Assembly of the ModSecurity score block of the observation (indices 12-15), see features.md."""

PARANOIA_LEVELS = (1, 2, 3, 4)
MODSEC_BLOCK_START = 12
MODSEC_SCORE_DIVISOR = 50


def modsec_feature_index(paranoia_level: int) -> int:
    if paranoia_level not in PARANOIA_LEVELS:
        raise ValueError(f"unknown paranoia level {paranoia_level}")
    return MODSEC_BLOCK_START + paranoia_level - 1


def modsec_features(scores: dict[int, int]) -> tuple[float, ...]:
    return tuple(min(1.0, scores[pl] / MODSEC_SCORE_DIVISOR) for pl in PARANOIA_LEVELS)
