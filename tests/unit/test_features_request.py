"""F1-T10: request features (indices 0-11) follow features.md exactly."""

import math

import pytest

from wafarena.features.request import REQUEST_FEATURE_NAMES, RequestInput, request_features


def feature(text_params: dict, **kwargs) -> dict:
    values = request_features(RequestInput(params=text_params, **kwargs))
    return dict(zip(REQUEST_FEATURE_NAMES, values, strict=True))


def test_there_are_twelve_request_features_all_in_unit_range():
    values = request_features(RequestInput(params={"q": "O'Brien' OR 1=1 --"}))

    assert len(values) == 12
    assert all(0.0 <= v <= 1.0 for v in values)


def test_len_log_matches_contract_formula():
    text = "abcde"  # one param, value len 5
    expected = min(1.0, math.log1p(len(text)) / math.log1p(2048))

    assert feature({"q": text})["len_log"] == pytest.approx(expected)


def test_special_ratio_counts_only_special_characters():
    # text "';" -> 2 special chars out of 2
    assert feature({"q": "';"})["special_ratio"] == pytest.approx(1.0)


def test_quote_count_is_normalized_by_ten():
    assert feature({"q": "'''''"})["quote_count"] == pytest.approx(0.5)


def test_comment_markers_counts_sql_comment_tokens():
    # "-- /* */" -> 3 markers / 5
    assert feature({"q": "-- /* */"})["comment_markers"] == pytest.approx(3 / 5)


def test_sql_kw_counts_keywords_case_insensitively():
    # union, select, or -> 3 keywords / 10
    assert feature({"q": "UNION select OR"})["sql_kw"] == pytest.approx(3 / 10)


def test_digit_ratio_is_fraction_of_digits():
    assert feature({"q": "ab12"})["digit_ratio"] == pytest.approx(0.5)


def test_upper_ratio_is_fraction_of_uppercase_over_letters():
    # "AbC1" letters AbC -> 2 upper of 3
    assert feature({"q": "AbC1"})["upper_ratio"] == pytest.approx(2 / 3)


def test_param_count_is_normalized_by_twenty():
    params = {f"p{i}": "x" for i in range(10)}

    assert feature(params)["param_count"] == pytest.approx(10 / 20)


def test_is_json_flag_reflects_body_type():
    assert feature({"q": "x"}, body_is_json=True)["is_json"] == 1.0
    assert feature({"q": "x"}, body_is_json=False)["is_json"] == 0.0


def test_max_token_len_is_longest_token_over_256():
    assert feature({"q": "a" * 128})["max_token_len"] == pytest.approx(128 / 256)


def test_encoding_depth_detects_url_encoding_layers():
    # single-encoded space %20 -> one layer / 3
    assert feature({"q": "a%20b"})["encoding_depth"] == pytest.approx(1 / 3)


def test_empty_request_gives_zero_features():
    values = feature({})

    assert values["len_log"] == 0.0
    assert values["entropy"] == 0.0
    assert values["special_ratio"] == 0.0
