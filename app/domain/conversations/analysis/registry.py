"""
HunterOS Engage — Analysis Artifact & Summary Template Registries (Phase 2.2.1)

Provides dynamic, extensible registries for custom analysis artifacts,
descriptors, and pluggable multi-perspective summary templates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from app.domain.conversations.analysis.models import (
    FactCategory,
    SegmentType,
    SummaryType,
)


# ── Analysis Artifact Registry ────────────────────────────────────────────────

@dataclass
class AnalysisArtifactDescriptor:
    """Descriptor defining a registered analysis artifact schema."""

    name: str
    category: str
    description: str
    schema_version: str = "1.0.0"
    is_custom: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnalysisArtifactRegistry:
    """
    Extensible registry for registering analysis artifact descriptors and custom serializers.
    Allows future modules to introduce new analytical dimensions without modifying pipeline stages.
    """

    def __init__(self) -> None:
        self._descriptors: Dict[str, AnalysisArtifactDescriptor] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register default core artifact descriptors."""
        self.register(
            AnalysisArtifactDescriptor(
                name="CONVERSATION_METADATA",
                category="METADATA",
                description="Structural conversation telemetry, durations, participant and message counts.",
            )
        )
        self.register(
            AnalysisArtifactDescriptor(
                name="CONVERSATION_SEGMENTS",
                category="SEGMENTATION",
                description="Temporal segmentation into Greeting, Discovery, Discussion, Negotiation, Closing, Follow-up.",
            )
        )
        self.register(
            AnalysisArtifactDescriptor(
                name="TOPIC_ANALYSIS",
                category="TOPICS",
                description="Hierarchical topic detection with primary/secondary classification, distributions, and timeline.",
            )
        )
        self.register(
            AnalysisArtifactDescriptor(
                name="KEY_FACTS",
                category="FACTS",
                description="Extracted customer, company, property, budget, date, contact, and document facts with canonical normalization.",
            )
        )
        self.register(
            AnalysisArtifactDescriptor(
                name="CONVERSATION_SUMMARIES",
                category="SUMMARIES",
                description="Multi-perspective deterministic summaries (Executive, Customer, Internal, Technical).",
            )
        )

    def register(self, descriptor: AnalysisArtifactDescriptor) -> None:
        """Register a new or custom artifact descriptor."""
        self._descriptors[descriptor.name.upper()] = descriptor

    def get(self, name: str) -> Optional[AnalysisArtifactDescriptor]:
        """Lookup descriptor by name."""
        return self._descriptors.get(name.upper())

    def list_descriptors(self) -> List[AnalysisArtifactDescriptor]:
        """List all registered artifact descriptors."""
        return list(self._descriptors.values())


# ── Summary Template Registry ─────────────────────────────────────────────────

class AbstractSummaryTemplate(ABC):
    """Abstract contract for deterministic summary generation templates."""

    def __init__(self, template_name: str, summary_type: SummaryType, description: str) -> None:
        self.template_name = template_name
        self.summary_type = summary_type
        self.description = description

    @abstractmethod
    def render(self, context: Any) -> Tuple[str, List[str]]:
        """
        Generate summary content and key bullet points from analysis context.
        Returns: (content_string, list_of_key_points)
        """
        pass


class ExecutiveSummaryTemplate(AbstractSummaryTemplate):
    """High-level concise business overview for executive stakeholders."""

    def __init__(self) -> None:
        super().__init__(
            template_name="EXECUTIVE_DEFAULT",
            summary_type=SummaryType.EXECUTIVE,
            description="High-level commercial overview focusing on participants, primary topics, and key commercial facts.",
        )

    def render(self, context: Any) -> Tuple[str, List[str]]:
        msg_count = len(context.normalized_messages)
        primary_topic = context.topics.primary_topic if context.topics else "General Discussion"
        
        # Collect top facts
        budget_facts = [f for f in context.facts if f.category == FactCategory.BUDGET_REFERENCE]
        prop_facts = [f for f in context.facts if f.category == FactCategory.PROPERTY_REFERENCE]
        date_facts = [f for f in context.facts if f.category == FactCategory.DATE_REFERENCE]

        key_points: List[str] = [
            f"Conversation spanning {msg_count} messages focused primarily on {primary_topic}."
        ]

        if budget_facts:
            key_points.append(f"Budget discussed: {budget_facts[0].canonical_value.formatted or budget_facts[0].raw_value}.")
        if prop_facts:
            key_points.append(f"Property / Product identified: {prop_facts[0].raw_value}.")
        if date_facts:
            key_points.append(f"Target timeline / schedule: {date_facts[0].canonical_value.formatted or date_facts[0].raw_value}.")

        content = (
            f"Executive Overview: Conversation of {msg_count} messages with focus on {primary_topic}. "
            + " ".join(key_points)
        )
        return content, key_points


