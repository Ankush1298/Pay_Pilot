import os
os.environ.setdefault("PAYPILOT_TEST_MODE", "1")
os.environ.setdefault("PAYPILOT_LEDGER", "simulated")

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture()
def client():
    return TestClient(app)
