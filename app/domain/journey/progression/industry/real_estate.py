"""
Real Estate industry stage progression rules.
"""
from __future__ import annotations
from typing import List

from app.domain.journey.models import (
    JourneyType, 
    JourneyStageCode, 
    TransitionType, 
    EvidenceType,
    TimelineEventType, 
    ConfidenceFactors, 
    TransitionCandidate
)
from app.domain.journey.progression.rules import AbstractStageProgressionRule

class PropertyInterestRule(AbstractStageProgressionRule):
    """Rule to transition from NEW_LEAD to INTERESTED in Real Estate."""

    @property
    def source_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.NEW_LEAD]

    @property
    def target_stage(self) -> JourneyStageCode:
        return JourneyStageCode.INTERESTED

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return [JourneyType.PROPERTY_PURCHASE, JourneyType.PROPERTY_RENTAL]

    @property
    def rule_id(self) -> str:
        return "real_estate.property_interest"

    def evaluate(self) -> TransitionCandidate | None:
        if self._has_intent("PROPERTY_INQUIRY") or self._has_intent("PRODUCT_INQUIRY"):
            intent = "PROPERTY_INQUIRY" if self._has_intent("PROPERTY_INQUIRY") else "PRODUCT_INQUIRY"
            conf = self._get_intent_confidence(intent)
            evidence = self._build_evidence(
                evidence_type=EvidenceType.INTENT_DETECTED,
                description=f"Detected {intent} intent.",
                confidence=conf,
                source="intent_engine",
                metadata={"intent": intent}
            )
            factors = ConfidenceFactors(
                intent_confidence=conf,
                behavioral_confidence=0.0,
                timeline_confidence=0.0,
                aggregate_score=conf
            )
            return TransitionCandidate(
                target_stage=self.target_stage,
                transition_type=TransitionType.PROGRESSION,
                confidence_factors=factors,
                evidence=[evidence],
                rule_id=self.rule_id
            )
        return None

class SiteVisitScheduledRule(AbstractStageProgressionRule):
    """Rule to transition to SITE_VISIT_SCHEDULED."""

    @property
    def source_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.QUALIFIED, JourneyStageCode.INTERESTED]

    @property
    def target_stage(self) -> JourneyStageCode:
        return JourneyStageCode.SITE_VISIT_SCHEDULED

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return [JourneyType.PROPERTY_PURCHASE, JourneyType.PROPERTY_RENTAL]

    @property
    def rule_id(self) -> str:
        return "real_estate.site_visit_scheduled"

    def evaluate(self) -> TransitionCandidate | None:
        if self._has_intent("SCHEDULE_SITE_VISIT"):
            conf = self._get_intent_confidence("SCHEDULE_SITE_VISIT")
            evidence = self._build_evidence(
                evidence_type=EvidenceType.INTENT_DETECTED,
                description="Detected SCHEDULE_SITE_VISIT intent.",
                confidence=conf,
                source="intent_engine",
                metadata={"intent": "SCHEDULE_SITE_VISIT"}
            )
            factors = ConfidenceFactors(
                intent_confidence=conf,
                behavioral_confidence=0.0,
                timeline_confidence=0.0,
                aggregate_score=conf
            )
            return TransitionCandidate(
                target_stage=self.target_stage,
                transition_type=TransitionType.PROGRESSION,
                confidence_factors=factors,
                evidence=[evidence],
                rule_id=self.rule_id
            )
        elif self._has_timeline_event(TimelineEventType.SITE_VISIT_SCHEDULED):
            evidence = self._build_evidence(
                evidence_type=EvidenceType.TIMELINE_EVENT,
                description="Timeline event SITE_VISIT_SCHEDULED found.",
                confidence=1.0,
                source="timeline",
                metadata={"event_type": TimelineEventType.SITE_VISIT_SCHEDULED.value}
            )
            factors = ConfidenceFactors(
                intent_confidence=0.0,
                behavioral_confidence=0.0,
                timeline_confidence=1.0,
                aggregate_score=1.0
            )
            return TransitionCandidate(
                target_stage=self.target_stage,
                transition_type=TransitionType.PROGRESSION,
                confidence_factors=factors,
                evidence=[evidence],
                rule_id=self.rule_id
            )
        return None

