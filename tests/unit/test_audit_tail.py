"""F2-T05: the audit log is read incrementally, not rescanned for every request."""

import json
import threading
from pathlib import Path

import pytest

from wafarena.defenders.modsec import AuditTail, wait_for_entry


def line(request_id: str, interrupted: bool = False) -> str:
    return json.dumps(
        {
            "transaction": {
                "is_interrupted": interrupted,
                "request": {"headers": {"X-Request-ID": request_id}},
                "response": {"http_code": 403 if interrupted else 200},
                "messages": [{"details": {"ruleId": "942100", "severity": "2"}}],
            }
        }
    )


def append(path: Path, *lines: str, newline: bool = True) -> None:
    with path.open("a") as handle:
        handle.write("\n".join(lines) + ("\n" if newline else ""))


def test_take_returns_entry_appended_after_creation(tmp_path):
    path = tmp_path / "pl1.json"
    tail = AuditTail(path)
    assert tail.take("a") is None  # file does not exist yet
    append(path, line("a", interrupted=True))
    entry = tail.take("a")
    assert entry.request_id == "a" and entry.would_block and entry.score == 5


def test_take_consumes_the_entry(tmp_path):
    path = tmp_path / "pl1.json"
    append(path, line("a"))
    tail = AuditTail(path)
    assert tail.take("a") is not None
    assert tail.take("a") is None


def test_only_new_bytes_are_read_on_each_lookup(tmp_path):
    path = tmp_path / "pl1.json"
    append(path, *[line(f"old-{i}") for i in range(200)])
    tail = AuditTail(path)
    assert tail.take("old-0") is not None
    offset_after_first_read = tail.offset
    append(path, line("new"))
    assert tail.take("new") is not None
    assert tail.offset > offset_after_first_read
    assert tail.bytes_read == path.stat().st_size  # every byte read exactly once


def test_entries_of_other_requests_stay_available(tmp_path):
    path = tmp_path / "pl1.json"
    append(path, line("a"), line("b"))
    tail = AuditTail(path)
    assert tail.take("b") is not None
    assert tail.take("a") is not None


def test_partial_last_line_is_not_lost_nor_misparsed(tmp_path):
    path = tmp_path / "pl1.json"
    tail = AuditTail(path)
    whole = line("a")
    with path.open("a") as handle:
        handle.write(whole[:30])
    assert tail.take("a") is None
    with path.open("a") as handle:
        handle.write(whole[30:] + "\n")
    assert tail.take("a") is not None


def test_complete_last_line_without_trailing_newline_is_read(tmp_path):
    path = tmp_path / "pl1.json"
    append(path, line("a"), newline=False)
    assert AuditTail(path).take("a") is not None


def test_truncated_log_is_reread_from_the_start(tmp_path):
    path = tmp_path / "pl1.json"
    append(path, *[line(f"x{i}") for i in range(50)])
    tail = AuditTail(path)
    assert tail.take("x49") is not None
    path.write_text(line("fresh") + "\n")  # log rotated by a lab restart
    assert tail.take("fresh") is not None


def test_non_json_lines_are_ignored(tmp_path):
    path = tmp_path / "pl1.json"
    append(path, "garbage", line("a"))
    assert AuditTail(path).take("a") is not None


def test_wait_for_entry_returns_entry_that_shows_up_later(tmp_path):
    path = tmp_path / "pl1.json"
    threading.Timer(0.05, append, args=(path, line("late"))).start()
    assert wait_for_entry(path, "late").request_id == "late"


def test_wait_for_entry_times_out(tmp_path, monkeypatch):
    monkeypatch.setattr("wafarena.defenders.modsec.AUDIT_POLL_TIMEOUT_SECONDS", 0.05)
    with pytest.raises(TimeoutError, match="missing"):
        wait_for_entry(tmp_path / "pl1.json", "missing")
