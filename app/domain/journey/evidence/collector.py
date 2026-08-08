from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.journey.models import JourneyEvidence, EvidenceType


class EvidenceCollector:
    """Collects evidence from various contexts for journey progression."""

    def collect_from_intent_context(self, intent_context: Dict[str, Any]) -> List[JourneyEvidence]:
        """Extracts evidence from IntentIntelligence outputs."""
        evidence_list = []
        now = datetime.now(timezone.utc)
        
        # Detected intents
        detected_intents = intent_context.get("detected_intents", [])
        for intent in detected_intents:
            evidence_list.append(
                JourneyEvidence(
                    evidence_id=uuid.uuid4(),
                    evidence_type=EvidenceType.INTENT,
                    source_module="intent_context",
                    source_id=intent.get("id", ""),
                    metadata={"data": intent},
                    confidence=intent.get("confidence", 1.0),
                    timestamp=now
                )
            )
            
        # Classified intents
        classified_intents = intent_context.get("classified_intents", [])
        for intent in classified_intents:
            evidence_list.append(
                JourneyEvidence(
                    evidence_id=uuid.uuid4(),
                    evidence_type=EvidenceType.INTENT,
                    source_module="intent_context",
                    source_id=intent.get("id", ""),
                    metadata={"data": intent},
                    confidence=intent.get("confidence", 1.0),
                    timestamp=now
                )
            )

        # Evolution events
        evolution_events = intent_context.get("evolution_events", [])
        for event in evolution_events:
            evidence_list.append(
                JourneyEvidence(
                    evidence_id=uuid.uuid4(),
                    evidence_type=EvidenceType.INTENT_EVOLUTION,
                    source_module="intent_context",
                    source_id=event.get("id", ""),
                    metadata={"data": event},
                    confidence=1.0,
                    timestamp=now
                )
            )

        # Resolution groups
        resolution_groups = intent_context.get("resolution_groups", [])
        for group in resolution_groups:
            evidence_list.append(
                JourneyEvidence(
                    evidence_id=uuid.uuid4(),
                    evidence_type=EvidenceType.INTENT_RESOLUTION,
                    source_module="intent_context",
                    source_id=group.get("id", ""),
                    metadata={"data": group},
                    confidence=1.0,
                    timestamp=now
                )
            )

        return evidence_list

    def collect_from_conversation_context(self, conversation_context: Dict[str, Any]) -> List[JourneyEvidence]:
        """Extracts evidence from conversation analysis, timeline events, insights."""
        evidence_list = []
        now = datetime.now(timezone.utc)

        # Insights / Conversation Analysis
        insights = conversation_context.get("insights", [])
        for insight in insights:
            evidence_list.append(
                JourneyEvidence(
                    evidence_id=uuid.uuid4(),
                    evidence_type=EvidenceType.CONVERSATION,
                    source_module="conversation_context",
                    source_id=insight.get("id", ""),
                    metadata={"data": insight},
                    confidence=insight.get("confidence", 1.0),
                    timestamp=now
                )
            )

        # Timeline events
        timeline_events = conversation_context.get("timeline_events", [])
        for event in timeline_events:
            evidence_list.append(
                JourneyEvidence(
                    evidence_id=uuid.uuid4(),
                    evidence_type=EvidenceType.TIMELINE_EVENT,
                    source_module="conversation_context",
                    source_id=event.get("id", ""),
                    metadata={"data": event},
                    confidence=1.0,
                    timestamp=now
                )
            )

        return evidence_list

    def collect_from_memory_context(self, memory_context: Optional[Dict[str, Any]]) -> List[JourneyEvidence]:
        """Creates MEMORY_CONTEXT evidence."""
        if not memory_context:
            return []

        now = datetime.now(timezone.utc)
        memory_items = memory_context.get("items", [])
        evidence_list = []
        
        for item in memory_items:
            evidence_list.append(
                JourneyEvidence(
                    evidence_id=uuid.uuid4(),
                    evidence_type=EvidenceType.MEMORY_CONTEXT,
                    source_module="memory_context",
                    source_id=item.get("id", ""),
                    metadata={"data": item},
                    confidence=item.get("confidence", 1.0),
                    timestamp=now
                )
            )
            
        return evidence_list

    def collect_all(
        self,
        intent_context: Dict[str, Any],
        conversation_context: Dict[str, Any],
        memory_context: Optional[Dict[str, Any]] = None
    ) -> List[JourneyEvidence]:
        """Combines all evidence from different contexts."""
        all_evidence = []
        all_evidence.extend(self.collect_from_intent_context(intent_context))
        all_evidence.extend(self.collect_from_conversation_context(conversation_context))
        all_evidence.extend(self.collect_from_memory_context(memory_context))
        
        return all_evidence
