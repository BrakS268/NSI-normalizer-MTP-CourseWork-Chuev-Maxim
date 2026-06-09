from __future__ import annotations

import re
from datetime import date

import dateparser

from nsi_normalizer.schemas.fstec import SEVERITY_MAP, Severity

_OKVED_CODE_RE = re.compile(r"^(\d{2})\.?(\d{0,2})\.?(\d?)$")
_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)
_MULTI_SPACE = re.compile(r"\s+")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def normalize_name(raw: str) -> str:
    """Strip extra whitespace and collapse internal spaces."""
    return _MULTI_SPACE.sub(" ", raw.strip())


def normalize_okved_code(raw: str) -> str:
    """Bring OKVED code to canonical XX, XX.XX, or XX.XX.X form."""
    code = raw.strip().replace(" ", "")
    match = _OKVED_CODE_RE.match(code)
    if not match:
        return code
    section = match.group(1)
    sub = match.group(2)
    detail = match.group(3)
    if not sub:
        return section
    if not detail:
        return f"{section}.{sub.zfill(2)}"
    return f"{section}.{sub.zfill(2)}.{detail}"


def normalize_severity(raw: str) -> Severity:
    """Map free-text severity to Severity enum (Russian and English)."""
    return SEVERITY_MAP.get(raw.strip().lower(), Severity.UNKNOWN)


def normalize_date(raw: str) -> date | None:
    """Parse a date string in any common format, return date or None."""
    if not raw or not raw.strip():
        return None
    parsed = dateparser.parse(
        raw.strip(),
        languages=["ru", "en"],
        settings={"RETURN_AS_TIMEZONE_AWARE": False, "PREFER_DAY_OF_MONTH": "first"},
    )
    if parsed is None:
        return None
    return parsed.date()


def normalize_cve_ids(raw: str) -> list[str]:
    """Extract and uppercase all CVE IDs from a raw string."""
    return [m.upper() for m in _CVE_RE.findall(raw)]


def normalize_cvss(raw: str) -> float | None:
    """Parse CVSS score string to float, return None if invalid."""
    try:
        value = float(raw.strip().replace(",", "."))
        if 0.0 <= value <= 10.0:
            return value
        return None
    except (ValueError, AttributeError):
        return None


def normalize_description(raw: str, max_sentences: int = 10) -> str:
    """Clean description: collapse whitespace, deduplicate sentences, cap length."""
    text = _MULTI_SPACE.sub(" ", raw.strip())
    sentences = _SENTENCE_END.split(text)
    seen: set[str] = set()
    unique: list[str] = []
    for s in sentences:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            unique.append(s)
    return " ".join(unique[:max_sentences])
