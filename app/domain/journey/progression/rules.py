"""
HunterOS Engage V1 — Stage Progression Rules
Phase 2.4.2: Stage Progression Engine

Abstract rule framework and cross-industry progression rules.
Rules are deterministic — they observe evidence and propose
transition candidates. They NEVER predict or recommend.
"""

from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from app.domain.journey.context import JourneyProgressionContext
from app.domain.journey.models import (
    ConfidenceFactors,
    EvidenceType,
    JourneyEvidence,
    JourneyStageCode,
    JourneyType,
    TransitionCandidate,
    TransitionType,
)


# ── Abstract Rule ────────────────────────────────────────────────────────────────


class AbstractStageProgressionRule(abc.ABC):
    """
    Base class for all stage progression rules.
    Rules evaluate context and produce transition candidates.

    Rules are deterministic: same inputs → same outputs.
    Rules describe observed state, never predict future state.
    """

    @property
    @abc.abstractmethod
    def rule_name(self) -> str:
        """Unique rule identifier."""
        ...

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    @abc.abstractmethod
    def supported_journey_types(self) -> List[JourneyType]:
        """Journey types this rule applies to."""
        ...

    @property
    @abc.abstractmethod
    def supported_stages(self) -> List[JourneyStageCode]:
        """Current stages from which this rule can fire."""
        ...

    @abc.abstractmethod
    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        """
        Evaluate the context and return a transition candidate if evidence supports it.
        Returns None if no transition is warranted.
        """
        ...

    def _has_intent(self, context: JourneyProgressionContext, intent_type: str) -> bool:
        """Check if intent context contains a specific intent type."""
        if not context.intent_context:
            return False
        intents = context.intent_context.get("detected_intents", [])
        if isinstance(intents, list):
            for intent in intents:
                if isinstance(intent, dict):
                    it = intent.get("intent_type", "")
                    if it == intent_type or it.upper() == intent_type.upper():
                        return True
                elif hasattr(intent, "intent_type"):
                    it = getattr(intent, "intent_type", "")
                    val = it.value if hasattr(it, "value") else str(it)
                    if val.upper() == intent_type.upper():
                        return True
        return False

    def _get_intent_confidence(self, context: JourneyProgressionContext, intent_type: str) -> float:
        """Get confidence for a specific intent type."""
        if not context.intent_context:
            return 0.0
        intents = context.intent_context.get("detected_intents", [])
        if isinstance(intents, list):
            for intent in intents:
                if isinstance(intent, dict):
                    it = intent.get("intent_type", "")
                    if it.upper() == intent_type.upper():
                        return float(intent.get("confidence", 0.0))
                elif hasattr(intent, "intent_type"):
                    it = getattr(intent, "intent_type", "")
                    val = it.value if hasattr(it, "value") else str(it)
                    if val.upper() == intent_type.upper():
                        return float(getattr(intent, "confidence", 0.0))
        return 0.0

    def _has_timeline_event(self, context: JourneyProgressionContext, event_type: str) -> bool:
        """Check if conversation context contains a timeline event."""
        if not context.conversation_context:
            return False
        events = context.conversation_context.get("timeline_events", [])
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    if event.get("event_type", "").upper() == event_type.upper():
                        return True
                elif hasattr(event, "event_type"):
                    et = getattr(event, "event_type", "")
                    val = et.value if hasattr(et, "value") else str(et)
                    if val.upper() == event_type.upper():
                        return True
        return False

    def _has_topic(self, context: JourneyProgressionContext, topic: str) -> bool:
        """Check if conversation context contains a specific topic."""
        if not context.conversation_context:
            return False
        topics = context.conversation_context.get("topics", [])
        if isinstance(topics, list):
            for t in topics:
                if isinstance(t, str) and topic.lower() in t.lower():
                    return True
                elif isinstance(t, dict) and topic.lower() in t.get("name", "").lower():
                    return True
        return False

    def _count_evidence_for_types(self, context: JourneyProgressionContext, types: List[EvidenceType]) -> int:
        """Count pre-collected evidence items matching given types."""
        return sum(1 for e in context.evidence if e.evidence_type in types)

    def _build_evidence(
        self,
        description: str,
        evidence_type: EvidenceType = EvidenceType.SYSTEM,
        source_module: str = "",
        confidence: float = 0.0,
    ) -> JourneyEvidence:
        """Helper to create evidence items."""
        return JourneyEvidence(
            evidence_id=uuid.uuid4(),
            evidence_type=evidence_type,
            source_module=source_module or self.rule_name,
            timestamp=datetime.now(timezone.utc),
            description=description,
            confidence=confidence,
        )


