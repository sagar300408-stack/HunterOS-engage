from typing import Dict, Any, Callable
from abc import ABC, abstractmethod

class WidgetDataSource(ABC):
    @abstractmethod
    async def fetch_data(self, workspace_id: str, session=None, **kwargs) -> Dict[str, Any]:
        pass

from datetime import datetime, timezone, timedelta
import uuid
from app.integrations.postgres.database import get_session
from app.domain.impact.repository import ImpactRepository

class RealROIWidgetSource(WidgetDataSource):
    async def fetch_data(self, workspace_id: str, session=None, **kwargs) -> Dict[str, Any]:
        # Typically want to look at a time period. Let's do past 30 days as default if not passed.
        start_date = kwargs.get("start_date", datetime.now(timezone.utc) - timedelta(days=30))
        end_date = kwargs.get("end_date", datetime.now(timezone.utc))
        
        async def _fetch(sess):
            repo = ImpactRepository(sess)
            attributions = await repo.get_attributions_for_period(uuid.UUID(workspace_id), start_date, end_date)
            
            total_value = sum(attr.estimated_financial_value for attr in attributions if attr.estimated_financial_value)
            
            # TODO: calculate trend by looking at previous 30 days if needed, but for now just sum.
            return {
                "roi_value": total_value,
                "currency": "USD", # Defaulting to USD, or fetch from config
                "trend": "+0%" # Placeholder for trend until historical comparison is needed
            }
            
        if session:
            return await _fetch(session)
        else:
            async with get_session() as sess:
                return await _fetch(sess)

class WidgetRegistry:
    """
    Registry linking UI widget keys to their backend data fetchers.
    """
    _registry: Dict[str, WidgetDataSource] = {}

    @classmethod
    def register(cls, key: str, source: WidgetDataSource):
        cls._registry[key] = source

    @classmethod
    async def resolve_widget(cls, key: str, workspace_id: str, session=None) -> Dict[str, Any]:
        source = cls._registry.get(key)
        if not source:
            return {"error": "Widget source not found"}
        return await source.fetch_data(workspace_id, session=session)

# Pre-registering real widgets
WidgetRegistry.register("roi_summary", RealROIWidgetSource())
