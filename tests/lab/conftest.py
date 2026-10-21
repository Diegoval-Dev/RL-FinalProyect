import os

import httpx
import psycopg
import pytest

VULNAPP_URL = os.environ.get("VULNAPP_URL", "http://vulnapp:8000")


def database_connection(env_name: str):
    connection = psycopg.connect(os.environ[env_name], autocommit=True)
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=VULNAPP_URL, timeout=10) as http_client:
        yield http_client


@pytest.fixture(scope="session")
def admin_db():
    yield from database_connection("ADMIN_DATABASE_URL")


@pytest.fixture(scope="session")
def app_db():
    yield from database_connection("APP_DATABASE_URL")


@pytest.fixture(scope="session")
def logger_db():
    yield from database_connection("LOGGER_DATABASE_URL")


@pytest.fixture(scope="session")
def canary_token(admin_db):
    return admin_db.execute("SELECT token FROM canary_secrets").fetchone()[0]
