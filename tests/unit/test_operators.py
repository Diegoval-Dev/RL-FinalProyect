"""F1-T08: the 16 mutation operators follow operadores-mutacion.md."""

import json
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from wafarena.mutations.payload import Payload
from wafarena.mutations.registry import REGISTRY, operator_at, operator_names

CORPUS_PATH = Path(__file__).parents[2] / "data" / "payloads" / "corpus.jsonl"
FROZEN_ORDER = (
    "case_swap",
    "whitespace_sub",
    "inline_comment",
    "comment_tail_variant",
    "url_encode",
    "double_url_encode",
    "tautology_rewrite",
    "number_rewrite",
    "string_concat_split",
    "chr_encode",
    "dollar_quote",
    "hex_string",
    "cast_noise",
    "paren_wrap",
    "operator_equivalent",
    "location_switch",
)


def corpus_payloads() -> list[Payload]:
    lines = CORPUS_PATH.read_text().splitlines()
    return [Payload(json.loads(line)["text"], json.loads(line)["location"], 0) for line in lines]


def test_registry_has_sixteen_operators_in_frozen_order():
    assert operator_names() == FROZEN_ORDER


def test_operator_at_returns_operator_by_index():
    assert operator_at(0).name == "case_swap"
    assert operator_at(15).name == "location_switch"


@pytest.mark.parametrize("index", range(len(FROZEN_ORDER)))
def test_same_seed_gives_same_result(index):
    payload = Payload("' UNION SELECT token FROM canary_secrets --", "query", 0)
    a = operator_at(index).apply(payload, np.random.default_rng(7))
    b = operator_at(index).apply(payload, np.random.default_rng(7))

    assert a == b


@pytest.mark.parametrize("operator", REGISTRY, ids=operator_names())
def test_apply_never_raises_on_any_corpus_payload(operator):
    rng = np.random.default_rng(0)
    for payload in corpus_payloads():
        operator.apply(payload, rng)  # must not raise


@pytest.mark.parametrize("operator", REGISTRY, ids=operator_names())
def test_result_differs_from_input_when_not_none(operator):
    rng = np.random.default_rng(1)
    changed = False
    for payload in corpus_payloads():
        result = operator.apply(payload, rng)
        if result is not None:
            assert result != payload
            changed = True
    assert changed, f"{operator.name} never applied to any corpus payload"


def test_location_switch_only_produces_allowed_locations():
    from wafarena.mutations.operators import LocationSwitch

    operator = LocationSwitch(allowed_locations=("query", "json"))
    rng = np.random.default_rng(3)
    payload = Payload("1 OR 1=1", "query", 0)
    for _ in range(20):
        result = operator.apply(payload, rng)
        if result is not None:
            assert result.location in ("query", "json")


@settings(max_examples=50, deadline=None)
@given(text=st.text(min_size=0, max_size=80), seed=st.integers(0, 10_000))
def test_operators_never_raise_on_arbitrary_text(text, seed):
    payload = Payload(text, "query", 0)
    for operator in REGISTRY:
        operator.apply(payload, np.random.default_rng(seed))
