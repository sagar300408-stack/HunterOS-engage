from typing import Dict, List, Type

from app.domain.kpi.calculators.base import BaseKpiCalculator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KpiRegistryError(Exception):
    pass


class KpiRegistry:
    """
    Registry for all KPI Calculators.
    Follows a singleton pattern.
    """

    def __init__(self) -> None:
        self._calculators: Dict[str, BaseKpiCalculator] = {}

    def register(self, calculator: BaseKpiCalculator) -> None:
        """Register an instantiated KPI calculator."""
        name = calculator.definition.name
        if name in self._calculators:
            raise KpiRegistryError(f"KPI Calculator for '{name}' is already registered.")
        
        self._calculators[name] = calculator
        logger.debug("kpi_calculator_registered", kpi_name=name)

    def get_calculator(self, kpi_name: str) -> BaseKpiCalculator:
        """Retrieve a specific calculator by its KPI name."""
        if kpi_name not in self._calculators:
            raise KpiRegistryError(f"KPI Calculator '{kpi_name}' not found in registry.")
        return self._calculators[kpi_name]

    def get_all_calculators(self) -> List[BaseKpiCalculator]:
        """Return all registered calculators."""
        return list(self._calculators.values())


# Singleton instance
kpi_registry = KpiRegistry()
