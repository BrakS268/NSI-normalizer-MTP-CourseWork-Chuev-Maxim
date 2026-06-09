# API Reference

Base URL: `http://localhost:8000`  
Auth: `X-API-Key: <your-key>` header required on all endpoints except `/health`.

Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## Health

### `GET /api/v1/health/live`
Liveness probe. Returns 200 if the process is running.

### `GET /api/v1/health/ready`
Readiness probe. Returns 200 if the service is ready to handle requests.

---

## Records

### `POST /api/v1/records/ingest`
Upload a batch of raw records for processing.

**Request body:**
```json
{
  "source": "okved2_fns",
  "record_type": "okved",
  "records": [
    {"code": "62.01", "name": "Разработка программного обеспечения"},
    {"code": "62.01", "name": "разраб. прогр. обеспеч."}
  ]
}
```

`record_type`: `"okved"` | `"fstec"` | `"generic"`

**Response `202 Accepted`:**
```json
{
  "accepted": 2,
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### `POST /api/v1/records/normalize`
Normalize a single record synchronously (< 100ms).

**Request body:**
```json
{
  "source": "manual",
  "record_type": "fstec",
  "payload": {
    "bdu_id": "BDU:2024-01234",
    "name": "Уязвимость ядра Linux",
    "severity_raw": "Высокий",
    "cve_ids_raw": "CVE-2024-12345",
    "cvss_score_raw": "7.5"
  }
}
```

**Response `200 OK`:**
```json
{
  "result": {
    "canonical_id": "...",
    "record_type": "fstec",
    "canonical_name": "Уязвимость ядра Linux",
    "canonical_code": "BDU:2024-01234",
    "normalized_payload": {
      "severity": "high",
      "cve_ids": ["CVE-2024-12345"],
      "cvss_score": 7.5
    },
    "confidence": 0.83,
    "source": "manual"
  }
}
```

---

### `POST /api/v1/records/deduplicate`
Start an asynchronous deduplication job over all ingested records.

**Request body:**
```json
{
  "record_type": "okved",
  "threshold": 0.65
}
```

**Response `202 Accepted`:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted"
}
```

---

## Jobs

### `GET /api/v1/jobs/{job_id}/status`

**Response `200 OK`:**
```json
{
  "job_id": "...",
  "status": "running",
  "total_records": 1000,
  "processed_records": 450,
  "progress": 0.45,
  "created_at": "2024-03-15T10:00:00Z",
  "finished_at": null,
  "error": null
}
```

`status`: `"pending"` | `"running"` | `"completed"` | `"failed"`

---

### `GET /api/v1/jobs/{job_id}/result`
Only available when `status == "completed"`. Returns `409` otherwise.

**Response `200 OK`:**
```json
{
  "job_id": "...",
  "clusters_found": 42,
  "duplicate_pairs": 78,
  "total_records": 100,
  "reduction_ratio": 0.83,
  "results": [
    {
      "cluster_id": "...",
      "record_count": 3,
      "confidence": 0.91,
      "canonical_record": {
        "canonical_name": "Разработка компьютерного программного обеспечения",
        "canonical_code": "62.01"
      }
    }
  ]
}
```

---

## Error codes

| Code | Meaning |
|------|---------|
| 401 | Invalid or missing X-API-Key |
| 404 | Job or resource not found |
| 409 | Job not completed yet |
| 422 | Validation error in request body |
