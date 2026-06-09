from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

OKVED_CODE_RE = re.compile(r"^\d{2}(\.\d{1,2}){0,2}$")


class OkvedRecord(BaseModel):
    code: Annotated[str, Field(description="OKVED-2 classifier code, e.g. 62.01 or 62.01.1")]
    name: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    parent_code: str | None = None
    section: str | None = Field(None, description="Section letter, e.g. 'J'")
    version: str = Field(default="OKVED-2", description="Classifier version")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        normalized = v.strip().replace(" ", "")
        if not OKVED_CODE_RE.match(normalized):
            raise ValueError(f"Invalid OKVED code format: '{v}'. Expected XX or XX.XX or XX.XX.X")
        return normalized

    @field_validator("parent_code")
    @classmethod
    def validate_parent_code(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = v.strip().replace(" ", "")
        if not OKVED_CODE_RE.match(normalized):
            raise ValueError(f"Invalid parent OKVED code format: '{v}'")
        return normalized


class OkvedRawRecord(BaseModel):
    """Loose schema for parsing raw OKVED data before validation."""

    code: str
    name: str
    description: str | None = None
    parent_code: str | None = None
    section: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)
