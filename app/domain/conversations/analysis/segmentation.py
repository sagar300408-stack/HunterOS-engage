"""
HunterOS Engage — Conversation Segmentation Engine (Phase 2.2.1)

Segments conversation message streams into distinct sequential conversational phases:
Greeting, Discovery, Discussion, Negotiation, Closing, Follow-up.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.domain.conversations.analysis.models import (
    ArtifactProvenance,
    ConversationSegment,
    ExtractionMethod,
    NormalizedMessage,
    SegmentType,
    SourceMessageRef,
)


class ConversationSegmentationEngine:
    """
    Deterministically segments conversation messages into sequential phases
    based on conversation progression cues and message content markers.
    """

    # Markers for classifying individual message turns
    GREETING_PATTERNS = [
        r"\b(hi|hello|hey|good morning|good afternoon|good evening|namaste|greetings)\b",
        r"\b(my name is|i am reaching out|thanks for connecting)\b",
    ]

    DISCOVERY_PATTERNS = [
        r"\b(looking for|interested in|wanted to know|tell me about|available|can you share|details regarding|inquiry)\b",
        r"\b(what are|how much|which projects|where is|do you have)\b",
    ]

    NEGOTIATION_PATTERNS = [
        r"\b(discount|negotiable|final price|offer|deal|concession|quote|best rate|budget is|downpayment|payment plan)\b",
    ]

    CLOSING_PATTERNS = [
        r"\b(sounds good|deal|let's proceed|let's do it|finalize|booked|confirm|thank you|thanks a lot|bye|goodbye)\b",
    ]

    FOLLOW_UP_PATTERNS = [
        r"\b(follow up|follow-up|call you later|talk tomorrow|check back|next week|keep me posted|share over email)\b",
    ]

    def segment(self, messages: List[NormalizedMessage]) -> List[ConversationSegment]:
        """
        Partition normalized messages into sequential ConversationSegments.
        """
        if not messages:
            return []

        if len(messages) == 1:
            msg = messages[0]
            stype = self._classify_turn(msg.cleaned_content, position=0.5)
            return [
                ConversationSegment(
                    segment_type=stype,
                    start_message_id=msg.id,
                    end_message_id=msg.id,
                    message_count=1,
                    summary_snippet=msg.cleaned_content[:100],
                    provenance=ArtifactProvenance(
                        pipeline_stage="SegmentStage",
                        confidence=0.9,
                        source_messages=[
                            SourceMessageRef(
                                message_id=msg.id,
                                timestamp=msg.timestamp,
                                text_snippet=msg.cleaned_content[:80],
                            )
                        ],
                        extraction_method=ExtractionMethod.HEURISTIC,
                    ),
                )
            ]

        # 1. Classify each message turn
        turn_classifications: List[SegmentType] = []
        total_msgs = len(messages)

        for idx, msg in enumerate(messages):
            pos = idx / max(1, total_msgs - 1)
            stype = self._classify_turn(msg.cleaned_content, position=pos)
            turn_classifications.append(stype)

        # 2. Cluster contiguous turns into segments
        segments: List[ConversationSegment] = []
        current_type = turn_classifications[0]
        start_idx = 0

        for idx in range(1, total_msgs):
            t_type = turn_classifications[idx]
            if t_type != current_type:
                # Close current segment
                seg = self._build_segment(messages, start_idx, idx - 1, current_type)
                segments.append(seg)
                current_type = t_type
                start_idx = idx

        # Close final segment
        segments.append(self._build_segment(messages, start_idx, total_msgs - 1, current_type))
        return segments

    def _classify_turn(self, text: str, position: float) -> SegmentType:
        """Classify a single message based on regex cues and positional heuristics."""
        lowered = text.lower()

        # Check closing cues (especially towards end)
        for pat in self.CLOSING_PATTERNS:
            if re.search(pat, lowered):
                return SegmentType.CLOSING

        # Check follow-up cues
        for pat in self.FOLLOW_UP_PATTERNS:
            if re.search(pat, lowered):
                return SegmentType.FOLLOW_UP

        # Check negotiation cues
        for pat in self.NEGOTIATION_PATTERNS:
            if re.search(pat, lowered):
                return SegmentType.NEGOTIATION

        # Check greeting (especially towards beginning)
        if position <= 0.3:
            for pat in self.GREETING_PATTERNS:
                if re.search(pat, lowered):
                    return SegmentType.GREETING

        # Check discovery
        for pat in self.DISCOVERY_PATTERNS:
            if re.search(pat, lowered):
                return SegmentType.DISCOVERY

        # Positional default
        if position < 0.2:
            return SegmentType.GREETING
        elif position < 0.7:
            return SegmentType.DISCUSSION
        elif position < 0.9:
            return SegmentType.NEGOTIATION
        else:
            return SegmentType.CLOSING

    def _build_segment(
        self,
        messages: List[NormalizedMessage],
        start_idx: int,
        end_idx: int,
        segment_type: SegmentType,
    ) -> ConversationSegment:
        sub_msgs = messages[start_idx : end_idx + 1]
        start_msg = sub_msgs[0]
        end_msg = sub_msgs[-1]

        snippet = f"{segment_type.value}: {len(sub_msgs)} messages from {start_msg.sender}"
        source_refs = [
            SourceMessageRef(
                message_id=m.id,
                timestamp=m.timestamp,
                text_snippet=m.cleaned_content[:80],
            )
            for m in sub_msgs[:3]
        ]

        return ConversationSegment(
            segment_type=segment_type,
            start_message_id=start_msg.id,
            end_message_id=end_msg.id,
            message_count=len(sub_msgs),
            summary_snippet=snippet,
            provenance=ArtifactProvenance(
                pipeline_stage="SegmentStage",
                confidence=0.88,
                source_messages=source_refs,
                extraction_method=ExtractionMethod.HEURISTIC,
            ),
        )
