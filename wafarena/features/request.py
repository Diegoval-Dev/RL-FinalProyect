"""Request features (indices 0-11 of the defender observation), see features.md.

The request text is the values of every parameter (query, form, flattened JSON) joined by '&' and
URL-decoded once. All features are normalized to [0, 1].
"""

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import unquote

REQUEST_FEATURE_NAMES: tuple[str, ...] = (
    "len_log",
    "entropy",
    "special_ratio",
    "sql_kw",
    "quote_count",
    "comment_markers",
    "encoding_depth",
    "digit_ratio",
    "upper_ratio",
    "param_count",
    "is_json",
    "max_token_len",
)

SPECIAL_CHARS = set("'\";()=<>|-/*#%")
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
    "having",
    "sleep",
    "benchmark",
    "cast",
    "concat",
    "null",
)
COMMENT_MARKERS = ("--", "/*", "*/")
LEN_NORM = math.log1p(2048)
SESSION_LEN_NORM = math.log1p(200)
SQL_KW_DIVISOR = 10
QUOTE_DIVISOR = 10
COMMENT_DIVISOR = 5
PARAM_DIVISOR = 20
MAX_TOKEN_DIVISOR = 256
MAX_ENCODING_LAYERS = 3
ENTROPY_BITS = 8


@dataclass(frozen=True)
class RequestInput:
    params: Mapping[str, str] = field(default_factory=dict)
    body_is_json: bool = False


def request_text(params: Mapping[str, str]) -> str:
    return unquote("&".join(str(value) for value in params.values()))


def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = {char: text.count(char) for char in set(text)}
    total = len(text)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def encoding_layers(raw: str) -> int:
    layers = 0
    current = raw
    while layers < MAX_ENCODING_LAYERS:
        decoded = unquote(current)
        if decoded == current:
            break
        layers += 1
        current = decoded
    return layers


def ratio(count: int, total: int) -> float:
    return count / total if total else 0.0


def request_features(request: RequestInput) -> tuple[float, ...]:
    raw_text = "&".join(str(value) for value in request.params.values())
    text = unquote(raw_text)
    lowered = text.lower()
    letters = [c for c in text if c.isalpha()]
    tokens = text.split()
    longest = max((len(token) for token in tokens), default=0)
    return (
        min(1.0, math.log1p(len(text)) / LEN_NORM),
        shannon_entropy(text) / ENTROPY_BITS,
        ratio(sum(c in SPECIAL_CHARS for c in text), len(text)),
        min(1.0, _sql_keyword_count(lowered) / SQL_KW_DIVISOR),
        min(1.0, (text.count("'") + text.count('"')) / QUOTE_DIVISOR),
        min(1.0, sum(text.count(marker) for marker in COMMENT_MARKERS) / COMMENT_DIVISOR),
        encoding_layers(raw_text) / MAX_ENCODING_LAYERS,
        ratio(sum(c.isdigit() for c in text), len(text)),
        ratio(sum(c.isupper() for c in letters), len(letters)),
        min(1.0, len(request.params) / PARAM_DIVISOR),
        1.0 if request.body_is_json else 0.0,
        min(1.0, longest / MAX_TOKEN_DIVISOR),
    )


def _sql_keyword_count(lowered: str) -> int:
    words = re.findall(r"[a-z_]+", lowered)
    keywords = set(SQL_KEYWORDS)
    return sum(word in keywords for word in words)