# ── Cross-Industry Rules ─────────────────────────────────────────────────────────


ALL_STANDARD_JOURNEY_TYPES = [
    JourneyType.SALES, JourneyType.PROPERTY_PURCHASE,
    JourneyType.PROPERTY_RENTAL, JourneyType.SERVICE,
    JourneyType.SUPPORT, JourneyType.PARTNERSHIP, JourneyType.CUSTOM,
]


class NewLeadRule(AbstractStageProgressionRule):
    """Initializes a journey at the NEW_LEAD stage."""

    @property
    def rule_name(self) -> str:
        return "NewLeadRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return []  # Fires on initialization (no current stage)

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if context.journey_state is not None and context.journey_state.current_stage != JourneyStageCode.NEW_LEAD:
            return None
        # This rule fires only during initialization
        if context.journey_state is not None and len(context.journey_state.stage_history) > 0:
            return None
        evidence = [self._build_evidence(
            "Journey initialized for new entity",
            EvidenceType.SYSTEM,
            confidence=1.0,
        )]
        return TransitionCandidate(
            from_stage=JourneyStageCode.NEW_LEAD,
            to_stage=JourneyStageCode.NEW_LEAD,
            transition_type=TransitionType.INITIALIZATION,
            evidence=evidence,
            confidence=1.0,
            confidence_factors=ConfidenceFactors(rule_strength=1.0),
            rule_name=self.rule_name,
            reason="New entity journey initialization",
            source_modules=["journey.progression"],
        )


class EngagementRule(AbstractStageProgressionRule):
    """Detects transition to INTERESTED based on engagement signals."""

    @property
    def rule_name(self) -> str:
        return "EngagementRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.NEW_LEAD]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state or context.journey_state.current_stage != JourneyStageCode.NEW_LEAD:
            return None

        evidence_items: List[JourneyEvidence] = []
        intent_conf = 0.0
        conv_conf = 0.0

        # Check for inquiry-type intents
        inquiry_intents = [
            "PROPERTY_INQUIRY", "PRODUCT_INQUIRY", "PRICING_INQUIRY",
            "INFORMATION_REQUEST", "GENERAL_INQUIRY", "COMMERCIAL_INQUIRY",
        ]
        for it in inquiry_intents:
            if self._has_intent(context, it):
                conf = self._get_intent_confidence(context, it)
                intent_conf = max(intent_conf, conf)
                evidence_items.append(self._build_evidence(
                    f"Detected {it} intent",
                    EvidenceType.INTENT,
                    confidence=conf,
                ))

        # Check conversation engagement
        if context.conversation_context:
            topics = context.conversation_context.get("topics", [])
            if topics:
                conv_conf = 0.7
                evidence_items.append(self._build_evidence(
                    f"Active conversation with {len(topics)} topic(s)",
                    EvidenceType.CONVERSATION,
                    confidence=conv_conf,
                ))

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            intent_match=intent_conf,
            conversation_match=conv_conf,
            rule_strength=0.80,
            evidence_count_factor=min(1.0, len(evidence_items) / 3.0),
        )
        return TransitionCandidate(
            from_stage=JourneyStageCode.NEW_LEAD,
            to_stage=JourneyStageCode.INTERESTED,
            transition_type=TransitionType.ADVANCE,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Customer engagement signals detected via intents and conversation",
            source_modules=["journey.progression", "intent_intelligence", "conversation_intelligence"],
        )


