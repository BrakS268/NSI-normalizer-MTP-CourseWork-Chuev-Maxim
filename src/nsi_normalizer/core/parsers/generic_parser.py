from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from nsi_normalizer.schemas.common import RawRecord, RecordType


def parse_json(
    source: str | Path | bytes,
    *,
    source_name: str = "generic_json",
    record_type: RecordType = "generic",
) -> list[RawRecord]:
    """Parse a JSON array of objects into RawRecords."""
    if isinstance(source, bytes):
        data: Any = json.loads(source)
    elif isinstance(source, str) and source.lstrip().startswith("["):
        data = json.loads(source)
    else:
        data = json.loads(Path(source).read_bytes())

    if not isinstance(data, list):
        data = [data]

    records: list[RawRecord] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        raw_id = str(item.get("id") or item.get("code") or i)
        records.append(
            RawRecord(
                source=source_name,
                record_type=record_type,
                raw_id=raw_id,
                payload=item,
            )
        )
    return records


def parse_csv(
    source: str | Path | bytes,
    *,
    source_name: str = "generic_csv",
    record_type: RecordType = "generic",
    encoding: str = "utf-8",
) -> list[RawRecord]:
    """Parse arbitrary CSV into RawRecords. First row must be headers."""
    if isinstance(source, bytes):
        text = source.decode(encoding)
    else:
        text = Path(source).read_text(encoding=encoding)

    records: list[RawRecord] = []
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader):
        payload = {k: v for k, v in row.items() if v}
        raw_id = payload.get("id") or payload.get("code") or str(i)
        records.append(
            RawRecord(
                source=source_name,
                record_type=record_type,
                raw_id=raw_id,
                payload=payload,
            )
        )
    return records
