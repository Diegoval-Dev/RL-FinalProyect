import os

import httpx
import pytest

VULNAPP_URL = os.environ.get("VULNAPP_URL", "http://vulnapp:8000")


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=VULNAPP_URL, timeout=10) as http_client:
        yield http_client
