"""Sends a request through a ModSecurity paranoia-level instance and reads its anomaly score.

Each PL instance proxies to vulnapp and writes its audit log to a shared volume; `modsec_score`
correlates the request by its `X-Request-ID` and returns the reconstructed score and block flag.
"""

import json
import os
import threading
import time
import uuid
from pathlib import Path

import httpx

from wafarena.defenders.audit import (
    PARANOIA_LEVELS,
    REQUEST_ID_HEADER,
    AuditEntry,
    parse_audit_line,
)

AUDIT_DIR_ENV = "MODSEC_AUDIT_DIR"
DEFAULT_AUDIT_DIR = "/var/log/modsec-audit"
AUDIT_POLL_TIMEOUT_SECONDS = 5.0
AUDIT_POLL_INTERVAL_SECONDS = 0.005


def modsec_base_url(pl: int) -> str:
    return f"http://modsec-pl{pl}:8080"


def audit_path(pl: int) -> Path:
    return Path(os.environ.get(AUDIT_DIR_ENV, DEFAULT_AUDIT_DIR)) / f"pl{pl}.json"


class AuditTail:
    """Incremental reader of an append-only audit log, indexed by request id.

    Each byte of the file is read once: `take` only looks at what was appended since the last
    call, so lookups stay O(new data) however large the log grows. Thread-safe.
    """

    def __init__(self, path: Path):
        self._path = Path(path)
        self._offset = 0
        self._bytes_read = 0
        self._entries: dict[str, AuditEntry] = {}
        self._lock = threading.Lock()

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def bytes_read(self) -> int:
        return self._bytes_read

    def take(self, request_id: str) -> AuditEntry | None:
        """Return (and forget) the entry of `request_id`, or None if it is not logged yet."""
        with self._lock:
            if request_id not in self._entries:
                self._read_new()
            return self._entries.pop(request_id, None)

    def _read_new(self) -> None:
        try:
            size = self._path.stat().st_size
        except FileNotFoundError:
            return
        if size < self._offset:  # truncated or rotated: start over
            self._offset = 0
            self._entries.clear()
        with self._path.open("rb") as handle:
            handle.seek(self._offset)
            chunk = handle.read()
        self._bytes_read += len(chunk)
        complete = chunk.rfind(b"\n") + 1
        consumed = complete
        tail = chunk[complete:]
        if tail and _is_json(tail):  # last line written without a trailing newline
            complete, consumed = len(chunk), len(chunk)
        for raw in chunk[:complete].decode(errors="replace").splitlines():
            entry = parse_audit_line(raw)
            if entry is not None:
                self._entries[entry.request_id] = entry
        self._offset += consumed
        self._bytes_read -= len(chunk) - consumed  # unread partial line is read again later


def _is_json(raw: bytes) -> bool:
    try:
        json.loads(raw)
    except ValueError:
        return False
    return True


_tails: dict[Path, AuditTail] = {}
_tails_lock = threading.Lock()


def audit_tail(path: Path) -> AuditTail:
    with _tails_lock:
        return _tails.setdefault(Path(path), AuditTail(path))


def wait_for_entry(path: Path, request_id: str) -> AuditEntry:
    tail = audit_tail(path)
    deadline = time.monotonic() + AUDIT_POLL_TIMEOUT_SECONDS
    while True:
        entry = tail.take(request_id)
        if entry is not None:
            return entry
        if time.monotonic() >= deadline:
            raise TimeoutError(f"no audit entry for {request_id} in {path}")
        time.sleep(AUDIT_POLL_INTERVAL_SECONDS)


_client: httpx.Client | None = None
_client_lock = threading.Lock()


def _http() -> httpx.Client:
    """Shared client: keeps connections to the ModSecurity instances alive between requests."""
    global _client
    with _client_lock:
        if _client is None:
            _client = httpx.Client(timeout=10)
        return _client


def send_through_modsec(method: str, path: str, pl: int, **kwargs) -> tuple[httpx.Response, str]:
    if pl not in PARANOIA_LEVELS:
        raise ValueError(f"unknown paranoia level {pl}")
    request_id = uuid.uuid4().hex
    headers = {**kwargs.pop("headers", {}), REQUEST_ID_HEADER: request_id}
    response = _http().request(method, f"{modsec_base_url(pl)}{path}", headers=headers, **kwargs)
    return response, request_id


def modsec_score(method: str, path: str, pl: int, **kwargs) -> AuditEntry:
    _response, request_id = send_through_modsec(method, path, pl, **kwargs)
    return wait_for_entry(audit_path(pl), request_id)
