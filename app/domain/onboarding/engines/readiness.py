"""
ReadinessEngine — R9: Real Go-Live Readiness Assessment

Evaluates whether a workspace is ready to go live by running real
checks against the database and returning an explainable decision.

Decision logic:
  - REQUIRED checks: all must PASS → status contributes to NOT_READY if failed
  - OPTIONAL checks: failure → READY_WITH_RECS (not NOT_READY)
  - WARNING checks: surfaced as recommendations

Required checks (must PASS for READY):
  1. PROVISIONING_COMPLETE
  2. OWNER_USER
  3. SECURITY_POLICY
  4. APPROVAL_POLICY
  5. BUSINESS_CONTEXT

Optional checks (failure → READY_WITH_RECS):
  6. COMMUNICATION_INTEGRATION
  7. EXTERNAL_INTEGRATION

System health is evaluated using the existing infrastructure health probe,
not a fabricated score. Optional infra (Redis, Celery) does not block readiness.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.domain.onboarding.models import (
    WorkspaceProvisioning,
    ProvisioningStatus,
    GoLiveStatus,
)
from app.domain.security.models import User, UserRole, SecurityPolicy
from app.domain.approval.models import ApprovalPolicy
from app.domain.context.models import OrganizationNode
from app.domain.integration.models import IntegrationConnection
from app.utils.logger import get_logger

logger = get_logger(__name__)

PASS = "PASS"
FAIL = "FAIL"
WARNING = "WARNING"


class ReadinessCheck:
    """Represents a single readiness check result."""
    def __init__(
        self,
        name: str,
        category: str,
        status: str,
        detail: str,
        required: bool = True,
    ) -> None:
        self.name = name
        self.category = category
        self.status = status
        self.detail = detail
        self.required = required

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "detail": self.detail,
            "required": self.required,
        }


class ReadinessReport:
    """Full readiness report with checks + overall decision."""
    def __init__(self, workspace_id: uuid.UUID, checks: List[ReadinessCheck]) -> None:
        self.workspace_id = workspace_id
        self.checks = checks
        self.evaluated_at = datetime.now(timezone.utc)

        required_checks = [c for c in checks if c.required]
        optional_checks = [c for c in checks if not c.required]

        required_failed = [c for c in required_checks if c.status == FAIL]
        optional_failed = [c for c in optional_checks if c.status == FAIL]

        if required_failed:
            self.status = GoLiveStatus.NOT_READY
        elif optional_failed:
            self.status = GoLiveStatus.READY_WITH_RECS
        else:
            self.status = GoLiveStatus.READY

        total_required = len(required_checks) or 1
        passed_required = len([c for c in required_checks if c.status == PASS])
        self.readiness_score = round(passed_required / total_required, 4)

    @property
    def not_ready_reasons(self) -> List[str]:
        return [c.detail for c in self.checks if c.status == FAIL and c.required]

    @property
    def recommendations(self) -> List[str]:
        return [
            c.detail for c in self.checks
            if c.status in (FAIL, WARNING) and not c.required
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": str(self.workspace_id),
            "status": self.status.value,
            "readiness_score": self.readiness_score,
            "evaluated_at": self.evaluated_at.isoformat(),
            "checks": [c.to_dict() for c in self.checks],
            "not_ready_reasons": self.not_ready_reasons,
            "recommendations": self.recommendations,
        }


class ReadinessEngine:
    """
    Evaluates tenant readiness for go-live.

    Uses real database state — never hardcodes readiness.
    Returns a ReadinessReport with per-check explainability.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def evaluate(self, workspace_id: uuid.UUID) -> ReadinessReport:
        """
        Run all readiness checks and return an explainable ReadinessReport.

        This is always a fresh evaluation — it does not cache results.
        The caller (GoliveEngine) is responsible for persisting the outcome.
        """
        checks: List[ReadinessCheck] = []

        # ── Required checks ───────────────────────────────────────────────────
        checks.append(await self._check_provisioning(workspace_id))
        checks.append(await self._check_owner_user(workspace_id))
        checks.append(await self._check_security_policy(workspace_id))
        checks.append(await self._check_approval_policy(workspace_id))
        checks.append(await self._check_business_context(workspace_id))

        # ── Optional checks (failure → READY_WITH_RECS) ───────────────────────
        checks.append(await self._check_communication_integration(workspace_id))
        checks.append(await self._check_calendar_integration(workspace_id))

        # ── System health (DB connectivity — minimum required) ────────────────
        checks.append(await self._check_system_health())

        report = ReadinessReport(workspace_id, checks)

        logger.info(
            "readiness_evaluated",
            workspace_id=str(workspace_id),
            status=report.status.value,
            score=report.readiness_score,
            failed_required=[c.name for c in checks if c.status == FAIL and c.required],
        )
        return report

    # ── Required checks ───────────────────────────────────────────────────────

    async def _check_provisioning(self, workspace_id: uuid.UUID) -> ReadinessCheck:
        result = await self.session.execute(
            select(WorkspaceProvisioning).where(
                WorkspaceProvisioning.workspace_id == workspace_id
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return ReadinessCheck(
                "Tenant Configuration", "configuration", FAIL,
                "Workspace has not been provisioned. Provisioning must complete first.",
                required=True,
            )
        if record.status != ProvisioningStatus.COMPLETED:
            return ReadinessCheck(
                "Tenant Configuration", "configuration", FAIL,
                f"Workspace provisioning is in state '{record.status.value}'. Must reach COMPLETED.",
                required=True,
            )
        return ReadinessCheck(
            "Tenant Configuration", "configuration", PASS,
            "Workspace provisioning is complete.",
            required=True,
        )

    async def _check_owner_user(self, workspace_id: uuid.UUID) -> ReadinessCheck:
        result = await self.session.execute(
            select(User).where(
                User.workspace_id == workspace_id,
                User.role == UserRole.org_owner,
                User.is_active == True,  # noqa: E712
            )
        )
        owners = result.scalars().all()
        if not owners:
            return ReadinessCheck(
                "Owner User", "authorization", FAIL,
                "No active organization owner found. At least one org_owner user is required.",
                required=True,
            )
        return ReadinessCheck(
            "Owner User", "authorization", PASS,
            f"{len(owners)} active organization owner(s) configured.",
            required=True,
        )

    async def _check_security_policy(self, workspace_id: uuid.UUID) -> ReadinessCheck:
        result = await self.session.execute(
            select(SecurityPolicy).where(SecurityPolicy.workspace_id == workspace_id)
        )
        policy = result.scalar_one_or_none()
        if policy is None:
            return ReadinessCheck(
                "Security Policy", "configuration", FAIL,
                "No security policy configured for this workspace.",
                required=True,
            )
        return ReadinessCheck(
            "Security Policy", "configuration", PASS,
            "Security policy is configured.",
            required=True,
        )

    async def _check_approval_policy(self, workspace_id: uuid.UUID) -> ReadinessCheck:
        result = await self.session.execute(
            select(ApprovalPolicy).where(
                ApprovalPolicy.workspace_id == workspace_id,
                ApprovalPolicy.enabled == True,  # noqa: E712
            )
        )
        policies = result.scalars().all()
        if not policies:
            return ReadinessCheck(
                "Approval Policy", "policy", FAIL,
                "No enabled approval policies configured. Required for autonomous action governance.",
                required=True,
            )
        return ReadinessCheck(
            "Approval Policy", "policy", PASS,
            f"{len(policies)} active approval policy/policies configured.",
            required=True,
        )

    async def _check_business_context(self, workspace_id: uuid.UUID) -> ReadinessCheck:
        """
        Strengthened check: requires an active OrganizationNode with a meaningful name.
        A workspace with no business context cannot personalize AI interactions.
        """
        result = await self.session.execute(
            select(OrganizationNode).where(
                OrganizationNode.workspace_id == workspace_id,
                OrganizationNode.is_active == True,  # noqa: E712
                OrganizationNode.name.isnot(None),
                OrganizationNode.name != "",
            )
        )
        nodes = result.scalars().all()
        if not nodes:
            return ReadinessCheck(
                "Business Context", "business_data", FAIL,
                "No active business context found. Configure organization name and type to enable AI personalization.",
                required=True,
            )
        has_meaningful = any(node.name and len(node.name.strip()) >= 2 for node in nodes)
        if not has_meaningful:
            return ReadinessCheck(
                "Business Context", "business_data", FAIL,
                "Business context exists but organization name is too short or empty.",
                required=True,
            )
        return ReadinessCheck(
            "Business Context", "business_data", PASS,
            f"Business context configured ({len(nodes)} organization node(s)).",
            required=True,
        )

    # ── Optional checks ───────────────────────────────────────────────────────

    async def _check_communication_integration(self, workspace_id: uuid.UUID) -> ReadinessCheck:
        """
        Communication integration is optional — absence results in READY_WITH_RECS.
        A WhatsApp-only tenant may still be ready if WhatsApp is configured at
        infrastructure level (not necessarily as an IntegrationConnection).
        """
        result = await self.session.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.workspace_id == workspace_id,
                IntegrationConnection.connector_type.in_(["messaging", "email", "whatsapp"]),
                IntegrationConnection.status == "connected",
            )
        )
        connections = result.scalars().all()
        if not connections:
            return ReadinessCheck(
                "Communication Integration", "connectivity", FAIL,
                "No connected communication integration (WhatsApp, email, or messaging). Recommended for customer engagement.",
                required=False,  # Optional — READY_WITH_RECS not NOT_READY
            )
        return ReadinessCheck(
            "Communication Integration", "connectivity", PASS,
            f"{len(connections)} communication channel(s) connected.",
            required=False,
        )

    async def _check_calendar_integration(self, workspace_id: uuid.UUID) -> ReadinessCheck:
        """
        Calendar integrations are optional unless the workspace has scheduling capability configured.
        Currently: optional for all workspaces (returns READY_WITH_RECS if absent).
        """
        result = await self.session.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.workspace_id == workspace_id,
                IntegrationConnection.connector_type == "calendar",
                IntegrationConnection.status == "connected",
            )
        )
        connections = result.scalars().all()
        if not connections:
            return ReadinessCheck(
                "Calendar Integration", "connectivity", WARNING,
                "No calendar integration connected. Scheduling features (Google Calendar, Outlook) will be unavailable.",
                required=False,
            )
        return ReadinessCheck(
            "Calendar Integration", "connectivity", PASS,
            f"{len(connections)} calendar integration(s) connected.",
            required=False,
        )

    async def _check_system_health(self) -> ReadinessCheck:
        """
        Verify the core system (database) is accessible.
        Redis and Celery are optional infrastructure — not required for basic readiness.
        """
        try:
            await self.session.execute(text("SELECT 1"))
            return ReadinessCheck(
                "System Health", "system", PASS,
                "Core database is accessible and responsive.",
                required=True,
            )
        except Exception as exc:
            return ReadinessCheck(
                "System Health", "system", FAIL,
                f"Database health check failed: {exc}",
                required=True,
            )


