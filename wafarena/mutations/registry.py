"""Frozen registry mapping each action index to its mutation operator.

The order is the attacker's action space and must not change without a MAJOR contract bump.
"""

from wafarena.mutations.operators import (
    CaseSwap,
    CastNoise,
    ChrEncode,
    CommentTailVariant,
    DollarQuote,
    DoubleUrlEncode,
    HexString,
    InlineComment,
    LocationSwitch,
    NumberRewrite,
    OperatorEquivalent,
    ParenWrap,
    StringConcatSplit,
    TautologyRewrite,
    UrlEncode,
    WhitespaceSub,
)

REGISTRY = (
    CaseSwap(),
    WhitespaceSub(),
    InlineComment(),
    CommentTailVariant(),
    UrlEncode(),
    DoubleUrlEncode(),
    TautologyRewrite(),
    NumberRewrite(),
    StringConcatSplit(),
    ChrEncode(),
    DollarQuote(),
    HexString(),
    CastNoise(),
    ParenWrap(),
    OperatorEquivalent(),
    LocationSwitch(),
)


def operator_at(index: int):
    return REGISTRY[index]


def operator_names() -> tuple[str, ...]:
    return tuple(operator.name for operator in REGISTRY)
