"""F1-T06: the proxy and honeypot services are up and the honeypot never touches the real DB."""

import os

import httpx
import pytest

pytestmark = pytest.mark.lab

PROXY_URL = os.environ.get("PROXY_URL", "http://proxy:8000")
HONEYPOT_URL = os.environ.get("HONEYPOT_URL", "http://honeypot:8000")


def test_proxy_service_is_healthy():
    assert httpx.get(f"{PROXY_URL}/health", timeout=10).status_code == 200


def test_honeypot_returns_fake_rows_without_database():
    response = httpx.get(f"{HONEYPOT_URL}/search?q=anything", timeout=10)
    assert response.status_code == 200
    assert response.json()["rows"]
