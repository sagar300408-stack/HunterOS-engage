from typing import Dict, Type
from .base import AbstractPriorityFactor

class PriorityFactorRegistry:
    _factors: Dict[str, Type[AbstractPriorityFactor]] = {}

    @classmethod
    def register(cls, factor_class: Type[AbstractPriorityFactor]):
        instance = factor_class()
        cls._factors[instance.factor_type()] = factor_class
        return factor_class

    @classmethod
    def get_all_instances(cls):
        return [factor_class() for factor_class in cls._factors.values()]
