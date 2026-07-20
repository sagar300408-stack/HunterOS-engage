from typing import Dict, Any, Callable
from abc import ABC, abstractmethod

class WidgetDataSource(ABC):
    @abstractmethod
    async def fetch_data(self, workspace_id: str, **kwargs) -> Dict[str, Any]:
        pass

class MockROIWidgetSource(WidgetDataSource):
    async def fetch_data(self, workspace_id: str, **kwargs) -> Dict[str, Any]:
        return {"roi_value": 1500000.00, "currency": "INR", "trend": "+12%"}

class WidgetRegistry:
    """
    Registry linking UI widget keys to their backend data fetchers.
    """
    _registry: Dict[str, WidgetDataSource] = {}

    @classmethod
    def register(cls, key: str, source: WidgetDataSource):
        cls._registry[key] = source

    @classmethod
    async def resolve_widget(cls, key: str, workspace_id: str) -> Dict[str, Any]:
        source = cls._registry.get(key)
        if not source:
            return {"error": "Widget source not found"}
        return await source.fetch_data(workspace_id)

# Pre-registering mock widgets
WidgetRegistry.register("roi_summary", MockROIWidgetSource())
