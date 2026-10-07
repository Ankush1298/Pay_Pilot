import os
os.environ.setdefault("PAYPILOT_TEST_MODE", "1")
os.environ.setdefault("PAYPILOT_DB", ":memory:")
os.environ.setdefault("PAYPILOT_LEDGER", "simulated")

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    from app import auth
    auth.LIMITER._hits.clear()
