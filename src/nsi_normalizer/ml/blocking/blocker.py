from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

from nsi_normalizer.core.cleaning.text_cleaner import clean_text, normalize_okved_code
from nsi_normalizer.schemas.common import RawRecord


class CandidatePair(NamedTuple):
    left_id: str
    right_id: str


def _record_id(record: RawRecord) -> str:
    return record.raw_id or str(id(record))


def _clean_name(record: RawRecord) -> str:
    name = record.payload.get("name", "")
    return clean_text(str(name), lowercase=True) if name else ""


def _code_prefix(record: RawRecord, length: int = 2) -> str:
    code = record.payload.get("code", "")
    if not code:
        return ""
    normalized = normalize_okved_code(str(code))
    return normalized[:length]


def _sorted_neighborhood_key(record: RawRecord) -> str:
    """Sort key: first 4 chars of cleaned name."""
    name = _clean_name(record)
    return name[:4] if len(name) >= 4 else name


class CodePrefixBlocker:
    """Block by first N digits of OKVED code — only pairs within same prefix."""

    def __init__(self, prefix_length: int = 2) -> None:
        self.prefix_length = prefix_length

    def get_candidate_pairs(self, records: list[RawRecord]) -> set[CandidatePair]:
        buckets: dict[str, list[str]] = {}
        for record in records:
            prefix = _code_prefix(record, self.prefix_length)
            if not prefix:
                continue
            rid = _record_id(record)
            buckets.setdefault(prefix, []).append(rid)

        pairs: set[CandidatePair] = set()
        for bucket in buckets.values():
            for i in range(len(bucket)):
                for j in range(i + 1, len(bucket)):
                    a, b = bucket[i], bucket[j]
                    pairs.add(CandidatePair(min(a, b), max(a, b)))
        return pairs


class SortedNeighborhoodBlocker:
    """Sorted Neighborhood blocking on cleaned name — sliding window of size W."""

    def __init__(self, window: int = 3) -> None:
        self.window = window

    def get_candidate_pairs(self, records: list[RawRecord]) -> set[CandidatePair]:
        indexed = sorted(
            [(_sorted_neighborhood_key(r), _record_id(r)) for r in records],
            key=lambda x: x[0],
        )
        pairs: set[CandidatePair] = set()
        for i, (_, rid_i) in enumerate(indexed):
            for j in range(i + 1, min(i + self.window, len(indexed))):
                _, rid_j = indexed[j]
                pairs.add(CandidatePair(min(rid_i, rid_j), max(rid_i, rid_j)))
        return pairs


class CompositeBlocker:
    """Union of multiple blockers — maximises recall."""

    def __init__(self, blockers: list[CodePrefixBlocker | SortedNeighborhoodBlocker]) -> None:
        self.blockers = blockers

    def get_candidate_pairs(self, records: list[RawRecord]) -> set[CandidatePair]:
        all_pairs: set[CandidatePair] = set()
        for blocker in self.blockers:
            all_pairs |= blocker.get_candidate_pairs(records)
        return all_pairs


def default_blocker() -> CompositeBlocker:
    return CompositeBlocker([
        CodePrefixBlocker(prefix_length=2),
        SortedNeighborhoodBlocker(window=5),
    ])