class QualificationRule(AbstractStageProgressionRule):
    """Detects qualification based on commercial intent signals."""

    @property
    def rule_name(self) -> str:
        return "QualificationRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.INTERESTED, JourneyStageCode.ENGAGED]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state:
            return None
        current = context.journey_state.current_stage
        if current not in self.supported_stages:
            return None

        evidence_items: List[JourneyEvidence] = []
        intent_conf = 0.0

        commercial_intents = [
            "BUDGET_DISCUSSION", "BUDGET_CONFIRMED", "BUDGET_DISCUSSED",
            "PRICING_INQUIRY", "BOOKING_INTEREST",
            "INVESTMENT_INQUIRY", "FINANCE_INQUIRY", "QUALIFICATION_CONFIRMED",
        ]
        for it in commercial_intents:
            if self._has_intent(context, it):
                conf = self._get_intent_confidence(context, it)
                intent_conf = max(intent_conf, conf)
                evidence_items.append(self._build_evidence(
                    f"Commercial intent detected: {it}",
                    EvidenceType.INTENT,
                    confidence=conf,
                ))

        if self._has_topic(context, "budget") or self._has_topic(context, "pricing"):
            evidence_items.append(self._build_evidence(
                "Budget/pricing discussion in conversation",
                EvidenceType.CONVERSATION,
                confidence=0.75,
            ))

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            intent_match=intent_conf,
            conversation_match=0.75 if len(evidence_items) > 1 else 0.0,
            rule_strength=0.85,
            evidence_count_factor=min(1.0, len(evidence_items) / 3.0),
        )
        return TransitionCandidate(
            from_stage=current,
            to_stage=JourneyStageCode.QUALIFIED,
            transition_type=TransitionType.ADVANCE,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Commercial qualification signals observed",
            source_modules=["journey.progression", "intent_intelligence"],
        )


class MeetingScheduledRule(AbstractStageProgressionRule):
    """Detects meeting/appointment scheduling."""

    @property
    def rule_name(self) -> str:
        return "MeetingScheduledRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.QUALIFIED, JourneyStageCode.INTERESTED, JourneyStageCode.ENGAGED]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state:
            return None
        current = context.journey_state.current_stage
        if current not in self.supported_stages:
            return None

        evidence_items: List[JourneyEvidence] = []
        intent_conf = 0.0

        if self._has_intent(context, "SCHEDULE_MEETING"):
            intent_conf = self._get_intent_confidence(context, "SCHEDULE_MEETING")
            evidence_items.append(self._build_evidence(
                "Meeting scheduling intent detected",
                EvidenceType.INTENT,
                confidence=intent_conf,
            ))

        if self._has_timeline_event(context, "MEETING_SCHEDULED"):
            evidence_items.append(self._build_evidence(
                "Meeting scheduled timeline event",
                EvidenceType.TIMELINE_EVENT,
                confidence=0.90,
            ))

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            intent_match=intent_conf,
            timeline_match=0.90 if len(evidence_items) > 1 else 0.0,
            rule_strength=0.90,
            evidence_count_factor=min(1.0, len(evidence_items) / 2.0),
        )
        return TransitionCandidate(
            from_stage=current,
            to_stage=JourneyStageCode.MEETING_SCHEDULED,
            transition_type=TransitionType.ADVANCE,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Meeting scheduling evidence observed",
            source_modules=["journey.progression", "intent_intelligence"],
        )


class MeetingCompletedRule(AbstractStageProgressionRule):
    """Detects meeting completion."""

    @property
    def rule_name(self) -> str:
        return "MeetingCompletedRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.MEETING_SCHEDULED]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state:
            return None
        if context.journey_state.current_stage != JourneyStageCode.MEETING_SCHEDULED:
            return None

        evidence_items: List[JourneyEvidence] = []

        if self._has_timeline_event(context, "MEETING_COMPLETED"):
            evidence_items.append(self._build_evidence(
                "Meeting completed timeline event",
                EvidenceType.TIMELINE_EVENT,
                confidence=0.95,
            ))

        if self._has_topic(context, "meeting") or self._has_topic(context, "discussed"):
            evidence_items.append(self._build_evidence(
                "Post-meeting discussion detected in conversation",
                EvidenceType.CONVERSATION,
                confidence=0.70,
            ))

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            timeline_match=0.95 if self._has_timeline_event(context, "MEETING_COMPLETED") else 0.0,
            conversation_match=0.70 if len(evidence_items) > 1 else 0.0,
            rule_strength=0.90,
            evidence_count_factor=min(1.0, len(evidence_items) / 2.0),
        )
        return TransitionCandidate(
            from_stage=JourneyStageCode.MEETING_SCHEDULED,
            to_stage=JourneyStageCode.MEETING_COMPLETED,
            transition_type=TransitionType.ADVANCE,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Meeting completion evidence observed",
            source_modules=["journey.progression"],
        )


