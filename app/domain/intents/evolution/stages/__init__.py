"""
HunterOS Engage V1 - Evolution Pipeline Stages Package
"""

from app.domain.intents.evolution.stages.stage1_load_history import LoadHistoricalSnapshotsStage
from app.domain.intents.evolution.stages.stage2_load_current import LoadCurrentSnapshotStage
from app.domain.intents.evolution.stages.stage3_normalize_state import NormalizeIntentStateStage
from app.domain.intents.evolution.stages.stage4_compare_snapshots import CompareSnapshotsStage
from app.domain.intents.evolution.stages.stage5_detect_evolution import DetectEvolutionStage
from app.domain.intents.evolution.stages.stage6_project_timelines import ProjectTimelinesStage
from app.domain.intents.evolution.stages.stage7_validate_evolution import ValidateEvolutionStage
from app.domain.intents.evolution.stages.stage8_generate_result import GenerateEvolutionResultStage

__all__ = [
    "LoadHistoricalSnapshotsStage",
    "LoadCurrentSnapshotStage",
    "NormalizeIntentStateStage",
    "CompareSnapshotsStage",
    "DetectEvolutionStage",
    "ProjectTimelinesStage",
    "ValidateEvolutionStage",
    "GenerateEvolutionResultStage",
]
