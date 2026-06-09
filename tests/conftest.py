import pytest
from fastapi.testclient import TestClient
from nsi_normalizer.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
