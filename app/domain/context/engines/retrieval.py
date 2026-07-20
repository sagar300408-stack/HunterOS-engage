import uuid
from typing import Dict, Any, List

from app.domain.context.repository import ContextRepository
from app.domain.context.models import EntityType, CustomerContext, BusinessPolicy
from app.domain.context.engines.graph import KnowledgeGraphEngine
from app.domain.context.engines.freshness import ContextFreshnessEngine
from app.domain.context.engines.confidence import ContextConfidenceEngine

class ContextRetrievalEngine:
    """
    The central query interface for all HunterOS domains.
    Guarded by the Context Budget.
    """

    @classmethod
    async def get_customer_context(
        cls, 
        repo: ContextRepository, 
        workspace_id: uuid.UUID,
        customer_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Retrieves a Customer and 1 hop of relationships.
        """
        customer = await repo.get_active_entity(CustomerContext, customer_id)
        if not customer:
            return {}
            
        is_stale, days_since = ContextFreshnessEngine.evaluate(customer)
        confidence = ContextConfidenceEngine.evaluate(customer)
        
        edges = await KnowledgeGraphEngine.get_related_entities(repo, customer_id, max_depth=1)
        
        return {
            "entity": customer,
            "is_stale": is_stale,
            "confidence": confidence,
            "related_edges": edges
        }

    @classmethod
    async def get_decision_context(
        cls, 
        repo: ContextRepository, 
        workspace_id: uuid.UUID,
        intent_type: str
    ) -> Dict[str, Any]:
        """
        Retrieves relevant policies and workflows for a specific decision/intent.
        """
        # A mocked retrieval for demonstration
        return {
            "intent_type": intent_type,
            "active_policies_count": 5
        }