class SiteVisitCompletedRule(AbstractStageProgressionRule):
    """Rule to transition to SITE_VISIT_COMPLETED."""

    @property
    def source_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.SITE_VISIT_SCHEDULED]

    @property
    def target_stage(self) -> JourneyStageCode:
        return JourneyStageCode.SITE_VISIT_COMPLETED

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return [JourneyType.PROPERTY_PURCHASE, JourneyType.PROPERTY_RENTAL]

    @property
    def rule_id(self) -> str:
        return "real_estate.site_visit_completed"

    def evaluate(self) -> TransitionCandidate | None:
        if self._has_timeline_event(TimelineEventType.SITE_VISIT_COMPLETED):
            evidence = self._build_evidence(
                evidence_type=EvidenceType.TIMELINE_EVENT,
                description="Timeline event SITE_VISIT_COMPLETED found.",
                confidence=1.0,
                source="timeline",
                metadata={"event_type": TimelineEventType.SITE_VISIT_COMPLETED.value}
            )
            factors = ConfidenceFactors(
                intent_confidence=0.0,
                behavioral_confidence=0.0,
                timeline_confidence=1.0,
                aggregate_score=1.0
            )
            return TransitionCandidate(
                target_stage=self.target_stage,
                transition_type=TransitionType.PROGRESSION,
                confidence_factors=factors,
                evidence=[evidence],
                rule_id=self.rule_id
            )
        elif self._has_topic("post_visit"):
            evidence = self._build_evidence(
                evidence_type=EvidenceType.CONVERSATION_TOPIC,
                description="Found post-visit conversation topic.",
                confidence=0.7,
                source="conversation_analysis",
                metadata={"topic": "post_visit"}
            )
            factors = ConfidenceFactors(
                intent_confidence=0.0,
                behavioral_confidence=0.7,
                timeline_confidence=0.0,
                aggregate_score=0.7
            )
            return TransitionCandidate(
                target_stage=self.target_stage,
                transition_type=TransitionType.PROGRESSION,
                confidence_factors=factors,
                evidence=[evidence],
                rule_id=self.rule_id
            )
        return None

class PropertyShortlistedRule(AbstractStageProgressionRule):
    """Rule to transition to PROPERTY_SHORTLISTED."""

    @property
    def source_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.SITE_VISIT_COMPLETED]

    @property
    def target_stage(self) -> JourneyStageCode:
        return JourneyStageCode.PROPERTY_SHORTLISTED

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return [JourneyType.PROPERTY_PURCHASE, JourneyType.PROPERTY_RENTAL]

    @property
    def rule_id(self) -> str:
        return "real_estate.property_shortlisted"

    def evaluate(self) -> TransitionCandidate | None:
        if self._has_topic("property_comparison") or self._has_topic("shortlist"):
            topic = "property_comparison" if self._has_topic("property_comparison") else "shortlist"
            evidence = self._build_evidence(
                evidence_type=EvidenceType.CONVERSATION_TOPIC,
                description=f"Found {topic} conversation topic.",
                confidence=0.8,
                source="conversation_analysis",
                metadata={"topic": topic}
            )
            factors = ConfidenceFactors(
                intent_confidence=0.0,
                behavioral_confidence=0.8,
                timeline_confidence=0.0,
                aggregate_score=0.8
            )
            return TransitionCandidate(
                target_stage=self.target_stage,
                transition_type=TransitionType.PROGRESSION,
                confidence_factors=factors,
                evidence=[evidence],
                rule_id=self.rule_id
            )
        return None

class PropertyNegotiationRule(AbstractStageProgressionRule):
    """Rule to transition to NEGOTIATION."""

    @property
    def source_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.SITE_VISIT_COMPLETED, JourneyStageCode.PROPERTY_SHORTLISTED]

    @property
    def target_stage(self) -> JourneyStageCode:
        return JourneyStageCode.NEGOTIATION

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return [JourneyType.PROPERTY_PURCHASE, JourneyType.PROPERTY_RENTAL]

    @property
    def rule_id(self) -> str:
        return "real_estate.property_negotiation"

    def evaluate(self) -> TransitionCandidate | None:
        if self._has_intent("NEGOTIATION") and self._has_topic("pricing"):
            conf = self._get_intent_confidence("NEGOTIATION")
            evidence1 = self._build_evidence(
                evidence_type=EvidenceType.INTENT_DETECTED,
                description="Detected NEGOTIATION intent.",
                confidence=conf,
                source="intent_engine",
                metadata={"intent": "NEGOTIATION"}
            )
            evidence2 = self._build_evidence(
                evidence_type=EvidenceType.CONVERSATION_TOPIC,
                description="Found pricing topic.",
                confidence=0.8,
                source="conversation_analysis",
                metadata={"topic": "pricing"}
            )
            factors = ConfidenceFactors(
                intent_confidence=conf,
                behavioral_confidence=0.8,
                timeline_confidence=0.0,
                aggregate_score=(conf + 0.8) / 2
            )
            return TransitionCandidate(
                target_stage=self.target_stage,
                transition_type=TransitionType.PROGRESSION,
                confidence_factors=factors,
                evidence=[evidence1, evidence2],
                rule_id=self.rule_id
            )
        return None

