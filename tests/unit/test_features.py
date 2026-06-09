from nsi_normalizer.ml.features.feature_extractor import (
    FEATURE_NAMES,
    extract_features,
    features_to_list,
)
from nsi_normalizer.schemas.common import RawRecord


def _make(code: str = "", name: str = "", description: str = "", raw_id: str = "x") -> RawRecord:
    return RawRecord(
        source="test",
        record_type="okved",
        raw_id=raw_id,
        payload={"code": code, "name": name, "description": description},
    )


class TestFeatureExtractor:
    def test_identical_records_high_similarity(self) -> None:
        r = _make("62.01", "Разработка программного обеспечения", "Описание")
        fv = extract_features(r, r)
        assert fv["jaro_winkler"] > 0.95
        assert fv["code_exact_match"] == 1.0
        assert fv["token_sort_ratio"] > 0.95

    def test_different_records_low_similarity(self) -> None:
        left = _make("62.01", "Разработка программного обеспечения")
        right = _make("47.91", "Торговля розничная через интернет")
        fv = extract_features(left, right)
        assert fv["code_exact_match"] == 0.0
        assert fv["code_prefix_2_match"] == 0.0
        assert fv["jaro_winkler"] < 0.7

    def test_same_code_prefix_match(self) -> None:
        left = _make("62.01", "Разработка ПО")
        right = _make("62.09", "Деятельность в IT")
        fv = extract_features(left, right)
        assert fv["code_prefix_2_match"] == 1.0
        assert fv["code_exact_match"] == 0.0

    def test_features_to_list_length(self) -> None:
        r = _make("62.01", "Тест")
        fv = extract_features(r, r)
        lst = features_to_list(fv)
        assert len(lst) == len(FEATURE_NAMES)

    def test_all_features_in_range(self) -> None:
        left = _make("62.01", "Разработка ПО", "Описание")
        right = _make("62.01", "разраб. прогр. обеспеч.", "")
        fv = extract_features(left, right)
        for key, val in fv.items():
            assert 0.0 <= val <= 1.0, f"Feature {key} = {val} out of [0, 1]"

    def test_description_jaccard_empty(self) -> None:
        left = _make("62.01", "Тест", "")
        right = _make("62.01", "Тест", "")
        fv = extract_features(left, right)
        assert fv["description_jaccard"] == 1.0

    def test_name_length_diff_identical(self) -> None:
        r = _make("62.01", "Разработка ПО")
        fv = extract_features(r, r)
        assert fv["name_length_diff"] == 0.0
