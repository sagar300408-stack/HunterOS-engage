import uuid
from typing import Dict, Any, List

from app.domain.ui.repository import UIRepository
from app.domain.ui.registries.dashboard_registry import DashboardRegistry
from app.domain.ui.registries.widget_registry import WidgetRegistry
from app.domain.ui.schemas import DashboardPayloadSchema, WidgetDataSchema

class ComposerEngine:
    """
    Composes a complete dashboard payload by cross-referencing dashboard definitions 
    with the Widget Registry to fetch live data.
    """

    @classmethod
    async def compose_dashboard(
        cls, 
        repo: UIRepository, 
        workspace_id: uuid.UUID,
        role: str
    ) -> DashboardPayloadSchema:
        
        # 1. Fetch Definition
        db_def = await repo.get_dashboard_def(workspace_id, role)
        
        if db_def:
            config = db_def.layout_config
        else:
            # Fallback to Registry defaults
            default_config = DashboardRegistry.get_default(role)
            config = default_config.get("widgets", [])
            
        # 2. Fetch Data for each widget
        resolved_widgets = []
        for w in config:
            key = w.get("key")
            if not key:
                continue
                
            data = await WidgetRegistry.resolve_widget(key, str(workspace_id), session=repo.session)
            
            resolved_widgets.append(
                WidgetDataSchema(
                    widget_key=key,
                    title=key.replace("_", " ").title(),
                    data_payload=data
                )
            )
            
        return DashboardPayloadSchema(role=role, widgets=resolved_widgets)
