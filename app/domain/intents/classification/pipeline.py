"""
HunterOS Engage V1 - Intent Classification Pipeline
Orchestrates the deterministic 8-stage classification workflow.
"""

from __future__ import annotations

from typing import Optional

from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.classification.stages.classify_intents import (
    ClassifyIntentsStage,
)
from app.domain.intents.classification.stages.compute_relationships import (
    ComputeIntentRelationshipsStage,
)
from app.domain.intents.classification.stages.enrich_intents import EnrichIntentsStage
from app.domain.intents.classification.stages.generate_result import (
    GenerateClassificationResultStage,
)
from app.domain.intents.classification.stages.group_intents import GroupIntentsStage
from app.domain.intents.classification.stages.load_intents import LoadDetectedIntentsStage
from app.domain.intents.classification.stages.normalize_data import (
    NormalizeIntentDataStage,
)
from app.domain.intents.classification.stages.validate_classification import (
    ValidateClassificationStage,
)


class IntentClassificationPipeline:
    """
    Executes the 8-stage deterministic classification pipeline.
    """

    def __init__(
        self,
        stage1_load: Optional[LoadDetectedIntentsStage] = None,
        stage2_normalize: Optional[NormalizeIntentDataStage] = None,
        stage3_classify: Optional[ClassifyIntentsStage] = None,
        stage4_enrich: Optional[EnrichIntentsStage] = None,
        stage5_relationships: Optional[ComputeIntentRelationshipsStage] = None,
        stage6_group: Optional[GroupIntentsStage] = None,
        stage7_validate: Optional[ValidateClassificationStage] = None,
        stage8_generate: Optional[GenerateClassificationResultStage] = None,
    ):
        self.stage1_load = stage1_load or LoadDetectedIntentsStage()
        self.stage2_normalize = stage2_normalize or NormalizeIntentDataStage()
        self.stage3_classify = stage3_classify or ClassifyIntentsStage()
        self.stage4_enrich = stage4_enrich or EnrichIntentsStage()
        self.stage5_relationships = stage5_relationships or ComputeIntentRelationshipsStage()
        self.stage6_group = stage6_group or GroupIntentsStage()
        self.stage7_validate = stage7_validate or ValidateClassificationStage()
        self.stage8_generate = stage8_generate or GenerateClassificationResultStage()

    def run(self, context: IntentClassificationContext) -> IntentClassificationResult:
        """
        Executes the entire classification pipeline sequentially.
        """
        # Stage 1: Load
        self.stage1_load.execute(context)

        # Stage 2: Normalize to CanonicalIntents
        self.stage2_normalize.execute(context)

        # Stage 3: Classify Candidates
        candidates = self.stage3_classify.execute(context)

        # Stage 4: Enrich Metadata (zero inference)
        self.stage4_enrich.execute(context, candidates)

        # Stage 5: Compute Relationships
        self.stage5_relationships.execute(context)

        # Stage 6: Group Intents
        self.stage6_group.execute(context)

        # Stage 7: Validate
        self.stage7_validate.execute(context)

        # Stage 8: Generate Result
        return self.stage8_generate.execute(context)


default_classification_pipeline = IntentClassificationPipeline()
