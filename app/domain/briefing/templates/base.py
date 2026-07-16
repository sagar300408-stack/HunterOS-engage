import abc
from typing import List, Dict, Any
from uuid import UUID

from app.domain.briefing.schemas import BriefingCalculationResult
from app.domain.insight.models import InsightSnapshot
from app.domain.recommendation.models import RecommendationSnapshot
from app.domain.health.models import HealthSnapshot
from app.domain.kpi.models import KpiSnapshot


class BaseBriefingTemplate(abc.ABC):
    """
    Defines the contract for creating an Executive Briefing template.
    Templates filter, prioritize, and structure existing intelligence without creating new facts.
    """
    
    @property
    @abc.abstractmethod
    def template_name(self) -> str:
        pass

    @abc.abstractmethod
    def compose(
        self,
        insights: List[InsightSnapshot],
        recommendations: List[RecommendationSnapshot],
        health_snapshots: List[HealthSnapshot],
        kpis: List[KpiSnapshot]
    ) -> BriefingCalculationResult:
        """
        Composes the briefing from raw intelligence snapshots.
        """
        pass
