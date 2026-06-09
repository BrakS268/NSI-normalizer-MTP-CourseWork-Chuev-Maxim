from __future__ import annotations

import csv
import io
from pathlib import Path

import defusedxml.ElementTree as ET

from nsi_normalizer.schemas.common import RawRecord


def parse_okved_xml(source: str | Path | bytes) -> list[RawRecord]:
    """Parse OKVED-2 XML in Federal Tax Service format.

    Expected structure:
      <OKVED2>
        <Item RAZDEL="A" KOD="01" NAIM="Растениеводство..." PRIM="..."/>
      </OKVED2>
    """
    if isinstance(source, bytes):
        root = ET.fromstring(source)
    else:
        tree = ET.parse(source)
        root = tree.getroot()

    records: list[RawRecord] = []
    for item in root.iter("Item"):
        code = item.get("KOD", "").strip()
        name = item.get("NAIM", "").strip()
        if not code or not name:
            continue
        records.append(
            RawRecord(
                source="okved2_fns",
                record_type="okved",
                raw_id=code,
                payload={
                    "code": code,
                    "name": name,
                    "description": item.get("PRIM", "") or None,
                    "section": item.get("RAZDEL") or None,
                    "parent_code": _parent_code(code),
                },
            )
        )
    return records


def parse_okved_csv(source: str | Path | bytes, *, encoding: str = "utf-8") -> list[RawRecord]:
    """Parse OKVED data from CSV with columns: code, name, description (optional)."""
    if isinstance(source, bytes):
        text = source.decode(encoding)
    else:
        text = Path(source).read_text(encoding=encoding)

    records: list[RawRecord] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        code = (row.get("code") or row.get("КОД") or "").strip()
        name = (row.get("name") or row.get("НАИМ") or "").strip()
        if not code or not name:
            continue
        records.append(
            RawRecord(
                source="okved2_csv",
                record_type="okved",
                raw_id=code,
                payload={
                    "code": code,
                    "name": name,
                    "description": (row.get("description") or row.get("ПРИМ") or None),
                    "parent_code": _parent_code(code),
                },
            )
        )
    return records


def _parent_code(code: str) -> str | None:
    """Derive parent code: 62.01.1 -> 62.01, 62.01 -> 62, 62 -> None."""
    parts = code.split(".")
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])