class BookingInterestRule(AbstractStageProgressionRule):
    """Rule to transition to BOOKING."""

    @property
    def source_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.NEGOTIATION]

    @property
    def target_stage(self) -> JourneyStageCode:
        return JourneyStageCode.BOOKING

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return [JourneyType.PROPERTY_PURCHASE, JourneyType.PROPERTY_RENTAL]

    @property
    def rule_id(self) -> str:
        return "real_estate.booking_interest"

    def evaluate(self) -> TransitionCandidate | None:
        if self._has_intent("BOOKING_INTEREST") and self._has_topic("booking"):
            conf = self._get_intent_confidence("BOOKING_INTEREST")
            evidence1 = self._build_evidence(
                evidence_type=EvidenceType.INTENT_DETECTED,
                description="Detected BOOKING_INTEREST intent.",
                confidence=conf,
                source="intent_engine",
                metadata={"intent": "BOOKING_INTEREST"}
            )
            evidence2 = self._build_evidence(
                evidence_type=EvidenceType.CONVERSATION_TOPIC,
                description="Found booking topic.",
                confidence=0.9,
                source="conversation_analysis",
                metadata={"topic": "booking"}
            )
            factors = ConfidenceFactors(
                intent_confidence=conf,
                behavioral_confidence=0.9,
                timeline_confidence=0.0,
                aggregate_score=(conf + 0.9) / 2
            )
            return TransitionCandidate(
                target_stage=self.target_stage,
                transition_type=TransitionType.PROGRESSION,
                confidence_factors=factors,
                evidence=[evidence1, evidence2],
                rule_id=self.rule_id
            )
        return None

class BookingCompletionRule(AbstractStageProgressionRule):
    """Rule to transition to CLOSED_WON."""

    @property
    def source_stages(self) -> List[JourneyStageCode]:
        return [JourneyStageCode.BOOKING]

    @property
    def target_stage(self) -> JourneyStageCode:
        return JourneyStageCode.CLOSED_WON

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return [JourneyType.PROPERTY_PURCHASE, JourneyType.PROPERTY_RENTAL]

    @property
    def rule_id(self) -> str:
        return "real_estate.booking_completion"

    def evaluate(self) -> TransitionCandidate | None:
        if self._has_timeline_event(TimelineEventType.BOOKING_CONFIRMED):
            evidence = self._build_evidence(
                evidence_type=EvidenceType.TIMELINE_EVENT,
                description="Timeline event BOOKING_CONFIRMED found.",
                confidence=1.0,
                source="timeline",
                metadata={"event_type": TimelineEventType.BOOKING_CONFIRMED.value}
            )
            factors = ConfidenceFactors(
                intent_confidence=0.0,
                behavioral_confidence=0.0,
                timeline_confidence=1.0,
                aggregate_score=1.0
            )
            return TransitionCandidate(
                target_stage=self.target_stage,
                transition_type=TransitionType.PROGRESSION,
                confidence_factors=factors,
                evidence=[evidence],
                rule_id=self.rule_id
            )
        return None

class PropertyCancellationRule(AbstractStageProgressionRule):
    """Rule to transition to CLOSED_LOST."""

    @property
    def source_stages(self) -> List[JourneyStageCode]:
        return [
            JourneyStageCode.NEW_LEAD, JourneyStageCode.INTERESTED, JourneyStageCode.QUALIFIED,
            JourneyStageCode.SITE_VISIT_SCHEDULED, JourneyStageCode.SITE_VISIT_COMPLETED,
            JourneyStageCode.PROPERTY_SHORTLISTED, JourneyStageCode.NEGOTIATION, JourneyStageCode.BOOKING
        ]

    @property
    def target_stage(self) -> JourneyStageCode:
        return JourneyStageCode.CLOSED_LOST

    @property
    def supported_journey_types(self) -> List[JourneyType]:
        return [JourneyType.PROPERTY_PURCHASE, JourneyType.PROPERTY_RENTAL]

    @property
    def rule_id(self) -> str:
        return "real_estate.property_cancellation"

    def evaluate(self) -> TransitionCandidate | None:
        if self._has_intent("CANCELLATION"):
            conf = self._get_intent_confidence("CANCELLATION")
            evidence = self._build_evidence(
                evidence_type=EvidenceType.INTENT_DETECTED,
                description="Detected CANCELLATION intent.",
                confidence=conf,
                source="intent_engine",
                metadata={"intent": "CANCELLATION"}
            )
            factors = ConfidenceFactors(
                intent_confidence=conf,
                behavioral_confidence=0.0,
                timeline_confidence=0.0,
                aggregate_score=conf
            )
            return TransitionCandidate(
                target_stage=self.target_stage,
                transition_type=TransitionType.CHURN, # Using CHURN for cancellation/closed lost
                confidence_factors=factors,
                evidence=[evidence],
                rule_id=self.rule_id
            )
        return None


class RealEstateStageRulePack:
    """Pack of all real estate stage rules."""
    
    @staticmethod
    def get_rules() -> List[AbstractStageProgressionRule]:
        """Get instances of all real estate progression rules."""
        return [
            PropertyInterestRule(),
            SiteVisitScheduledRule(),
            SiteVisitCompletedRule(),
            PropertyShortlistedRule(),
            PropertyNegotiationRule(),
            BookingInterestRule(),
            BookingCompletionRule(),
            PropertyCancellationRule()
        ]

def register_real_estate_rules(registry):
    """Registers all real estate rules to the given registry."""
    for rule in RealEstateStageRulePack.get_rules():
        registry.register(rule)
