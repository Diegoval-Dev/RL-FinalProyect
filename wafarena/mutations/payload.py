from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Payload:
    text: str
    location: Literal["query", "form", "json"]
    url_encoding_layers: int
