from dataclasses import dataclass
from typing import Literal

Location = Literal["query", "form", "json"]


@dataclass(frozen=True)
class Payload:
    text: str
    location: Location
    url_encoding_layers: int
