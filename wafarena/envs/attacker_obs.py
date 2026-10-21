"""Attacker observation encoder: 288-dim vector (env-atacante.md)."""

import hashlib

import numpy as np

from wafarena.attackers.base import Response

NGRAM_SIZE = 256
WINDOW = 4
N_RESPONSE_CLASSES = 6
OBS_SIZE = 288
FAMILY_ORDER = ("tautology", "union", "error", "boolean_blind", "stacked")

NGRAM_BLOCK = slice(0, 256)
WINDOW_BLOCK = slice(256, 280)
MUTATIONS_IDX = 280
QUERIES_IDX = 281
BLOCKS_IDX = 282
FAMILY_BLOCK = slice(283, 288)


def _stable_hash(gram: str) -> int:
    return int.from_bytes(hashlib.sha1(gram.encode()).digest()[:4], "big")


def ngram_hashing(text: str) -> np.ndarray:
    counts = np.zeros(NGRAM_SIZE, dtype=np.float32)
    for n in (1, 2, 3):
        for i in range(len(text) - n + 1):
            counts[_stable_hash(text[i : i + n]) % NGRAM_SIZE] += 1.0
    norm = np.linalg.norm(counts)
    return counts / norm if norm > 0 else counts


def family_index(family: str) -> int:
    return FAMILY_ORDER.index(family)


def encode_observation(
    text: str,
    responses: list[int],
    mutations: int,
    max_steps: int,
    queries_used: int,
    query_budget: int,
    blocks: int,
    ban_threshold: int,
    family: str,
) -> np.ndarray:
    obs = np.zeros(OBS_SIZE, dtype=np.float32)
    obs[NGRAM_BLOCK] = ngram_hashing(text)
    for i in range(WINDOW):
        if i < len(responses):
            obs[256 + i * N_RESPONSE_CLASSES + responses[i]] = 1.0
    obs[MUTATIONS_IDX] = min(1.0, mutations / max_steps)
    obs[QUERIES_IDX] = min(1.0, queries_used / query_budget)
    obs[BLOCKS_IDX] = min(1.0, blocks / ban_threshold)
    obs[283 + family_index(family)] = 1.0
    return np.clip(obs, 0.0, 1.0)


def initial_responses() -> list[int]:
    return [int(Response.NONE)]
