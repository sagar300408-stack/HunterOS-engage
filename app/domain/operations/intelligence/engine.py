import uuid
from typing import Optional
from datetime import datetime, timezone

from app.domain.recommendations.models import Recommendation
from app.domain.operations.engine import OperationsEngine
from app.domain.operations.schemas import (
    CreateActionRequest,
    ActionEvidenceDTO,
    ActionProvenanceDTO,
)
from app.domain.operations.exceptions import ActionConflictError
from app.domain.operations.intelligence.models import (
    ActionIntelligenceResult,
    ActionIntelligenceOutcome,
    OperationalRequirement,
)
from app.domain.operations.intelligence.registry import ActionCapabilityRegistry


class ActionIntelligenceEngine:
    """
    Action Intelligence Engine.
    Bridges Phase 2 Recommendation Intelligence into Phase 3.1 Operations.
    """

    def __init__(self, operations_engine: OperationsEngine):
        self.operations_engine = operations_engine

    async def evaluate_recommendation(self, recommendation: Recommendation) -> ActionIntelligenceResult:
        """
        Evaluates a Recommendation and deterministically maps it to an Action
        if supported by the Capability Registry.
        """
        supported_action_type = ActionCapabilityRegistry.get_supported_action(recommendation.type)

        if not supported_action_type:
            return ActionIntelligenceResult(
                outcome=ActionIntelligenceOutcome.UNSUPPORTED,
                recommendation_id=recommendation.id,
                explanation=f"RecommendationType {recommendation.type.value} is not mapped to any supported ActionType.",
            )

        # Create the conceptual Operational Requirement
        requirement = OperationalRequirement(
            requirement_id=uuid.uuid4(),
            workspace_id=recommendation.workspace_id,
            source_recommendation_id=recommendation.id,
            supported_action_type=supported_action_type,
            reason=f"Matched Recommendation {recommendation.id} of type {recommendation.type.value} to ActionType {supported_action_type.value}"
        )

        # 1. Target resolution
        target_data = {}
        if recommendation.targets:
            # For V1, we take the primary target from the recommendation
            target_data = {
                "target_id": recommendation.targets[0].target_id,
                "target_type": recommendation.targets[0].target_type,
            }
            target_data.update(recommendation.targets[0].metadata)

        # 2. Evidence extraction
        evidence_list = [
            ActionEvidenceDTO(
                evidence_type="recommendation_context",
                content=recommendation.description,
                confidence=recommendation.confidence.value if recommendation.confidence else 1.0,
                metadata={"title": recommendation.title}
            )
        ]

        # 3. Provenance with explicit versioning
        provenance = ActionProvenanceDTO(
            system_source="ACTION_INTELLIGENCE",
            timestamp=datetime.now(timezone.utc).isoformat(),
            context={
                "recommendation_id": str(recommendation.id),
                "recommendation_type": recommendation.type.value,
                "recommendation_updated_at": recommendation.updated_at.isoformat(),
            }
        )

        # 4. Strict Deduplication via Idempotency Key
        idempotency_key = f"action_intel_rec_{recommendation.id}"

        # 5. Delegate to OperationsEngine (Creation ONLY)
        request = CreateActionRequest(
            workspace_id=recommendation.workspace_id,
            action_type=supported_action_type,
            priority=recommendation.priority.value,  # Direct mapping
            target=target_data,
            evidence=evidence_list,
            provenance=provenance,
            idempotency_key=idempotency_key,
        )

        try:
            # If it already exists, OperationsEngine might return the existing one or raise conflict.
            # To be strictly safe and avoid double-eventing, we can check the repo if we had direct access.
            # But the contract is to use the engine boundary.
            action = await self.operations_engine.create_action(
                workspace_id=recommendation.workspace_id,
                request=request
            )
            
            return ActionIntelligenceResult(
                outcome=ActionIntelligenceOutcome.ACTION_CREATED,
                recommendation_id=recommendation.id,
                explanation=requirement.reason,
                requirement=requirement,
                action_id=action.id
            )

        except ActionConflictError as e:
            return ActionIntelligenceResult(
                outcome=ActionIntelligenceOutcome.ACTION_ALREADY_EXISTS,
                recommendation_id=recommendation.id,
                explanation=str(e),
                requirement=requirement
            )
