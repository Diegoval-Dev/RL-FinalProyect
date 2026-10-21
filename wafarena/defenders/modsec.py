"""Sends a request through a ModSecurity paranoia-level instance and reads its anomaly score.

Each PL instance proxies to vulnapp and writes its audit log to a shared volume; `modsec_score`
correlates the request by its `X-Request-ID` and returns the reconstructed score and block flag.
"""

import os
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
AUDIT_POLL_INTERVAL_SECONDS = 0.05


def modsec_base_url(pl: int) -> str:
    return f"http://modsec-pl{pl}:8080"


def audit_path(pl: int) -> Path:
    return Path(os.environ.get(AUDIT_DIR_ENV, DEFAULT_AUDIT_DIR)) / f"pl{pl}.json"


def find_entry(path: Path, request_id: str) -> AuditEntry | None:
    if not path.exists():
        return None
    with path.open() as handle:
        for line in handle:
            entry = parse_audit_line(line)
            if entry is not None and entry.request_id == request_id:
                return entry
    return None


def wait_for_entry(path: Path, request_id: str) -> AuditEntry:
    deadline = time.monotonic() + AUDIT_POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        entry = find_entry(path, request_id)
        if entry is not None:
            return entry
        time.sleep(AUDIT_POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"no audit entry for {request_id} in {path}")


def send_through_modsec(method: str, path: str, pl: int, **kwargs) -> tuple[httpx.Response, str]:
    if pl not in PARANOIA_LEVELS:
        raise ValueError(f"unknown paranoia level {pl}")
    request_id = uuid.uuid4().hex
    headers = {**kwargs.pop("headers", {}), REQUEST_ID_HEADER: request_id}
    response = httpx.request(
        method, f"{modsec_base_url(pl)}{path}", headers=headers, timeout=10, **kwargs
    )
    return response, request_id


def modsec_score(method: str, path: str, pl: int, **kwargs) -> AuditEntry:
    _response, request_id = send_through_modsec(method, path, pl, **kwargs)
    return wait_for_entry(audit_path(pl), request_id)
