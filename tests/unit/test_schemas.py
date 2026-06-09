import uuid

import pytest
from pydantic import ValidationError

from nsi_normalizer.schemas.common import NormalizedRecord, RawRecord
from nsi_normalizer.schemas.fstec import SEVERITY_MAP, FstecRecord, Severity
from nsi_normalizer.schemas.okved import OkvedRecord


class TestOkvedRecord:
    @pytest.mark.parametrize("code", ["62", "62.01", "62.01.1", "47.91.2"])
    def test_valid_codes(self, code: str) -> None:
        record = OkvedRecord(code=code, name="Test")
        assert record.code == code

    @pytest.mark.parametrize("code", ["62.01 ", " 62.01", "62 .01"])
    def test_code_stripped(self, code: str) -> None:
        record = OkvedRecord(code=code, name="Test")
        assert " " not in record.code

    @pytest.mark.parametrize("code", ["6", "62.01.1.1", "AB.CD", ""])
    def test_invalid_codes(self, code: str) -> None:
        with pytest.raises(ValidationError):
            OkvedRecord(code=code, name="Test")

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OkvedRecord(code="62.01", name="")

    def test_parent_code_validated(self) -> None:
        record = OkvedRecord(code="62.01.1", name="Test", parent_code="62.01")
        assert record.parent_code == "62.01"

    def test_invalid_parent_code_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OkvedRecord(code="62.01.1", name="Test", parent_code="INVALID")


class TestFstecRecord:
    def test_valid_record(self) -> None:
        record = FstecRecord(
            bdu_id="BDU:2024-01234",
            name="Test vulnerability",
            severity=Severity.HIGH,
            cve_ids=["CVE-2024-12345"],
            cvss_score=7.5,
        )
        assert record.bdu_id == "BDU:2024-01234"
        assert record.severity == Severity.HIGH

    @pytest.mark.parametrize("bdu_id", ["BDU:2024-012", "bdu:2024-01234", "2024-01234"])
    def test_invalid_bdu_id(self, bdu_id: str) -> None:
        with pytest.raises(ValidationError):
            FstecRecord(bdu_id=bdu_id, name="Test")

    def test_cve_ids_normalized(self) -> None:
        record = FstecRecord(
            bdu_id="BDU:2024-01234",
            name="Test",
            cve_ids=["cve-2024-12345", "CVE-2024-99999", "INVALID-ID"],
        )
        assert "CVE-2024-12345" in record.cve_ids
        assert "CVE-2024-99999" in record.cve_ids
        assert len(record.cve_ids) == 2

    def test_cvss_score_bounds(self) -> None:
        with pytest.raises(ValidationError):
            FstecRecord(bdu_id="BDU:2024-01234", name="Test", cvss_score=11.0)

    def test_default_severity_unknown(self) -> None:
        record = FstecRecord(bdu_id="BDU:2024-01234", name="Test")
        assert record.severity == Severity.UNKNOWN


class TestSeverityMap:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("высокий", Severity.HIGH),
            ("High", Severity.HIGH),
            ("H", Severity.HIGH),
            ("критический", Severity.CRITICAL),
            ("medium", Severity.MEDIUM),
            ("низкий", Severity.LOW),
        ],
    )
    def test_severity_map_coverage(self, raw: str, expected: Severity) -> None:
        assert SEVERITY_MAP[raw.lower()] == expected


class TestRawRecord:
    def test_extra_fields_allowed(self) -> None:
        record = RawRecord(
            source="test",
            record_type="okved",
            payload={"code": "62.01"},
            extra_field="allowed",
        )
        assert record.model_extra is not None

    def test_valid_record_types(self) -> None:
        for rt in ("okved", "fstec", "generic"):
            r = RawRecord(source="s", record_type=rt, payload={})  # type: ignore[arg-type]
            assert r.record_type == rt


class TestNormalizedRecord:
    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            NormalizedRecord(
                record_type="okved",
                canonical_name="Test",
                confidence=1.5,
                source="test",
            )

    def test_canonical_id_auto_generated(self) -> None:
        r = NormalizedRecord(
            record_type="okved",
            canonical_name="Test",
            confidence=0.9,
            source="test",
        )
        assert isinstance(r.canonical_id, uuid.UUID)
