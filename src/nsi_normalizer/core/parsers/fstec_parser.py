from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET
from pathlib import Path

from nsi_normalizer.schemas.common import RawRecord


def parse_fstec_csv(source: str | Path | bytes, *, encoding: str = "utf-8") -> list[RawRecord]:
    """Parse FSTEC BDU threat/vulnerability CSV export.

    Expected columns (Russian headers from BDU export):
      Идентификатор, Наименование, Описание, Тип, Уровень опасности,
      Идентификатор CVE, Оценка CVSS, Дата публикации, Дата обновления
    """
    if isinstance(source, bytes):
        text = source.decode(encoding)
    else:
        text = Path(source).read_text(encoding=encoding)

    COL_MAP = {
        "Идентификатор": "bdu_id",
        "Наименование": "name",
        "Описание": "description",
        "Уровень опасности": "severity_raw",
        "Идентификатор CVE": "cve_ids_raw",
        "Оценка CVSS": "cvss_score_raw",
        "Дата публикации": "published_at_raw",
        "Дата обновления": "updated_at_raw",
        # English aliases
        "ID": "bdu_id",
        "Name": "name",
        "Description": "description",
        "Severity": "severity_raw",
        "CVE": "cve_ids_raw",
        "CVSS": "cvss_score_raw",
    }

    records: list[RawRecord] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        payload: dict[str, str | None] = {}
        for col, field in COL_MAP.items():
            if col in row:
                val = row[col].strip() if row[col] else None
                payload[field] = val or None

        bdu_id = payload.get("bdu_id")
        name = payload.get("name")
        if not bdu_id or not name:
            continue

        records.append(
            RawRecord(
                source="fstec_bdu_csv",
                record_type="fstec",
                raw_id=bdu_id,
                payload=payload,
            )
        )
    return records


def parse_fstec_xml(source: str | Path | bytes) -> list[RawRecord]:
    """Parse FSTEC BDU XML export format."""
    if isinstance(source, bytes):
        root = ET.fromstring(source)
    else:
        tree = ET.parse(source)
        root = tree.getroot()

    records: list[RawRecord] = []
    for vuln in root.iter("vulnerability"):
        bdu_id = (vuln.findtext("identifier") or "").strip()
        name = (vuln.findtext("name") or "").strip()
        if not bdu_id or not name:
            continue

        cve_ids_raw = vuln.findtext("cve") or ""

        records.append(
            RawRecord(
                source="fstec_bdu_xml",
                record_type="fstec",
                raw_id=bdu_id,
                payload={
                    "bdu_id": bdu_id,
                    "name": name,
                    "description": vuln.findtext("description") or None,
                    "severity_raw": vuln.findtext("severity") or None,
                    "cve_ids_raw": cve_ids_raw or None,
                    "cvss_score_raw": vuln.findtext("cvss") or None,
                    "published_at_raw": vuln.findtext("published") or None,
                    "updated_at_raw": vuln.findtext("updated") or None,
                },
            )
        )
    return records