class ProposalRule(AbstractStageProgressionRule):
    """Detects transition to proposal stage."""

    @property
    def rule_name(self) -> str:
        return "ProposalRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.MEETING_COMPLETED, JourneyStageCode.QUALIFIED]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state:
            return None
        current = context.journey_state.current_stage
        if current not in self.supported_stages:
            return None

        evidence_items: List[JourneyEvidence] = []
        intent_conf = 0.0

        if self._has_intent(context, "PROPOSAL_REQUEST"):
            intent_conf = self._get_intent_confidence(context, "PROPOSAL_REQUEST")
            evidence_items.append(self._build_evidence(
                "Proposal request intent detected",
                EvidenceType.INTENT,
                confidence=intent_conf,
            ))

        if self._has_topic(context, "proposal") or self._has_topic(context, "quotation"):
            evidence_items.append(self._build_evidence(
                "Proposal/quotation discussion in conversation",
                EvidenceType.CONVERSATION,
                confidence=0.75,
            ))

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            intent_match=intent_conf,
            conversation_match=0.75 if self._has_topic(context, "proposal") else 0.0,
            rule_strength=0.85,
            evidence_count_factor=min(1.0, len(evidence_items) / 2.0),
        )
        return TransitionCandidate(
            from_stage=current,
            to_stage=JourneyStageCode.PROPOSAL,
            transition_type=TransitionType.ADVANCE,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Proposal-related evidence observed",
            source_modules=["journey.progression", "intent_intelligence"],
        )


class NegotiationRule(AbstractStageProgressionRule):
    """Detects transition to negotiation stage."""

    @property
    def rule_name(self) -> str:
        return "NegotiationRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [
            JourneyStageCode.PROPOSAL,
            JourneyStageCode.MEETING_COMPLETED,
            JourneyStageCode.QUALIFIED,
            JourneyStageCode.SITE_VISIT_COMPLETED,
            JourneyStageCode.PROPERTY_SHORTLISTED,
        ]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state:
            return None
        current = context.journey_state.current_stage
        if current not in self.supported_stages:
            return None

        evidence_items: List[JourneyEvidence] = []
        intent_conf = 0.0

        if self._has_intent(context, "NEGOTIATION"):
            intent_conf = self._get_intent_confidence(context, "NEGOTIATION")
            evidence_items.append(self._build_evidence(
                "Negotiation intent detected",
                EvidenceType.INTENT,
                confidence=intent_conf,
            ))

        pricing_topics = ["pricing", "discount", "negotiat", "counter-offer", "bargain"]
        for topic in pricing_topics:
            if self._has_topic(context, topic):
                evidence_items.append(self._build_evidence(
                    f"Negotiation-related topic detected: {topic}",
                    EvidenceType.CONVERSATION,
                    confidence=0.80,
                ))
                break

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            intent_match=intent_conf,
            conversation_match=0.80 if len(evidence_items) > 1 else 0.0,
            rule_strength=0.90,
            evidence_count_factor=min(1.0, len(evidence_items) / 2.0),
        )
        return TransitionCandidate(
            from_stage=current,
            to_stage=JourneyStageCode.NEGOTIATION,
            transition_type=TransitionType.ADVANCE,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Negotiation evidence observed: pricing/discount discussions",
            source_modules=["journey.progression", "intent_intelligence", "conversation_intelligence"],
        )


class BookingRule(AbstractStageProgressionRule):
    """Detects transition to booking stage."""

    @property
    def rule_name(self) -> str:
        return "BookingRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.NEGOTIATION, JourneyStageCode.PROPOSAL]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state:
            return None
        current = context.journey_state.current_stage
        if current not in self.supported_stages:
            return None

        evidence_items: List[JourneyEvidence] = []
        intent_conf = 0.0

        if self._has_intent(context, "BOOKING_INTEREST"):
            intent_conf = self._get_intent_confidence(context, "BOOKING_INTEREST")
            evidence_items.append(self._build_evidence(
                "Booking interest intent detected",
                EvidenceType.INTENT,
                confidence=intent_conf,
            ))

        booking_topics = ["booking", "reserve", "payment", "deposit", "contract"]
        for topic in booking_topics:
            if self._has_topic(context, topic):
                evidence_items.append(self._build_evidence(
                    f"Booking-related topic detected: {topic}",
                    EvidenceType.CONVERSATION,
                    confidence=0.85,
                ))
                break

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            intent_match=intent_conf,
            conversation_match=0.85 if len(evidence_items) > 1 else 0.0,
            rule_strength=0.90,
            evidence_count_factor=min(1.0, len(evidence_items) / 2.0),
        )
        return TransitionCandidate(
            from_stage=current,
            to_stage=JourneyStageCode.BOOKING,
            transition_type=TransitionType.ADVANCE,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Booking evidence observed",
            source_modules=["journey.progression", "intent_intelligence"],
        )


