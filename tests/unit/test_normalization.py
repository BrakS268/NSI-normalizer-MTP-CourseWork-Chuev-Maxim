from datetime import date

import pytest

from nsi_normalizer.core.normalization.canonical_selector import (
    elect_canonical,
    normalize_cluster,
    normalize_fstec_record,
    normalize_okved_record,
)
from nsi_normalizer.core.normalization.field_normalizer import (
    normalize_cve_ids,
    normalize_cvss,
    normalize_date,
    normalize_description,
    normalize_name,
    normalize_okved_code,
    normalize_severity,
)
from nsi_normalizer.schemas.common import RawRecord
from nsi_normalizer.schemas.fstec import Severity


def _okved(code: str, name: str, source: str = "okved2_fns", desc: str = "") -> RawRecord:
    return RawRecord(
        source=source,
        record_type="okved",
        raw_id=code,
        payload={"code": code, "name": name, "description": desc or None},
    )


def _fstec(bdu_id: str, name: str, **kw: str) -> RawRecord:
    return RawRecord(
        source="fstec_bdu_csv",
        record_type="fstec",
        raw_id=bdu_id,
        payload={"bdu_id": bdu_id, "name": name, **kw},
    )


class TestFieldNormalizer:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("  лишние пробелы  ", "лишние пробелы"),
            ("много   внутри", "много внутри"),
            ("норм", "норм"),
        ],
    )
    def test_normalize_name(self, raw: str, expected: str) -> None:
        assert normalize_name(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("62.1", "62.01"),
            ("62.01", "62.01"),
            ("62", "62"),
            ("62.01.1", "62.01.1"),
            (" 47.91 ", "47.91"),
        ],
    )
    def test_normalize_okved_code(self, raw: str, expected: str) -> None:
        assert normalize_okved_code(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("высокий", Severity.HIGH),
            ("High", Severity.HIGH),
            ("H", Severity.HIGH),
            ("критический", Severity.CRITICAL),
            ("средний", Severity.MEDIUM),
            ("низкий", Severity.LOW),
            ("неизвестно", Severity.UNKNOWN),
            ("", Severity.UNKNOWN),
        ],
    )
    def test_normalize_severity(self, raw: str, expected: Severity) -> None:
        assert normalize_severity(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("2024-03-15", date(2024, 3, 15)),
            ("15.03.2024", date(2024, 3, 15)),
            ("", None),
            ("not-a-date", None),
        ],
    )
    def test_normalize_date(self, raw: str, expected: date | None) -> None:
        assert normalize_date(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("CVE-2024-12345", ["CVE-2024-12345"]),
            ("cve-2024-12345", ["CVE-2024-12345"]),
            ("CVE-2024-12345, CVE-2023-99999", ["CVE-2024-12345", "CVE-2023-99999"]),
            ("нет идентификаторов", []),
            ("", []),
        ],
    )
    def test_normalize_cve_ids(self, raw: str, expected: list[str]) -> None:
        assert normalize_cve_ids(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("7.5", 7.5),
            ("7,5", 7.5),
            ("10.0", 10.0),
            ("0.0", 0.0),
            ("11.0", None),
            ("abc", None),
            ("", None),
        ],
    )
    def test_normalize_cvss(self, raw: str, expected: float | None) -> None:
        assert normalize_cvss(raw) == expected

    def test_normalize_description_deduplicates_sentences(self) -> None:
        desc = "Первое предложение. Второе предложение. Первое предложение."
        result = normalize_description(desc)
        assert result.count("Первое предложение") == 1

    def test_normalize_description_caps_sentences(self) -> None:
        long_desc = ". ".join([f"Предложение {i}" for i in range(20)]) + "."
        result = normalize_description(long_desc, max_sentences=5)
        assert result.count("Предложение") <= 5


class TestOkvedNormalizer:
    def test_normalizes_code_format(self) -> None:
        record = _okved("62.1", "Разработка ПО")
        result = normalize_okved_record(record)
        assert result.canonical_code == "62.01"
        assert result.normalized_payload["code"] == "62.01"

    def test_normalizes_name(self) -> None:
        record = _okved("62.01", "  Разработка   ПО  ")
        result = normalize_okved_record(record)
        assert result.canonical_name == "Разработка ПО"

    def test_record_type_preserved(self) -> None:
        result = normalize_okved_record(_okved("62.01", "Тест"))
        assert result.record_type == "okved"

    def test_confidence_between_0_and_1(self) -> None:
        result = normalize_okved_record(_okved("62.01", "Тест"))
        assert 0.0 <= result.confidence <= 1.0


class TestFstecNormalizer:
    def test_severity_normalized(self) -> None:
        record = _fstec("BDU:2024-01234", "Уязвимость", severity_raw="Высокий")
        result = normalize_fstec_record(record)
        assert result.normalized_payload["severity"] == "high"

    def test_cve_ids_extracted(self) -> None:
        record = _fstec("BDU:2024-01234", "Уязвимость", cve_ids_raw="CVE-2024-12345")
        result = normalize_fstec_record(record)
        assert "CVE-2024-12345" in result.normalized_payload["cve_ids"]

    def test_cvss_parsed(self) -> None:
        record = _fstec("BDU:2024-01234", "Уязвимость", cvss_score_raw="7.5")
        result = normalize_fstec_record(record)
        assert result.normalized_payload["cvss_score"] == 7.5

    def test_bdu_id_as_canonical_code(self) -> None:
        record = _fstec("BDU:2024-01234", "Уязвимость")
        result = normalize_fstec_record(record)
        assert result.canonical_code == "BDU:2024-01234"


class TestCanonicalSelector:
    def test_elect_prefers_trusted_source(self) -> None:
        official = _okved("62.01", "Разработка ПО", source="okved2_fns", desc="Длинное описание")
        generic = _okved("62.01", "Разработка ПО", source="generic_csv")
        best = elect_canonical([generic, official])
        assert best.source == "okved2_fns"

    def test_elect_prefers_more_complete_record(self) -> None:
        full = _okved("62.01", "Разработка ПО", desc="Подробное описание процесса")
        empty = _okved("62.01", "ПО")
        best = elect_canonical([empty, full])
        assert best is full

    def test_normalize_cluster_boosts_confidence(self) -> None:
        records = [_okved("62.01", f"Разработка ПО вариант {i}") for i in range(5)]
        single = [_okved("62.01", "Разработка ПО")]
        cluster_result = normalize_cluster(records)
        single_result = normalize_cluster(single)
        assert cluster_result.confidence >= single_result.confidence

    def test_normalize_cluster_confidence_max_1(self) -> None:
        records = [_okved("62.01", "Разработка ПО") for _ in range(20)]
        result = normalize_cluster(records)
        assert result.confidence <= 1.0
