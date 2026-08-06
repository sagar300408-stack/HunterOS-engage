"""
HunterOS Engage — Summary Generator (Phase 2.2.1)

Generates multi-perspective deterministic conversation summaries
using the SummaryTemplateRegistry.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.extractors.base import AbstractSummaryGenerator
from app.domain.conversations.analysis.models import (
    ArtifactProvenance,
    ConversationSummary,
    ExtractionMethod,
    SourceMessageRef,
    SummaryType,
)
from app.domain.conversations.analysis.registry import (
    SummaryTemplateRegistry,
    default_summary_template_registry,
)


class TemplateBasedSummaryGenerator(AbstractSummaryGenerator):
    """
    Generates multi-perspective summaries by querying registered templates.
    """

    def __init__(self, registry: Optional[SummaryTemplateRegistry] = None) -> None:
        self._registry = registry or default_summary_template_registry

    def generate_summary(
        self,
        summary_type: SummaryType,
        context: Any,
        template_name: Optional[str] = None,
    ) -> ConversationSummary:
        lookup_key = template_name or summary_type
        template = self._registry.get(lookup_key)

        if not template:
            # Fallback default summary
            content = f"Summary ({summary_type.value}): Processed {len(context.normalized_messages)} messages."
            key_points = [f"Total messages: {len(context.normalized_messages)}"]
            used_template_name = "FALLBACK"
        else:
            content, key_points = template.render(context)
            used_template_name = template.template_name

        # Collect sample source message references
        source_refs: List[SourceMessageRef] = []
        for msg in context.normalized_messages[:5]:
            source_refs.append(
                SourceMessageRef(
                    message_id=msg.id,
                    timestamp=msg.timestamp,
                    text_snippet=msg.cleaned_content[:80],
                )
            )

        return ConversationSummary(
            summary_type=summary_type,
            template_name=used_template_name,
            content=content,
            key_points=key_points,
            provenance=ArtifactProvenance(
                pipeline_stage="SummaryStage",
                confidence=0.95,
                source_messages=source_refs,
                extraction_method=ExtractionMethod.TEMPLATE,
            ),
        )
