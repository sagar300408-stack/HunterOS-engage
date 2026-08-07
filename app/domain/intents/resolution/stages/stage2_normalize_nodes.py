"""
HunterOS Engage V1 - Stage 2: Normalize Intent Nodes
Consolidates raw items into immutable, normalized IntentNode entities with complete cross-artifact metadata.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import IntentNode


class Stage2_NormalizeIntentNodes:
    """
    Stage 2: Merges and indexes intent records from detection, classification, and evolution
    into canonical IntentNode instances.
    """

    def execute(self, context: MultiIntentResolutionContext) -> None:
        start = time.perf_counter()
        grouped: Dict[uuid.UUID, List[Dict[str, Any]]] = defaultdict(list)

        for item in context.raw_intent_items:
            iid = item.get("intent_id")
            if isinstance(iid, str):
                iid = uuid.UUID(iid)
            elif not isinstance(iid, uuid.UUID):
                iid = uuid.uuid4()
            grouped[iid].append(item)

        normalized_nodes: Dict[str, IntentNode] = {}

        for intent_id, items in grouped.items():
            canonical_name = next((it["canonical_name"] for it in items if it.get("canonical_name")), "UNKNOWN_INTENT")
            raw_intent_type = next((it["raw_intent_type"] for it in items if it.get("raw_intent_type")), canonical_name)
            category = next((it["category"] for it in items if it.get("category") and it["category"] != "GENERAL"), "GENERAL")
            taxonomy_path = next((it["taxonomy_path"] for it in items if it.get("taxonomy_path")), "")
            importance = next((it["business_importance"] for it in items if it.get("business_importance")), "NORMAL")
            lifecycle = next((it["lifecycle_state"] for it in items if it.get("lifecycle_state")), "ACTIVE")
            velocity = next((it["velocity"] for it in items if it.get("velocity")), "STABLE")

            # Max confidence across artifacts
            confidence = max((float(it.get("confidence", 0.5)) for it in items), default=1.0)
            confidence = max(0.0, min(1.0, confidence))

            # Union of source conversations
            convs = set()
            for it in items:
                if it.get("source_conversation"):
                    convs.add(it["source_conversation"])

            # Union of evidence message IDs
            ev_msg_ids = set()
            for it in items:
                ev_msg_ids.update(it.get("evidence_message_ids", []))

            # First and last seen timestamps
            timestamps = [it[k] for it in items for k in ("first_seen", "last_seen") if it.get(k) and isinstance(it[k], datetime)]
            first_seen = min(timestamps) if timestamps else datetime.now(timezone.utc)
            last_seen = max(timestamps) if timestamps else datetime.now(timezone.utc)

            node = IntentNode(
                intent_id=intent_id,
                canonical_name=canonical_name,
                raw_intent_type=raw_intent_type,
                category=category,
                taxonomy_path=taxonomy_path,
                confidence=confidence,
                business_importance=importance,
                lifecycle_state=lifecycle,
                velocity=velocity,
                source_conversations=list(convs),
                evidence_count=len(ev_msg_ids),
                evidence_message_ids=list(ev_msg_ids),
                first_seen=first_seen,
                last_seen=last_seen,
                metadata={"items_merged_count": len(items)},
            )
            normalized_nodes[str(intent_id)] = node

        context.normalized_nodes = normalized_nodes
        duration = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage2_NormalizeIntentNodes", duration)
