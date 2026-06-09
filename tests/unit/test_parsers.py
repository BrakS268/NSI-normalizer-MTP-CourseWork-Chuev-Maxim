import pytest

from nsi_normalizer.core.parsers.okved_parser import parse_okved_xml, parse_okved_csv
from nsi_normalizer.core.parsers.fstec_parser import parse_fstec_csv, parse_fstec_xml
from nsi_normalizer.core.parsers.generic_parser import parse_json, parse_csv


OKVED_XML_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<OKVED2>
  <Item RAZDEL="J" KOD="62" NAIM="Разработка компьютерного программного обеспечения"/>
  <Item RAZDEL="J" KOD="62.01" NAIM="Разработка компьютерного программного обеспечения" PRIM="Включает разработку ПО"/>
  <Item RAZDEL="J" KOD="62.01.1" NAIM="Разработка программного обеспечения"/>
  <Item KOD="" NAIM="Пустой код — должен быть пропущен"/>
</OKVED2>""".encode()

OKVED_CSV_FIXTURE = """code,name,description
62,Разработка ПО,
62.01,Разработка компьютерного программного обеспечения,Включает разработку
62.01.1,Разработка ПО системы,"""

FSTEC_CSV_FIXTURE = """Идентификатор,Наименование,Описание,Уровень опасности,Идентификатор CVE,Оценка CVSS
BDU:2024-01234,Уязвимость ядра Linux,Описание уязвимости,Высокий,CVE-2024-12345,7.5
BDU:2024-05678,Уязвимость OpenSSL,,Средний,,5.3
,Без идентификатора,Пропускаем,,, """

FSTEC_XML_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<vulnerabilities>
  <vulnerability>
    <identifier>BDU:2024-01234</identifier>
    <name>Уязвимость ядра Linux</name>
    <description>Описание</description>
    <severity>высокий</severity>
    <cve>CVE-2024-12345</cve>
    <cvss>7.5</cvss>
  </vulnerability>
  <vulnerability>
    <identifier></identifier>
    <name>Без ID — пропускаем</name>
  </vulnerability>
</vulnerabilities>""".encode()

GENERIC_JSON_FIXTURE = '[{"id": "1", "name": "Запись 1"}, {"id": "2", "name": "Запись 2"}]'.encode()
GENERIC_CSV_FIXTURE = "id,name,value\n1,Запись 1,100\n2,Запись 2,200"


class TestOkvedParser:
    def test_xml_parses_all_valid_items(self) -> None:
        records = parse_okved_xml(OKVED_XML_FIXTURE)
        assert len(records) == 3

    def test_xml_skips_empty_code(self) -> None:
        records = parse_okved_xml(OKVED_XML_FIXTURE)
        codes = [r.payload["code"] for r in records]
        assert "" not in codes

    def test_xml_record_type(self) -> None:
        records = parse_okved_xml(OKVED_XML_FIXTURE)
        assert all(r.record_type == "okved" for r in records)

    def test_xml_section_preserved(self) -> None:
        records = parse_okved_xml(OKVED_XML_FIXTURE)
        assert records[0].payload["section"] == "J"

    def test_xml_parent_code_derived(self) -> None:
        records = parse_okved_xml(OKVED_XML_FIXTURE)
        child = next(r for r in records if r.payload["code"] == "62.01.1")
        assert child.payload["parent_code"] == "62.01"

    def test_csv_parses_records(self) -> None:
        records = parse_okved_csv(OKVED_CSV_FIXTURE.encode())
        assert len(records) == 3

    def test_csv_raw_id_set(self) -> None:
        records = parse_okved_csv(OKVED_CSV_FIXTURE.encode())
        assert records[0].raw_id == "62"


class TestFstecParser:
    def test_csv_parses_valid_rows(self) -> None:
        records = parse_fstec_csv(FSTEC_CSV_FIXTURE.encode())
        assert len(records) == 2

    def test_csv_skips_missing_id(self) -> None:
        records = parse_fstec_csv(FSTEC_CSV_FIXTURE.encode())
        bdu_ids = [r.raw_id for r in records]
        assert None not in bdu_ids

    def test_csv_severity_in_payload(self) -> None:
        records = parse_fstec_csv(FSTEC_CSV_FIXTURE.encode())
        first = records[0]
        assert first.payload.get("severity_raw") == "Высокий"

    def test_xml_parses_vulnerability(self) -> None:
        records = parse_fstec_xml(FSTEC_XML_FIXTURE)
        assert len(records) == 1
        assert records[0].payload["bdu_id"] == "BDU:2024-01234"

    def test_xml_skips_empty_id(self) -> None:
        records = parse_fstec_xml(FSTEC_XML_FIXTURE)
        assert all(r.raw_id for r in records)


class TestGenericParser:
    def test_json_parses_array(self) -> None:
        records = parse_json(GENERIC_JSON_FIXTURE)
        assert len(records) == 2
        assert records[0].payload["name"] == "Запись 1"

    def test_csv_parses_rows(self) -> None:
        records = parse_csv(GENERIC_CSV_FIXTURE.encode())
        assert len(records) == 2

    def test_csv_raw_id_from_id_column(self) -> None:
        records = parse_csv(GENERIC_CSV_FIXTURE.encode())
        assert records[0].raw_id == "1"
