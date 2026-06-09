from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

CVE_ID_RE = re.compile(r"^CVE-\d{4}-\d{4,}$")
BDU_ID_RE = re.compile(r"^BDU:\d{4}-\d{5}$")


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"
    UNKNOWN = "unknown"


SEVERITY_MAP: dict[str, Severity] = {
    "критический": Severity.CRITICAL,
    "critical": Severity.CRITICAL,
    "высокий": Severity.HIGH,
    "high": Severity.HIGH,
    "h": Severity.HIGH,
    "средний": Severity.MEDIUM,
    "medium": Severity.MEDIUM,
    "m": Severity.MEDIUM,
    "низкий": Severity.LOW,
    "low": Severity.LOW,
    "l": Severity.LOW,
    "информационный": Severity.INFORMATIONAL,
    "info": Severity.INFORMATIONAL,
    "informational": Severity.INFORMATIONAL,
}


class FstecRecord(BaseModel):
    bdu_id: Annotated[str, Field(description="BDU identifier, e.g. BDU:2024-01234")]
    name: str = Field(..., min_length=1, max_length=1000)
    description: str | None = None
    severity: Severity = Severity.UNKNOWN
    cve_ids: list[str] = Field(default_factory=list)
    cvss_score: float | None = Field(None, ge=0.0, le=10.0)
    published_at: date | None = None
    updated_at: date | None = None
    affected_software: list[str] = Field(default_factory=list)

    @field_validator("bdu_id")
    @classmethod
    def validate_bdu_id(cls, v: str) -> str:
        v = v.strip()
        if not BDU_ID_RE.match(v):
            raise ValueError(f"Invalid BDU ID format: '{v}'. Expected BDU:YYYY-NNNNN")
        return v

    @field_validator("cve_ids", mode="before")
    @classmethod
    def validate_cve_ids(cls, v: list[str]) -> list[str]:
        result = []
        for cve in v:
            cve = cve.strip().upper()
            if CVE_ID_RE.match(cve):
                result.append(cve)
        return result


class FstecRawRecord(BaseModel):
    """Loose schema for raw FSTEC BDU data before normalization."""

    bdu_id: str
    name: str
    description: str | None = None
    severity_raw: str | None = None
    cve_ids_raw: str | None = None
    cvss_score_raw: str | None = None
    published_at_raw: str | None = None
    updated_at_raw: str | None = None