class CompletionRule(AbstractStageProgressionRule):
    """Detects journey completion (CLOSED_WON)."""

    @property
    def rule_name(self) -> str:
        return "CompletionRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.BOOKING, JourneyStageCode.NEGOTIATION]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state:
            return None
        current = context.journey_state.current_stage
        if current not in self.supported_stages:
            return None

        evidence_items: List[JourneyEvidence] = []

        if self._has_timeline_event(context, "DEAL_CLOSED") or self._has_timeline_event(context, "BOOKING_CONFIRMED"):
            evidence_items.append(self._build_evidence(
                "Deal closure / booking confirmation event",
                EvidenceType.TIMELINE_EVENT,
                confidence=0.95,
            ))

        completion_topics = ["confirmed", "completed", "done", "closed", "finalized"]
        for topic in completion_topics:
            if self._has_topic(context, topic):
                evidence_items.append(self._build_evidence(
                    f"Completion topic detected: {topic}",
                    EvidenceType.CONVERSATION,
                    confidence=0.80,
                ))
                break

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            timeline_match=0.95 if evidence_items else 0.0,
            conversation_match=0.80 if len(evidence_items) > 1 else 0.0,
            rule_strength=0.95,
            evidence_count_factor=min(1.0, len(evidence_items) / 2.0),
        )
        return TransitionCandidate(
            from_stage=current,
            to_stage=JourneyStageCode.CLOSED_WON,
            transition_type=TransitionType.COMPLETION,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Journey completion evidence observed",
            source_modules=["journey.progression"],
        )


class CancellationRule(AbstractStageProgressionRule):
    """Detects cancellation or loss (CLOSED_LOST)."""

    @property
    def rule_name(self) -> str:
        return "CancellationRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [
            JourneyStageCode.INTERESTED, JourneyStageCode.QUALIFIED,
            JourneyStageCode.ENGAGED, JourneyStageCode.MEETING_SCHEDULED,
            JourneyStageCode.MEETING_COMPLETED, JourneyStageCode.PROPOSAL,
            JourneyStageCode.NEGOTIATION, JourneyStageCode.BOOKING,
            JourneyStageCode.SITE_VISIT_SCHEDULED, JourneyStageCode.SITE_VISIT_COMPLETED,
            JourneyStageCode.PROPERTY_SHORTLISTED,
        ]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state:
            return None
        current = context.journey_state.current_stage
        if current not in self.supported_stages:
            return None

        evidence_items: List[JourneyEvidence] = []
        intent_conf = 0.0

        if self._has_intent(context, "CANCELLATION"):
            intent_conf = self._get_intent_confidence(context, "CANCELLATION")
            evidence_items.append(self._build_evidence(
                "Cancellation intent detected",
                EvidenceType.INTENT,
                confidence=intent_conf,
            ))

        cancel_topics = ["cancel", "not interested", "withdraw", "reject"]
        for topic in cancel_topics:
            if self._has_topic(context, topic):
                evidence_items.append(self._build_evidence(
                    f"Cancellation topic detected: {topic}",
                    EvidenceType.CONVERSATION,
                    confidence=0.80,
                ))
                break

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            intent_match=intent_conf,
            conversation_match=0.80 if len(evidence_items) > 1 else 0.0,
            rule_strength=0.90,
            evidence_count_factor=min(1.0, len(evidence_items) / 2.0),
        )
        return TransitionCandidate(
            from_stage=current,
            to_stage=JourneyStageCode.CLOSED_LOST,
            transition_type=TransitionType.CLOSURE,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Cancellation/loss evidence observed",
            source_modules=["journey.progression", "intent_intelligence"],
        )


