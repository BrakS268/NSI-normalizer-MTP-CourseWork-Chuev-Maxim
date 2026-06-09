from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from nsi_normalizer.api.main import app
from nsi_normalizer.store import record_store, job_store

API_KEY = "changeme"
HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture(autouse=True)
def clear_stores() -> None:
    record_store.clear()
    job_store.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestHealth:
    def test_liveness(self, client: TestClient) -> None:
        r = client.get("/api/v1/health/live")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_readiness(self, client: TestClient) -> None:
        r = client.get("/api/v1/health/ready")
        assert r.status_code == 200


class TestIngest:
    def test_ingest_accepted(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/records/ingest",
            json={
                "source": "test",
                "record_type": "okved",
                "records": [
                    {"code": "62.01", "name": "Разработка ПО"},
                    {"code": "47.91", "name": "Торговля через интернет"},
                ],
            },
            headers=HEADERS,
        )
        assert r.status_code == 202
        body = r.json()
        assert body["accepted"] == 2
        assert "job_id" in body

    def test_ingest_requires_api_key(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/records/ingest",
            json={"source": "s", "record_type": "okved", "records": [{"name": "x"}]},
        )
        assert r.status_code == 422

    def test_ingest_empty_records_rejected(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/records/ingest",
            json={"source": "test", "record_type": "okved", "records": []},
            headers=HEADERS,
        )
        assert r.status_code == 422

    def test_ingest_invalid_record_type(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/records/ingest",
            json={"source": "s", "record_type": "unknown_type", "records": [{"name": "x"}]},
            headers=HEADERS,
        )
        assert r.status_code == 422


class TestNormalize:
    def test_normalize_okved(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/records/normalize",
            json={
                "source": "test",
                "record_type": "okved",
                "payload": {"code": "62.1", "name": "  Разработка ПО  "},
            },
            headers=HEADERS,
        )
        assert r.status_code == 200
        result = r.json()["result"]
        assert result["canonical_code"] == "62.01"
        assert result["canonical_name"] == "Разработка ПО"

    def test_normalize_fstec(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/records/normalize",
            json={
                "source": "test",
                "record_type": "fstec",
                "payload": {
                    "bdu_id": "BDU:2024-01234",
                    "name": "Уязвимость",
                    "severity_raw": "Высокий",
                    "cvss_score_raw": "7.5",
                },
            },
            headers=HEADERS,
        )
        assert r.status_code == 200
        payload = r.json()["result"]["normalized_payload"]
        assert payload["severity"] == "high"
        assert payload["cvss_score"] == 7.5

    def test_normalize_requires_api_key(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/records/normalize",
            json={"source": "s", "record_type": "okved", "payload": {}},
        )
        assert r.status_code == 422


class TestDeduplicate:
    def _ingest(self, client: TestClient, records: list[dict]) -> None:
        client.post(
            "/api/v1/records/ingest",
            json={"source": "test", "record_type": "okved", "records": records},
            headers=HEADERS,
        )

    def test_deduplicate_no_records_returns_404(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/records/deduplicate",
            json={"record_type": "okved"},
            headers=HEADERS,
        )
        assert r.status_code == 404

    def test_deduplicate_accepted_after_ingest(self, client: TestClient) -> None:
        from unittest.mock import patch, MagicMock

        self._ingest(client, [{"code": "62.01", "name": "Разработка ПО"}])
        with patch("nsi_normalizer.workers.tasks.run_deduplication") as mock_task:
            mock_task.delay = MagicMock()
            r = client.post(
                "/api/v1/records/deduplicate",
                json={"record_type": "okved"},
                headers=HEADERS,
            )
        assert r.status_code == 202
        assert "job_id" in r.json()


class TestJobStatus:
    def test_unknown_job_returns_404(self, client: TestClient) -> None:
        r = client.get(f"/api/v1/jobs/{uuid.uuid4()}/status", headers=HEADERS)
        assert r.status_code == 404

    def test_job_status_after_ingest(self, client: TestClient) -> None:
        ingest_r = client.post(
            "/api/v1/records/ingest",
            json={"source": "s", "record_type": "okved", "records": [{"name": "x"}]},
            headers=HEADERS,
        )
        job_id = ingest_r.json()["job_id"]
        r = client.get(f"/api/v1/jobs/{job_id}/status", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "pending"
        assert body["total_records"] == 1

    def test_result_on_non_completed_job_returns_409(self, client: TestClient) -> None:
        ingest_r = client.post(
            "/api/v1/records/ingest",
            json={"source": "s", "record_type": "okved", "records": [{"name": "x"}]},
            headers=HEADERS,
        )
        job_id = ingest_r.json()["job_id"]
        r = client.get(f"/api/v1/jobs/{job_id}/result", headers=HEADERS)
        assert r.status_code == 409
