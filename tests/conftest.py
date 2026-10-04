import os
os.environ.setdefault("INTENTLOCK_TEST_MODE", "1")
os.environ.setdefault("INTENTLOCK_LEDGER", "simulated")

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture()
def client():
    return TestClient(app)
