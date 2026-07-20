from typing import Dict, List, Type
from abc import ABC, abstractmethod

class ConnectorCapability(ABC):
    @property
    @abstractmethod
    def supported_entities(self) -> List[str]:
        pass

class ConnectorRegistry:
    """
    Registry for external system adapters, declaring their specific capabilities.
    """
    _adapters: Dict[str, Type[ConnectorCapability]] = {}

    @classmethod
    def register(cls, name: str, adapter_cls: Type[ConnectorCapability]):
        cls._adapters[name] = adapter_cls

    @classmethod
    def get_adapter(cls, name: str) -> Type[ConnectorCapability]:
        return cls._adapters.get(name)

    @classmethod
    def available_connectors(cls) -> List[str]:
        return list(cls._adapters.keys())
