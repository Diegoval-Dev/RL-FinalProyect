"""Persistent cache of ModSecurity results keyed by (config version, PL, request hash).

The cache is invalidated by bumping CRS_CONFIG_VERSION when the CRS version or ModSecurity config
changes (ADR-0005).
"""

import hashlib
import json
from pathlib import Path

CRS_CONFIG_VERSION = "owasp-crs-4.30.0-pl-anomaly"
DEFAULT_CACHE_PATH = Path("results/cache/modsec_cache.json")


def request_hash(method: str, path_with_query: str) -> str:
    raw = f"{CRS_CONFIG_VERSION}|{method}|{path_with_query}"
    return hashlib.sha1(raw.encode()).hexdigest()


class ModSecCache:
    def __init__(self, path: Path | str = DEFAULT_CACHE_PATH):
        self._path = Path(path)
        self._data: dict[str, list[int]] = {}
        self._dirty = False
        self.hits = 0
        self.misses = 0
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            self._data = json.loads(self._path.read_text())

    def key(self, pl: int, method: str, path_with_query: str) -> str:
        return f"{pl}:{request_hash(method, path_with_query)}"

    def get(self, pl: int, method: str, path_with_query: str) -> tuple[int, bool] | None:
        value = self._data.get(self.key(pl, method, path_with_query))
        if value is None:
            self.misses += 1
        else:
            self.hits += 1
        return (value[0], bool(value[1])) if value is not None else None

    def put(self, pl: int, method: str, path_with_query: str, score: int, block: bool) -> None:
        self._data[self.key(pl, method, path_with_query)] = [score, int(block)]
        self._dirty = True

    def flush(self) -> None:
        if not self._dirty:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data))
        self._dirty = False