class CustomerSummaryTemplate(AbstractSummaryTemplate):
    """Customer-facing recap of discussed points and agreed requirements."""

    def __init__(self) -> None:
        super().__init__(
            template_name="CUSTOMER_DEFAULT",
            summary_type=SummaryType.CUSTOMER,
            description="Polite customer recap summarizing their inquiries and key information shared.",
        )

    def render(self, context: Any) -> Tuple[str, List[str]]:
        primary_topic = context.topics.primary_topic if context.topics else "our discussion"
        key_points: List[str] = [
            f"Discussed requirements regarding {primary_topic}."
        ]
        
        for f in context.facts[:4]:
            key_points.append(f"{f.key.replace('_', ' ').capitalize()}: {f.canonical_value.formatted or f.raw_value}")

        content = (
            f"Summary of our conversation regarding {primary_topic}: "
            + "; ".join(key_points)
        )
        return content, key_points


class InternalSummaryTemplate(AbstractSummaryTemplate):
    """Operational notes for internal team members and CRM handlers."""

    def __init__(self) -> None:
        super().__init__(
            template_name="INTERNAL_DEFAULT",
            summary_type=SummaryType.INTERNAL,
            description="Operational internal briefing including contact information, facts, and segments.",
        )

    def render(self, context: Any) -> Tuple[str, List[str]]:
        contact_facts = [f for f in context.facts if f.category == FactCategory.CONTACT_INFO]
        segments = [s.segment_type.value for s in context.segments]
        
        key_points: List[str] = [
            f"Completed conversation phases: {', '.join(segments) if segments else 'General'}",
            f"Total facts extracted: {len(context.facts)}",
        ]
        if contact_facts:
            key_points.append(f"Contact details: {', '.join(str(c.raw_value) for c in contact_facts)}")

        content = (
            f"Internal Operational Summary: {len(context.normalized_messages)} messages processed. "
            + " | ".join(key_points)
        )
        return content, key_points


class TechnicalSummaryTemplate(AbstractSummaryTemplate):
    """Technical summary focusing on specifications, channels, and metadata."""

    def __init__(self) -> None:
        super().__init__(
            template_name="TECHNICAL_DEFAULT",
            summary_type=SummaryType.TECHNICAL,
            description="Technical summary detailing communication channels, durations, and system parameters.",
        )

    def render(self, context: Any) -> Tuple[str, List[str]]:
        meta = context.metadata
        duration = meta.duration_seconds if meta else 0.0
        channels = meta.communication_channels if meta else ["whatsapp"]
        
        key_points = [
            f"Duration: {duration:.1f}s across {len(context.normalized_messages)} messages.",
            f"Channels: {', '.join(channels)}.",
            f"Diagnostics: {len(context.diagnostics.stages_executed)} stages executed successfully.",
        ]
        content = f"Technical Summary: {'; '.join(key_points)}"
        return content, key_points


class RealEstateSummaryTemplate(AbstractSummaryTemplate):
    """Specialized custom industry template for Real Estate / Property conversations."""

    def __init__(self) -> None:
        super().__init__(
            template_name="REAL_ESTATE_SPECIALIZED",
            summary_type=SummaryType.CUSTOM,
            description="Specialized template for property buyers and real estate leads.",
        )

    def render(self, context: Any) -> Tuple[str, List[str]]:
        props = [f.raw_value for f in context.facts if f.category == FactCategory.PROPERTY_REFERENCE]
        budgets = [f.canonical_value.formatted or f.raw_value for f in context.facts if f.category == FactCategory.BUDGET_REFERENCE]
        locs = [f.raw_value for f in context.facts if f.category == FactCategory.LOCATION_REFERENCE]

        key_points = []
        if props:
            key_points.append(f"Configuration: {', '.join(str(p) for p in props)}")
        if budgets:
            key_points.append(f"Budget Range: {', '.join(str(b) for b in budgets)}")
        if locs:
            key_points.append(f"Target Locations: {', '.join(str(l) for l in locs)}")

        if not key_points:
            key_points.append("Real Estate inquiry in preliminary discovery stage.")

        content = f"Real Estate Brief: {' | '.join(key_points)}"
        return content, key_points


class SummaryTemplateRegistry:
    """
    Registry for pluggable summary templates. Allows industry-specific and custom
    summary templates to be added dynamically.
    """

    def __init__(self) -> None:
        self._templates: Dict[str, AbstractSummaryTemplate] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register standard out-of-the-box summary templates."""
        self.register(ExecutiveSummaryTemplate())
        self.register(CustomerSummaryTemplate())
        self.register(InternalSummaryTemplate())
        self.register(TechnicalSummaryTemplate())
        self.register(RealEstateSummaryTemplate())

    def register(self, template: AbstractSummaryTemplate) -> None:
        """Register a new summary template."""
        self._templates[template.template_name.upper()] = template
        # Also map by summary type value if not already set
        type_key = template.summary_type.value.upper()
        if type_key not in self._templates:
            self._templates[type_key] = template

    def get(self, name_or_type: str | SummaryType) -> Optional[AbstractSummaryTemplate]:
        """Lookup template by template name or SummaryType."""
        key = name_or_type.value if hasattr(name_or_type, "value") else str(name_or_type)
        return self._templates.get(key.upper())

    def list_templates(self) -> List[AbstractSummaryTemplate]:
        """List all unique registered templates."""
        seen = set()
        unique = []
        for t in self._templates.values():
            if t.template_name not in seen:
                seen.add(t.template_name)
                unique.append(t)
        return unique


# Default global registries
default_analysis_artifact_registry = AnalysisArtifactRegistry()
default_summary_template_registry = SummaryTemplateRegistry()