class InactivityRule(AbstractStageProgressionRule):
    """Detects transition to INACTIVE due to prolonged inactivity."""

    @property
    def rule_name(self) -> str:
        return "InactivityRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [
            JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED,
            JourneyStageCode.QUALIFIED, JourneyStageCode.ENGAGED,
            JourneyStageCode.MEETING_SCHEDULED, JourneyStageCode.PROPOSAL,
            JourneyStageCode.NEGOTIATION,
        ]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state:
            return None
        current = context.journey_state.current_stage
        if current not in self.supported_stages:
            return None

        # Check for explicit inactivity signals
        evidence_items: List[JourneyEvidence] = []

        # Check if evidence explicitly signals inactivity
        for ev in context.evidence:
            if "inactive" in ev.description.lower() or "no response" in ev.description.lower():
                evidence_items.append(ev)

        if self._has_timeline_event(context, "INACTIVITY_DETECTED"):
            evidence_items.append(self._build_evidence(
                "Inactivity detected via timeline event",
                EvidenceType.TIMELINE_EVENT,
                confidence=0.85,
            ))

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            timeline_match=0.85,
            rule_strength=0.80,
            evidence_count_factor=min(1.0, len(evidence_items) / 2.0),
        )
        return TransitionCandidate(
            from_stage=current,
            to_stage=JourneyStageCode.INACTIVE,
            transition_type=TransitionType.CLOSURE,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Inactivity evidence observed",
            source_modules=["journey.progression"],
        )


class ReactivationRule(AbstractStageProgressionRule):
    """Detects reactivation from INACTIVE or CLOSED_LOST."""

    @property
    def rule_name(self) -> str:
        return "ReactivationRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return ALL_STANDARD_JOURNEY_TYPES

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.INACTIVE, JourneyStageCode.CLOSED_LOST]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        if not context.journey_state:
            return None
        current = context.journey_state.current_stage
        if current not in self.supported_stages:
            return None

        evidence_items: List[JourneyEvidence] = []
        intent_conf = 0.0

        # Any new intent indicates reactivation
        if context.intent_context:
            intents = context.intent_context.get("detected_intents", [])
            if intents:
                intent_conf = 0.75
                evidence_items.append(self._build_evidence(
                    f"New intent activity detected from inactive/lost state ({len(intents)} intent(s))",
                    EvidenceType.INTENT,
                    confidence=intent_conf,
                ))

        # New conversation activity
        if context.conversation_context:
            topics = context.conversation_context.get("topics", [])
            if topics:
                evidence_items.append(self._build_evidence(
                    "New conversation activity from inactive/lost customer",
                    EvidenceType.CONVERSATION,
                    confidence=0.70,
                ))

        if not evidence_items:
            return None

        factors = ConfidenceFactors(
            intent_match=intent_conf,
            conversation_match=0.70 if len(evidence_items) > 1 else 0.0,
            rule_strength=0.80,
            evidence_count_factor=min(1.0, len(evidence_items) / 2.0),
        )
        return TransitionCandidate(
            from_stage=current,
            to_stage=JourneyStageCode.INTERESTED,
            transition_type=TransitionType.REACTIVATION,
            evidence=evidence_items,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Reactivation evidence observed: renewed customer engagement",
            source_modules=["journey.progression", "intent_intelligence"],
        )


class CustomStageRule(AbstractStageProgressionRule):
    """Handles custom stage transitions based on explicit evidence."""

    @property
    def rule_name(self) -> str:
        return "CustomStageRule"

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return [JourneyType.CUSTOM]

    @property
    def supported_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.CUSTOM]

    def evaluate(self, context: JourneyProgressionContext) -> Optional[TransitionCandidate]:
        # Custom rules require explicit manual evidence
        manual_evidence = [e for e in context.evidence if e.evidence_type == EvidenceType.MANUAL]
        if not manual_evidence:
            return None

        factors = ConfidenceFactors(
            rule_strength=0.70,
            evidence_count_factor=min(1.0, len(manual_evidence) / 2.0),
        )
        return TransitionCandidate(
            from_stage=context.journey_state.current_stage if context.journey_state else JourneyStageCode.CUSTOM,
            to_stage=JourneyStageCode.CUSTOM,
            transition_type=TransitionType.CUSTOM,
            evidence=manual_evidence,
            confidence=factors.compute_aggregate(),
            confidence_factors=factors,
            rule_name=self.rule_name,
            reason="Custom transition based on manual evidence",
            source_modules=["journey.progression"],
        )


# ── Default Cross-Industry Rules ─────────────────────────────────────────────────

DEFAULT_CROSS_INDUSTRY_RULES: List[AbstractStageProgressionRule] = [
    NewLeadRule(),
    EngagementRule(),
    QualificationRule(),
    MeetingScheduledRule(),
    MeetingCompletedRule(),
    ProposalRule(),
    NegotiationRule(),
    BookingRule(),
    CompletionRule(),
    CancellationRule(),
    InactivityRule(),
    ReactivationRule(),
    CustomStageRule(),
]
