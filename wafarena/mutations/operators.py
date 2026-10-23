"""The 16 mutation operators: the attacker's action space (operadores-mutacion.md).

Each operator is deterministic given the rng, does no I/O, and returns None when it does not apply.
None of them guarantees preserving functionality; the oracle decides.
"""

import re
from collections.abc import Sequence
from urllib.parse import quote

import numpy as np

from wafarena.mutations.payload import Location, Payload

SQL_KEYWORDS = (
    "select",
    "union",
    "insert",
    "update",
    "delete",
    "drop",
    "or",
    "and",
    "from",
    "where",
    "all",
    "between",
    "like",
    "null",
    "cast",
    "chr",
)
WHITESPACE_SUBS = ("\t", "\n", "\r", "\f")
COMMENT_TAILS = ("--", "-- -", "-- x", "--+", "#")
TAUTOLOGY_REWRITES = {"1=1": "2>1", "2>1": "1=1", "'a'='a'": "'x' LIKE 'x'"}
STRING_LITERAL = re.compile(r"'([^']*)'")
INTEGER = re.compile(r"(?<![\w.])(\d+)(?![\w.])")
OPERATOR_EQUIVALENTS = {"<>": "!=", "!=": "<>", "UNION": "UNION ALL"}


def _rebuild(payload: Payload, text: str) -> Payload:
    return Payload(
        text=text, location=payload.location, url_encoding_layers=payload.url_encoding_layers
    )


class CaseSwap:
    name = "case_swap"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        def swap(match: re.Match) -> str:
            word = match.group(0)
            return "".join(c.upper() if rng.random() < 0.5 else c.lower() for c in word)

        pattern = re.compile("|".join(SQL_KEYWORDS), re.IGNORECASE)
        if not pattern.search(payload.text):
            return None
        mutated = pattern.sub(swap, payload.text)
        return _rebuild(payload, mutated) if mutated != payload.text else None


class WhitespaceSub:
    name = "whitespace_sub"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        positions = [i for i, c in enumerate(payload.text) if c == " "]
        if not positions:
            return None
        index = int(rng.choice(positions))
        sub = WHITESPACE_SUBS[int(rng.integers(len(WHITESPACE_SUBS)))]
        text = payload.text[:index] + sub + payload.text[index + 1 :]
        return _rebuild(payload, text)


class InlineComment:
    name = "inline_comment"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        positions = [i for i, c in enumerate(payload.text) if c == " "]
        if not positions:
            return None
        index = int(rng.choice(positions))
        text = payload.text[:index] + "/**/" + payload.text[index + 1 :]
        return _rebuild(payload, text)


class CommentTailVariant:
    name = "comment_tail_variant"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        for tail in COMMENT_TAILS:
            if payload.text.rstrip().endswith(tail):
                stripped = payload.text.rstrip()[: -len(tail)].rstrip()
                options = [t for t in COMMENT_TAILS if t != tail]
                new_tail = options[int(rng.integers(len(options)))]
                return _rebuild(payload, f"{stripped} {new_tail}")
        return None


class UrlEncode:
    name = "url_encode"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        if payload.url_encoding_layers >= 2 or not payload.text:
            return None
        encoded = quote(payload.text, safe="")
        if encoded == payload.text:
            return None
        return Payload(encoded, payload.location, payload.url_encoding_layers + 1)


class DoubleUrlEncode:
    name = "double_url_encode"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        if payload.url_encoding_layers >= 2 or not payload.text:
            return None
        once = quote(payload.text, safe="")
        twice = quote(once, safe="")
        if twice == payload.text:
            return None
        return Payload(twice, payload.location, payload.url_encoding_layers + 2)


class TautologyRewrite:
    name = "tautology_rewrite"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        for source, target in TAUTOLOGY_REWRITES.items():
            if source in payload.text:
                return _rebuild(payload, payload.text.replace(source, target, 1))
        return None


class NumberRewrite:
    name = "number_rewrite"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        matches = list(INTEGER.finditer(payload.text))
        if not matches:
            return None
        match = matches[int(rng.integers(len(matches)))]
        value = int(match.group(1))
        replacement = f"({value + 1}-1)"
        text = payload.text[: match.start()] + replacement + payload.text[match.end() :]
        return _rebuild(payload, text)


class StringConcatSplit:
    name = "string_concat_split"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        match = STRING_LITERAL.search(payload.text)
        if match is None or len(match.group(1)) < 2:
            return None
        literal = match.group(1)
        cut = 1 + int(rng.integers(len(literal) - 1))
        replacement = f"'{literal[:cut]}'||'{literal[cut:]}'"
        text = payload.text[: match.start()] + replacement + payload.text[match.end() :]
        return _rebuild(payload, text)


class ChrEncode:
    name = "chr_encode"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        match = STRING_LITERAL.search(payload.text)
        if match is None or not match.group(1):
            return None
        literal = match.group(1)
        encoded = "||".join(f"CHR({ord(c)})" for c in literal)
        text = payload.text[: match.start()] + encoded + payload.text[match.end() :]
        return _rebuild(payload, text)


class DollarQuote:
    name = "dollar_quote"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        match = STRING_LITERAL.search(payload.text)
        if match is None or "$$" in payload.text:
            return None
        literal = match.group(1)
        text = payload.text[: match.start()] + f"$${literal}$$" + payload.text[match.end() :]
        return _rebuild(payload, text)


HEX_STRING_MARKER = "convert_from(decode("


class HexString:
    name = "hex_string"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        # hex-of-hex is always valid hex, so the oracle accepts this forever; without this guard
        # it reapplies to its own output and the payload grows without bound (found in F2-T05).
        if HEX_STRING_MARKER in payload.text:
            return None
        match = STRING_LITERAL.search(payload.text)
        if match is None or not match.group(1):
            return None
        literal = match.group(1)
        hex_text = literal.encode().hex()
        replacement = f"{HEX_STRING_MARKER}'{hex_text}','hex'),'UTF8')"
        text = payload.text[: match.start()] + replacement + payload.text[match.end() :]
        return _rebuild(payload, text)


class CastNoise:
    name = "cast_noise"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        matches = list(INTEGER.finditer(payload.text))
        if not matches:
            return None
        match = matches[int(rng.integers(len(matches)))]
        text = (
            payload.text[: match.start()] + f"{match.group(1)}::int" + payload.text[match.end() :]
        )
        return _rebuild(payload, text)


class ParenWrap:
    name = "paren_wrap"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        match = re.search(r"\d+\s*(?:=|>|<|<>|!=)\s*\d+", payload.text)
        if match is None:
            return None
        wrapped = f"(({match.group(0)}))"
        text = payload.text[: match.start()] + wrapped + payload.text[match.end() :]
        return _rebuild(payload, text)


class OperatorEquivalent:
    name = "operator_equivalent"

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        for source, target in OPERATOR_EQUIVALENTS.items():
            pattern = re.escape(source)
            if re.search(pattern, payload.text):
                return _rebuild(payload, re.sub(pattern, target, payload.text, count=1))
        return None


class LocationSwitch:
    name = "location_switch"

    def __init__(self, allowed_locations: Sequence[Location] = ("query", "form", "json")):
        self._allowed = tuple(allowed_locations)

    def apply(self, payload: Payload, rng: np.random.Generator) -> Payload | None:
        options = [loc for loc in self._allowed if loc != payload.location]
        if not options:
            return None
        target = options[int(rng.integers(len(options)))]
        return Payload(payload.text, target, payload.url_encoding_layers)
