import pytest

from nsi_normalizer.ml.blocking.blocker import (
    CodePrefixBlocker,
    SortedNeighborhoodBlocker,
    CompositeBlocker,
    CandidatePair,
    default_blocker,
)
from nsi_normalizer.schemas.common import RawRecord


def _make(code: str, name: str, raw_id: str) -> RawRecord:
    return RawRecord(
        source="test",
        record_type="okved",
        raw_id=raw_id,
        payload={"code": code, "name": name},
    )


RECORDS = [
    _make("62.01", "Разработка программного обеспечения", "r1"),
    _make("62.01", "Разраб. прогр. обеспеч.", "r2"),
    _make("62.09", "Деятельность в области IT", "r3"),
    _make("47.91", "Торговля через интернет", "r4"),
    _make("47.91.2", "Интернет-торговля", "r5"),
]


class TestCodePrefixBlocker:
    def test_same_prefix_paired(self) -> None:
        blocker = CodePrefixBlocker(prefix_length=2)
        pairs = blocker.get_candidate_pairs(RECORDS)
        assert CandidatePair("r1", "r2") in pairs or CandidatePair("r2", "r1") in pairs

    def test_different_prefix_not_paired(self) -> None:
        blocker = CodePrefixBlocker(prefix_length=2)
        pairs = blocker.get_candidate_pairs(RECORDS)
        # r1 (62.*) and r4 (47.*) must not be paired by prefix blocker
        assert CandidatePair("r1", "r4") not in pairs
        assert CandidatePair("r4", "r1") not in pairs

    def test_no_self_pairs(self) -> None:
        blocker = CodePrefixBlocker(prefix_length=2)
        pairs = blocker.get_candidate_pairs(RECORDS)
        for pair in pairs:
            assert pair.left_id != pair.right_id

    def test_pairs_are_ordered(self) -> None:
        blocker = CodePrefixBlocker(prefix_length=2)
        pairs = blocker.get_candidate_pairs(RECORDS)
        for pair in pairs:
            assert pair.left_id <= pair.right_id


class TestSortedNeighborhoodBlocker:
    def test_produces_pairs(self) -> None:
        blocker = SortedNeighborhoodBlocker(window=3)
        pairs = blocker.get_candidate_pairs(RECORDS)
        assert len(pairs) > 0

    def test_window_limits_pairs(self) -> None:
        blocker_small = SortedNeighborhoodBlocker(window=2)
        blocker_large = SortedNeighborhoodBlocker(window=10)
        pairs_small = blocker_small.get_candidate_pairs(RECORDS)
        pairs_large = blocker_large.get_candidate_pairs(RECORDS)
        assert len(pairs_small) <= len(pairs_large)


class TestCompositeBlocker:
    def test_union_of_blockers(self) -> None:
        b1 = CodePrefixBlocker(prefix_length=2)
        b2 = SortedNeighborhoodBlocker(window=3)
        composite = CompositeBlocker([b1, b2])
        pairs = composite.get_candidate_pairs(RECORDS)
        assert len(pairs) >= len(b1.get_candidate_pairs(RECORDS))
        assert len(pairs) >= len(b2.get_candidate_pairs(RECORDS))

    def test_default_blocker_returns_composite(self) -> None:
        blocker = default_blocker()
        pairs = blocker.get_candidate_pairs(RECORDS)
        assert len(pairs) > 0
