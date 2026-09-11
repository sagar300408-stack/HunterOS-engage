"""
GoliveEngine — R9: Go-Live Assessment Executor

Coordinates the go-live readiness process:
1. Calls ReadinessEngine.evaluate() for real checks
2. Persists a GoLiveAssessment record to the database (audit trail)
3. Returns the assessment

Each call creates a new GoLiveAssessment record for audit history.
Readiness is always recomputed from current state — never cached.
"""
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.onboarding.models import GoLiveAssessment, GoLiveStatus
from app.domain.onboarding.engines.readiness import ReadinessEngine, ReadinessReport
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GoliveEngine:
    """
    Executes the go-live assessment by running ReadinessEngine checks
    and persisting the result for observability and audit.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._readiness_engine = ReadinessEngine(session)

    async def execute(self, workspace_id: uuid.UUID) -> GoLiveAssessment:
        """
        Run full readiness assessment and persist the result.

        Always recomputes from current database state.
        Creates a new GoLiveAssessment row each call (audit trail).

        Returns:
            GoLiveAssessment: persisted assessment with status and reasons.
        """
        # -- Run real readiness checks --
        report: ReadinessReport = await self._readiness_engine.evaluate(workspace_id)

        # -- Build explainable reason string --
        if report.status == GoLiveStatus.NOT_READY:
            reason = "NOT READY: " + "; ".join(report.not_ready_reasons)
        elif report.status == GoLiveStatus.READY_WITH_RECS:
            reason = "READY WITH RECOMMENDATIONS: " + "; ".join(report.recommendations)
        else:
            reason = "All required checks passed. Tenant is ready for go-live."

        # -- Persist assessment (always creates new row for audit) --
        assessment = GoLiveAssessment(
            workspace_id=workspace_id,
            status=report.status,
            readiness_score=report.readiness_score,
            deployment_confidence=report.readiness_score,  # same source of truth
            reason=reason[:2000],  # clamp to column length
            evaluated_at=report.evaluated_at,
        )
        self.session.add(assessment)
        await self.session.flush()

        logger.info(
            "golive_assessment_persisted",
            workspace_id=str(workspace_id),
            status=report.status.value,
            score=report.readiness_score,
            assessment_id=str(assessment.id),
        )

        # Attach the full report for API response (not persisted in DB but available in-memory)
        assessment._readiness_report = report

        return assessment


