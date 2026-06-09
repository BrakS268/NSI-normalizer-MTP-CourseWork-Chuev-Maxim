from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EM_DASH_RE = re.compile(r"[—–]")
_MULTI_DOT_RE = re.compile(r"\.{2,}")
_OKVED_CODE_RE = re.compile(r"^(\d{2})\.?(\d{0,2})\.?(\d?)$")

_LEGAL_SUFFIXES = re.compile(
    r"\b(ООО|ОАО|ЗАО|АО|ИП|ПАО|НКО|ФГУП|МУП|ГУП|ГКУ|ФКУ)\b",
    re.IGNORECASE,
)

_ABBREV_MAP: dict[str, str] = {
    # Разработка ПО
    "разраб.": "разработка",
    "прогр.": "программного",
    "обеспеч.": "обеспечения",
    # Торговля
    "розн.": "розничная",
    "розничн.": "розничная",
    "опт.": "оптовая",
    "инт.": "интернет",
    # Производство / организация
    "произв.": "производство",
    "орг-ция": "организация",
    "орг.": "организация",
    # Деятельность / область
    "деят.": "деятельность",
    "обл.": "области",
    "тех.": "технических",
    "техн.": "технических",
    "инф.": "информационных",
    "инф.-комм.": "информационно-коммуникационной",
    # Услуги
    "услуг.": "услуги",
    "управл.": "управление",
    "управл-ние": "управление",
}


def unicode_normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def remove_control_chars(text: str) -> str:
    return _CONTROL_CHARS_RE.sub("", text)


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_dashes(text: str) -> str:
    return _EM_DASH_RE.sub("-", text)


def expand_abbreviations(text: str) -> str:
    for abbrev, expanded in _ABBREV_MAP.items():
        text = re.sub(re.escape(abbrev), expanded, text, flags=re.IGNORECASE)
    return text


def strip_legal_suffixes(text: str) -> str:
    return collapse_whitespace(_LEGAL_SUFFIXES.sub("", text))


def normalize_okved_code(code: str) -> str:
    """Normalize OKVED code to canonical XX, XX.XX or XX.XX.X form."""
    code = code.strip().replace(" ", "")
    match = _OKVED_CODE_RE.match(code)
    if not match:
        return code
    section, sub, detail = match.group(1), match.group(2), match.group(3)
    if not sub:
        return section
    if not detail:
        return f"{section}.{sub.zfill(2)}"
    return f"{section}.{sub.zfill(2)}.{detail}"


def clean_text(
    text: str,
    *,
    strip_legal: bool = False,
    expand_abbrevs: bool = True,
    lowercase: bool = False,
) -> str:
    text = unicode_normalize(text)
    text = remove_control_chars(text)
    text = normalize_dashes(text)
    text = _MULTI_DOT_RE.sub(".", text)
    if expand_abbrevs:
        text = expand_abbreviations(text)
    if strip_legal:
        text = strip_legal_suffixes(text)
    text = collapse_whitespace(text)
    if lowercase:
        text = text.lower()
    return text
