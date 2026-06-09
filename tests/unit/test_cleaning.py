import pytest

from nsi_normalizer.core.cleaning.text_cleaner import (
    clean_text,
    normalize_okved_code,
    collapse_whitespace,
    unicode_normalize,
    strip_legal_suffixes,
)
from nsi_normalizer.core.cleaning.pipeline import CleaningPipeline
from nsi_normalizer.schemas.common import RawRecord


class TestTextCleaner:
    @pytest.mark.parametrize("raw,expected", [
        ("  лишние   пробелы  ", "лишние пробелы"),
        ("строка\tс\tтабами", "строка с табами"),
        ("много\n\nпустых\n\nстрок", "много пустых строк"),
    ])
    def test_collapse_whitespace(self, raw: str, expected: str) -> None:
        assert collapse_whitespace(raw) == expected

    def test_unicode_normalize_nfc(self) -> None:
        # NFC: composed form
        text = "е́" # е + combining acute = ё in NFD
        result = unicode_normalize(text)
        assert len(result) <= len(text)

    @pytest.mark.parametrize("raw,expected", [
        ("ООО Рога и Копыта", "Рога и Копыта"),
        ("ОАО  Газпром", "Газпром"),
        ("ИП Иванов", "Иванов"),
    ])
    def test_strip_legal_suffixes(self, raw: str, expected: str) -> None:
        assert strip_legal_suffixes(raw) == expected

    def test_clean_text_removes_control_chars(self) -> None:
        result = clean_text("нормальный\x00текст\x1fс мусором")
        assert "\x00" not in result
        assert "\x1f" not in result

    def test_clean_text_normalizes_dashes(self) -> None:
        result = clean_text("раздел — подраздел")
        assert "—" not in result
        assert "-" in result

    def test_clean_text_lowercase(self) -> None:
        result = clean_text("Разработка ПО", lowercase=True)
        assert result == result.lower()

    def test_clean_text_expand_abbreviations(self) -> None:
        result = clean_text("Разраб. прогр. обеспеч.", expand_abbrevs=True)
        assert "разработка" in result.lower()


class TestOkvedCodeNormalizer:
    @pytest.mark.parametrize("raw,expected", [
        ("62", "62"),
        ("62.01", "62.01"),
        ("62.1", "62.01"),
        ("62.01.1", "62.01.1"),
        (" 62.01 ", "62.01"),
        ("47.91.2", "47.91.2"),
    ])
    def test_normalize_code(self, raw: str, expected: str) -> None:
        assert normalize_okved_code(raw) == expected

    def test_invalid_code_returned_as_is(self) -> None:
        assert normalize_okved_code("INVALID") == "INVALID"


class TestCleaningPipeline:
    def _make_record(self, **payload: object) -> RawRecord:
        return RawRecord(source="test", record_type="okved", payload=dict(payload))

    def test_pipeline_cleans_name(self) -> None:
        pipeline = CleaningPipeline()
        record = self._make_record(name="  ООО  Рога  и  Копыта  ", code="62.01")
        result = pipeline.run_one(record)
        assert result.payload["name"] == "Рога и Копыта"

    def test_pipeline_normalizes_okved_code(self) -> None:
        pipeline = CleaningPipeline()
        record = self._make_record(name="Тест", code="62.1")
        result = pipeline.run_one(record)
        assert result.payload["code"] == "62.01"

    def test_pipeline_normalizes_fstec_severity(self) -> None:
        pipeline = CleaningPipeline()
        record = RawRecord(
            source="test",
            record_type="fstec",
            payload={"name": "Уязвимость", "severity_raw": "Высокий"},
        )
        result = pipeline.run_one(record)
        assert result.payload["severity"] == "high"

    def test_pipeline_run_batch(self) -> None:
        pipeline = CleaningPipeline()
        records = [
            self._make_record(name=f"  Запись {i}  ", code="62.01")
            for i in range(5)
        ]
        results = pipeline.run(records)
        assert len(results) == 5
        assert all(not r.payload["name"].startswith(" ") for r in results)

    def test_pipeline_add_step(self) -> None:
        def custom_step(record: RawRecord) -> RawRecord:
            payload = dict(record.payload)
            payload["custom"] = "added"
            return record.model_copy(update={"payload": payload})

        pipeline = CleaningPipeline().add_step(custom_step)
        record = self._make_record(name="Тест", code="62.01")
        result = pipeline.run_one(record)
        assert result.payload["custom"] == "added"
