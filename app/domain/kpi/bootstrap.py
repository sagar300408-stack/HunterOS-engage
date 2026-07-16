from app.domain.kpi.calculators.registry import kpi_registry
from app.domain.kpi.calculators.standard_kpis import MeetingConversionRateCalculator, ReplyRateCalculator

def bootstrap_kpis() -> None:
    """Register all standard KPI calculators into the registry."""
    # We ignore if already registered for idempotent bootstraps
    try:
        kpi_registry.register(MeetingConversionRateCalculator())
    except Exception:
        pass
        
    try:
        kpi_registry.register(ReplyRateCalculator())
    except Exception:
        pass
