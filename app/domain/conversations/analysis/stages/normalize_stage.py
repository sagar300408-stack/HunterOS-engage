"""
HunterOS Engage — Normalize Stage (Phase 2.2.1)

Normalizes raw messages into standardized NormalizedMessage models and extracts metadata.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.context import ConversationAnalysisContext
from app.domain.conversations.analysis.engines import ConversationMetadataExtractor
from app.domain.conversations.analysis.models import (
    MessageDirection,
    NormalizedMessage,
    PipelineState,
)
from app.domain.conversations.analysis.stages.base import PipelineStage


class NormalizeStage(PipelineStage):
    """
    Normalizes raw message payloads into uniform NormalizedMessage objects,
    removes whitespace/transport noise, and extracts structural metadata.
    """

    def __init__(self, metadata_extractor: Optional[ConversationMetadataExtractor] = None) -> None:
        self._meta_extractor = metadata_extractor or ConversationMetadataExtractor()

    @property
    def stage_name(self) -> str:
        return "NormalizeStage"

    @property
    def target_state(self) -> PipelineState:
        return PipelineState.NORMALIZING

    def execute(self, context: ConversationAnalysisContext) -> ConversationAnalysisContext:
        normalized: List[NormalizedMessage] = []

        for idx, raw in enumerate(context.raw_messages):
            norm_msg = self._normalize_single_message(raw, idx, context.conversation_id)
            normalized.append(norm_msg)

        context.normalized_messages = normalized

        # Extract structural conversation metadata
        conv_id = context.conversation_id or (normalized[0].conversation_id if normalized else str(uuid.uuid4()))
        context.metadata = self._meta_extractor.extract_metadata(
            conversation_id=conv_id,
            messages=normalized,
            workspace_id=context.workspace_id,
            raw_metadata=context.raw_metadata,
        )

        return context

    def _normalize_single_message(
        self,
        raw: Any,
        idx: int,
        default_conv_id: Optional[str] = None,
    ) -> NormalizedMessage:
        # Extract attributes from Dict or Object
        if isinstance(raw, dict):
            m_id = str(raw.get("id") or raw.get("message_id") or f"msg_{idx+1}")
            conv_id = str(raw.get("conversation_id") or default_conv_id or "default")
            sender = str(raw.get("sender") or raw.get("sender_type") or "user")
            content = str(raw.get("content") or raw.get("text") or raw.get("body") or "")
            ts = raw.get("timestamp") or raw.get("created_at")
            channel = str(raw.get("channel") or "whatsapp")
            attachments = raw.get("attachments") or []
            meta = raw.get("metadata") or {}
            dir_val = raw.get("direction")
        else:
            m_id = str(getattr(raw, "id", None) or getattr(raw, "message_id", None) or f"msg_{idx+1}")
            conv_id = str(getattr(raw, "conversation_id", None) or default_conv_id or "default")
            sender = str(getattr(raw, "sender", None) or getattr(raw, "sender_type", None) or "user")
            content = str(getattr(raw, "content", None) or getattr(raw, "text", None) or getattr(raw, "body", None) or "")
            ts = getattr(raw, "timestamp", None) or getattr(raw, "created_at", None)
            channel = str(getattr(raw, "channel", None) or "whatsapp")
            attachments = getattr(raw, "attachments", None) or []
            meta = getattr(raw, "metadata", None) or {}
            dir_val = getattr(raw, "direction", None)

        # Parse timestamp
        if isinstance(ts, datetime):
            parsed_ts = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        elif isinstance(ts, str):
            try:
                parsed_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                parsed_ts = datetime.now(timezone.utc)
        else:
            parsed_ts = datetime.now(timezone.utc)

        # Determine direction
        if dir_val:
            dir_str = str(dir_val).upper()
            if "IN" in dir_str:
                direction = MessageDirection.INCOMING
            elif "OUT" in dir_str:
                direction = MessageDirection.OUTGOING
            else:
                direction = MessageDirection.SYSTEM
        else:
            # Infer direction from sender
            sender_low = sender.lower()
            if sender_low in ["agent", "system", "assistant", "bot", "representative"]:
                direction = MessageDirection.OUTGOING
            else:
                direction = MessageDirection.INCOMING

        # Clean noise & normalize whitespace
        cleaned = re.sub(r"\s+", " ", content).strip()

        return NormalizedMessage(
            id=m_id,
            conversation_id=conv_id,
            direction=direction,
            sender=sender,
            content=content,
            cleaned_content=cleaned,
            timestamp=parsed_ts,
            channel=channel,
            attachments=attachments if isinstance(attachments, list) else [],
            metadata=meta if isinstance(meta, dict) else {},
        )
