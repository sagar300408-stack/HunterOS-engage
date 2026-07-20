from typing import Dict, Any
from app.domain.ui.schemas import CommandCenterIntent

class CommandCenterEngine:
    """
    Global command palette parser. Supports Search, Navigate, Execute, Create, Ask, Recent.
    """

    @classmethod
    async def process_query(cls, workspace_id: str, query: str) -> CommandCenterIntent:
        """
        Parses the text query to determine intent.
        In a full implementation, this uses Postgres FTS and an NLP layer.
        """
        query_lower = query.lower()
        
        if query_lower.startswith("find") or query_lower.startswith("search"):
            return CommandCenterIntent(
                intent_type="SEARCH",
                action_payload={"target": query.replace("find", "").replace("search", "").strip()}
            )
            
        if query_lower.startswith("go to") or query_lower.startswith("open"):
            return CommandCenterIntent(
                intent_type="NAVIGATE",
                action_payload={"route": query_lower.split(" ")[-1]}
            )
            
        if query_lower.startswith("summarize") or query_lower.endswith("?"):
            return CommandCenterIntent(
                intent_type="ASK",
                action_payload={"question": query}
            )
            
        # Default
        return CommandCenterIntent(
            intent_type="SEARCH",
            action_payload={"target": query}
        )
