from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional
from datetime import datetime

class JourneyContextRepository(abc.ABC):
    @abc.abstractmethod
    def save_context(self, context: Any) -> None:
        """Saves a JourneyContext to the repository."""
        pass

    @abc.abstractmethod
    def get_context(self, context_id: str) -> Optional[Any]:
        """Retrieves a JourneyContext by its ID."""
        pass

    @abc.abstractmethod
    def get_latest_context(self, workspace_id: str, entity_id: str, journey_type: str) -> Optional[Any]:
        """Retrieves the latest JourneyContext for a specific entity and journey type within a workspace."""
        pass

    @abc.abstractmethod
    def query_contexts(self, workspace_id: str, **kwargs: Any) -> List[Any]:
        """Queries JourneyContexts by workspace ID and other optional attributes."""
        pass

class InMemoryJourneyContextRepository(JourneyContextRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def save_context(self, context: Any) -> None:
        self._store[context.context_id] = context

    def get_context(self, context_id: str) -> Optional[Any]:
        return self._store.get(context_id)

    def get_latest_context(self, workspace_id: str, entity_id: str, journey_type: str) -> Optional[Any]:
        contexts = [
            c for c in self._store.values()
            if getattr(c, "workspace_id", None) == workspace_id 
            and getattr(c, "entity_id", None) == entity_id 
            and getattr(c, "journey_type", None) == journey_type
        ]
        if not contexts:
            return None
        return sorted(contexts, key=lambda x: getattr(x, "generated_at", datetime.min), reverse=True)[0]

    def query_contexts(self, workspace_id: str, **kwargs: Any) -> List[Any]:
        results = []
        for ctx in self._store.values():
            if getattr(ctx, "workspace_id", None) != workspace_id:
                continue
            
            match = True
            for k, v in kwargs.items():
                if getattr(ctx, k, None) != v:
                    match = False
                    break
            
            if match:
                results.append(ctx)
                
        return sorted(results, key=lambda x: getattr(x, "generated_at", datetime.min), reverse=True)
