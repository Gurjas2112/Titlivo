"""Tests run against the local database loaded by `make data` (synthetic, seed 42)."""

import pytest
from fastapi.testclient import TestClient

from titlivo.main import app
from titlivo.settings import get_settings


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def demo(client):
    return client.get("/v1/demo/parcels").json()


@pytest.fixture(scope="session")
def dev_headers():
    return {"Authorization": f"Bearer {get_settings().demo_api_key}"}


@pytest.fixture(scope="session")
def admin_headers():
    return {"Authorization": f"Bearer {get_settings().admin_api_key}"}
