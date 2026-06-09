from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import networkx as nx

from nsi_normalizer.ml.blocking.blocker import CompositeBlocker, blocker_for, default_blocker
from nsi_normalizer.ml.classification.dedup_classifier import DedupClassifier
from nsi_normalizer.ml.features.feature_extractor import extract_features
from nsi_normalizer.schemas.common import DeduplicationResult, NormalizedRecord, RawRecord


@dataclass
class DeduplicationReport:
    total_records: int
    candidate_pairs: int
    duplicate_pairs: int
    clusters_found: int
    results: list[DeduplicationResult] = field(default_factory=list)

    @property
    def reduction_ratio(self) -> float:
        """Fraction of pairs skipped by blocking vs brute-force O(n²)."""
        brute_force = self.total_records * (self.total_records - 1) / 2
        if brute_force == 0:
            return 0.0
        return 1.0 - self.candidate_pairs / brute_force


class DeduplicationPipeline:
    def __init__(
        self,
        blocker: CompositeBlocker | None = None,
        classifier: DedupClassifier | None = None,
        threshold: float = 0.65,
    ) -> None:
        self.blocker = blocker  # None = auto-detect by record type in run()
        self.classifier = classifier or DedupClassifier()
        self.threshold = threshold

    def run(self, records: list[RawRecord]) -> DeduplicationReport:
        if not records:
            return DeduplicationReport(0, 0, 0, 0)

        # Re-index records so every record has a unique raw_id (avoids collisions on same code)
        records = [r.model_copy(update={"raw_id": str(i)}) for i, r in enumerate(records)]
        id_to_record = {r.raw_id: r for r in records if r.raw_id}

        # Stage 1: blocking (use type-aware blocker if not explicitly set)
        active_blocker = self.blocker if self.blocker is not None else blocker_for(records)
        candidate_pairs = active_blocker.get_candidate_pairs(records)

        # Stage 2 & 3: feature extraction + classification
        graph: nx.Graph = nx.Graph()
        graph.add_nodes_from(id_to_record.keys())

        duplicate_count = 0
        for left_id, right_id in candidate_pairs:
            left = id_to_record.get(left_id)
            right = id_to_record.get(right_id)
            if left is None or right is None:
                continue
            fv = extract_features(left, right)
            is_dup, confidence = self.classifier.is_duplicate(fv, self.threshold)
            if is_dup:
                graph.add_edge(left_id, right_id, confidence=confidence)
                duplicate_count += 1

        # Stage 4: clustering via connected components
        results: list[DeduplicationResult] = []
        for component in nx.connected_components(graph):
            component_records = [id_to_record[rid] for rid in component if rid in id_to_record]
            if not component_records:
                continue

            canonical = _elect_canonical(component_records)
            avg_confidence = _average_edge_confidence(graph, component)
            cluster_id = uuid.uuid4()

            results.append(
                DeduplicationResult(
                    cluster_id=cluster_id,
                    record_ids=[uuid.uuid4() for _ in component_records],
                    canonical_record=canonical,
                    confidence=avg_confidence,
                    record_count=len(component_records),
                )
            )

        return DeduplicationReport(
            total_records=len(records),
            candidate_pairs=len(candidate_pairs),
            duplicate_pairs=duplicate_count,
            clusters_found=len(results),
            results=results,
        )


def _elect_canonical(records: list[RawRecord]) -> NormalizedRecord:
    """Choose the best record from a cluster and normalize it."""
    from nsi_normalizer.core.normalization.canonical_selector import normalize_record
    from nsi_normalizer.core.normalization.field_normalizer import normalize_name

    def score(r: RawRecord) -> int:
        raw_name = str(r.payload.get("name", ""))
        name = normalize_name(raw_name)
        desc = str(r.payload.get("description") or "")
        has_code = 1 if r.payload.get("code") else 0
        # Penalise ALL-CAPS names — prefer mixed/title case
        is_allcaps = raw_name == raw_name.upper() and raw_name.isalpha() is False and len(raw_name) > 5
        caps_penalty = -30 if is_allcaps else 0
        return len(name) + len(desc) // 2 + has_code * 20 + caps_penalty

    best = max(records, key=score)
    return normalize_record(best)


def _average_edge_confidence(graph: nx.Graph, nodes: set[str]) -> float:
    edges = [
        data.get("confidence", 0.5)
        for u, v, data in graph.edges(data=True)
        if u in nodes and v in nodes
    ]
    if not edges:
        return 1.0
    return sum(edges) / len(edges)
