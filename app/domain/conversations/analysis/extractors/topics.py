"""
HunterOS Engage — Topic Extractors (Phase 2.2.1)

Implements deterministic topic extraction utilizing the TopicTaxonomy hierarchy.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.domain.conversations.analysis.extractors.base import AbstractTopicExtractor
from app.domain.conversations.analysis.models import (
    ArtifactProvenance,
    ExtractionMethod,
    NormalizedMessage,
    SourceMessageRef,
    TopicAnalysis,
    TopicDistribution,
    TopicTimelineItem,
)
from app.domain.conversations.analysis.taxonomy import (
    TopicTaxonomy,
    TopicTaxonomyNode,
    default_topic_taxonomy,
)


class TaxonomyTopicExtractor(AbstractTopicExtractor):
    """
    Extracts structured topic hierarchies, frequency distributions,
    and progression timelines from conversation messages.
    """

    def __init__(self, taxonomy: Optional[TopicTaxonomy] = None) -> None:
        self._taxonomy = taxonomy or default_topic_taxonomy

    def extract_topics(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> TopicAnalysis:
        if not messages:
            return TopicAnalysis(
                primary_topic="General Discussion",
                primary_taxonomy_path="general",
                provenance=ArtifactProvenance(
                    pipeline_stage="TopicStage",
                    confidence=1.0,
                    extraction_method=ExtractionMethod.HEURISTIC,
                ),
            )

        # 1. Evaluate per-message matches to build timeline and distributions
        topic_counts: Dict[str, int] = {}
        topic_nodes: Dict[str, TopicTaxonomyNode] = {}
        topic_first_seen: Dict[str, Any] = {}
        topic_last_seen: Dict[str, Any] = {}
        topic_source_refs: Dict[str, List[SourceMessageRef]] = {}
        timeline: List[TopicTimelineItem] = []

        total_messages = len(messages)

        for idx, msg in enumerate(messages):
            position_frac = (idx + 1) / total_messages
            matched = self._taxonomy.match_all(msg.cleaned_content)
            
            for node, count, conf in matched:
                path = node.path
                topic_nodes[path] = node
                topic_counts[path] = topic_counts.get(path, 0) + count

                if path not in topic_first_seen:
                    topic_first_seen[path] = msg.timestamp
                topic_last_seen[path] = msg.timestamp

                ref = SourceMessageRef(
                    message_id=msg.id,
                    timestamp=msg.timestamp,
                    text_snippet=msg.cleaned_content[:80],
                )
                if path not in topic_source_refs:
                    topic_source_refs[path] = []
                topic_source_refs[path].append(ref)

                timeline.append(
                    TopicTimelineItem(
                        topic_name=node.name,
                        taxonomy_path=node.path,
                        message_id=msg.id,
                        timestamp=msg.timestamp,
                        position_fraction=round(position_frac, 3),
                    )
                )

        if not topic_counts:
            # Fallback when no specific keywords match
            return TopicAnalysis(
                primary_topic="General Discussion",
                primary_taxonomy_path="general/discussion",
                provenance=ArtifactProvenance(
                    pipeline_stage="TopicStage",
                    confidence=0.75,
                    extraction_method=ExtractionMethod.HEURISTIC,
                ),
            )

        # 2. Build distributions
        distributions: List[TopicDistribution] = []
        total_occurrences = sum(topic_counts.values())

        for path, count in topic_counts.items():
            node = topic_nodes[path]
            weight = round(count / max(1, total_occurrences), 3)
            # Higher depth nodes get small boost for specificity
            depth_factor = len(path.split("/")) * 0.05
            conf = min(1.0, 0.7 + depth_factor + (min(count, 5) * 0.05))

            dist = TopicDistribution(
                topic_name=node.name,
                taxonomy_path=path,
                category=node.category,
                frequency=count,
                weight=weight,
                first_mentioned_at=topic_first_seen.get(path),
                last_mentioned_at=topic_last_seen.get(path),
                provenance=ArtifactProvenance(
                    pipeline_stage="TopicStage",
                    confidence=round(conf, 2),
                    source_messages=topic_source_refs.get(path, [])[:5],
                    extraction_method=ExtractionMethod.RULE_BASED,
                ),
            )
            distributions.append(dist)

        # Sort distributions by frequency descending, then path depth
        distributions.sort(key=lambda d: (d.frequency, len(d.taxonomy_path.split("/"))), reverse=True)

        primary_dist = distributions[0]
        secondary_topics = [d.topic_name for d in distributions[1:5]]

        all_sources = []
        for refs in topic_source_refs.values():
            all_sources.extend(refs)

        return TopicAnalysis(
            primary_topic=primary_dist.topic_name,
            primary_taxonomy_path=primary_dist.taxonomy_path,
            secondary_topics=secondary_topics,
            distribution=distributions,
            timeline=timeline,
            provenance=ArtifactProvenance(
                pipeline_stage="TopicStage",
                confidence=primary_dist.provenance.confidence,
                source_messages=all_sources[:10],
                extraction_method=ExtractionMethod.RULE_BASED,
            ),
        )
