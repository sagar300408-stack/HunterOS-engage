"""
HunterOS Engage — Execution Intelligence Package
app/events/intelligence/__init__.py
"""

from app.events.intelligence.analysis import HistoricalAnalyticsEngine, HistoricalTrends
from app.events.intelligence.anomalies import AbstractAnomalyDetector, DefaultAnomalyDetector
from app.events.intelligence.bottlenecks import AbstractBottleneckAnalyzer, DefaultBottleneckAnalyzer
from app.events.intelligence.config import IntelligenceConfig
from app.events.intelligence.engine import (
    AbstractExecutionIntelligenceEngine,
    DefaultExecutionIntelligenceEngine,
)
from app.events.intelligence.health import AbstractHealthCalculator, DefaultHealthCalculator
from app.events.intelligence.models import (
    AnomalyReport,
    BottleneckCategory,
    BottleneckReport,
    ComponentHealth,
    ExecutionIntelligenceReport,
    FailureCategory,
    HealthComponent,
    PatternReport,
    PatternType,
    Recommendation,
    RootCauseReport,
    SeverityLevel,
    SystemHealthReport,
)
from app.events.intelligence.patterns import AbstractPatternDetector, DefaultPatternDetector
from app.events.intelligence.recommendations import (
    AbstractRecommendationEngine,
    DefaultRecommendationEngine,
)
from app.events.intelligence.root_cause import (
    AbstractRootCauseAnalyzer,
    DefaultRootCauseAnalyzer,
)
from app.events.intelligence.validator import ExecutionIntelligenceStartupValidator

# Global singleton execution intelligence engine
intelligence_engine = DefaultExecutionIntelligenceEngine()

__all__ = [
    "IntelligenceConfig",
    "FailureCategory",
    "BottleneckCategory",
    "SeverityLevel",
    "HealthComponent",
    "PatternType",
    "RootCauseReport",
    "BottleneckReport",
    "PatternReport",
    "AnomalyReport",
    "Recommendation",
    "ComponentHealth",
    "SystemHealthReport",
    "ExecutionIntelligenceReport",
    "HistoricalTrends",
    "AbstractRootCauseAnalyzer",
    "DefaultRootCauseAnalyzer",
    "AbstractBottleneckAnalyzer",
    "DefaultBottleneckAnalyzer",
    "AbstractPatternDetector",
    "DefaultPatternDetector",
    "AbstractAnomalyDetector",
    "DefaultAnomalyDetector",
    "AbstractRecommendationEngine",
    "DefaultRecommendationEngine",
    "AbstractHealthCalculator",
    "DefaultHealthCalculator",
    "HistoricalAnalyticsEngine",
    "AbstractExecutionIntelligenceEngine",
    "DefaultExecutionIntelligenceEngine",
    "ExecutionIntelligenceStartupValidator",
    "intelligence_engine",
]
