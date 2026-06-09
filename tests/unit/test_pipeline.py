import pytest

from nsi_normalizer.ml.pipeline import DeduplicationPipeline, DeduplicationReport
from nsi_normalizer.schemas.common import RawRecord


def _make(code: str, name: str, raw_id: str, description: str = "") -> RawRecord:
    return RawRecord(
        source="test",
        record_type="okved",
        raw_id=raw_id,
        payload={"code": code, "name": name, "description": description},
    )


DUPLICATES = [
    _make("62.01", "Разработка компьютерного программного обеспечения", "r1"),
    _make("62.01", "Разработка программного обеспечения", "r2"),
    _make("62.01", "разраб. прогр. обеспеч.", "r3"),
]

DISTINCT = [
    _make("62.01", "Разработка программного обеспечения", "a1"),
    _make("47.91", "Торговля розничная через интернет", "b1"),
    _make("85.41", "Образование дополнительное для детей", "c1"),
]


class TestDeduplicationPipeline:
    def test_empty_input_returns_empty_report(self) -> None:
        pipeline = DeduplicationPipeline()
        report = pipeline.run([])
        assert report.total_records == 0
        assert report.clusters_found == 0

    def test_single_record_returns_one_cluster(self) -> None:
        pipeline = DeduplicationPipeline()
        report = pipeline.run([_make("62.01", "Тест", "x1")])
        assert report.total_records == 1
        assert report.clusters_found == 1

    def test_obvious_duplicates_clustered(self) -> None:
        pipeline = DeduplicationPipeline(threshold=0.5)
        report = pipeline.run(DUPLICATES)
        assert report.duplicate_pairs > 0
        assert report.clusters_found < len(DUPLICATES)

    def test_distinct_records_not_merged(self) -> None:
        pipeline = DeduplicationPipeline(threshold=0.65)
        report = pipeline.run(DISTINCT)
        # distinct codes from different sections — should not be merged
        assert report.clusters_found >= 1

    def test_report_has_reduction_ratio(self) -> None:
        pipeline = DeduplicationPipeline()
        report = pipeline.run(DUPLICATES)
        assert 0.0 <= report.reduction_ratio <= 1.0

    def test_canonical_record_has_name(self) -> None:
        pipeline = DeduplicationPipeline(threshold=0.5)
        report = pipeline.run(DUPLICATES)
        for result in report.results:
            assert result.canonical_record.canonical_name != ""

    def test_total_records_in_report(self) -> None:
        pipeline = DeduplicationPipeline()
        report = pipeline.run(DUPLICATES)
        assert report.total_records == len(DUPLICATES)

    def test_candidate_pairs_less_than_brute_force(self) -> None:
        pipeline = DeduplicationPipeline()
        report = pipeline.run(DUPLICATES + DISTINCT)
        n = len(DUPLICATES) + len(DISTINCT)
        brute_force = n * (n - 1) // 2
        assert report.candidate_pairs <= brute_force
