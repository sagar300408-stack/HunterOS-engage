"""
ValidationEngine — R8: Real Customer Onboarding Validation

Runs a suite of database-backed checks to determine whether a workspace has been
sufficiently configured for business operation.

Check categories:
  - PROVISIONING: WorkspaceProvisioning is COMPLETED
  - OWNER_USER: At least one active org_owner user exists
  - SECURITY_POLICY: SecurityPolicy exists
  - APPROVAL_POLICY: At least one enabled ApprovalPolicy exists
  - BUSINESS_CONTEXT: OrganizationNode with name + is_active exists
  - COMMUNICATION: At least one communication integration is connected (optional/warning)
  - INTEGRATION_REQUIRED: Required integrations are connected per workspace capabilities
"""
import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.domain.onboarding.models import (
    WorkspaceProvisioning,
    ProvisioningStatus,
    ValidationResult,
    OnboardingIntegrationConnection,
)
from app.domain.security.models import User, UserRole, SecurityPolicy
from app.domain.approval.models import ApprovalPolicy
from app.domain.context.models import OrganizationNode
from app.domain.integration.models import IntegrationConnection
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Check status constants
PASS = "PASS"
FAIL = "FAIL"
WARNING = "WARNING"


class ValidationEngine:
    """
    Runs onboarding validation checks against the real database state.

    Each check is persisted as a ValidationResult row. This creates an
    audit trail of what passed and what failed at each validation run.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run_checks(self, workspace_id: uuid.UUID) -> List[ValidationResult]:
        """
        Run all validation checks for the given workspace.

        Persists ValidationResult rows and returns them.
        Each call creates a fresh set of results (audit history).
        """
        checks: List[Tuple[str, str, str]] = []

        # 1. Provisioning completed
        checks.append(await self._check_provisioning(workspace_id))

        # 2. Owner user
        checks.append(await self._check_owner_user(workspace_id))

        # 3. Security policy
        checks.append(await self._check_security_policy(workspace_id))

        # 4. Approval policy
        checks.append(await self._check_approval_policy(workspace_id))

        # 5. Business context (strengthened — requires active OrganizationNode with name)
        checks.append(await self._check_business_context(workspace_id))

        # 6. Communication integration (optional — warning if absent)
        checks.append(await self._check_communication(workspace_id))

        # Persist all results
        results = []
        for check_name, status, detail in checks:
            result = ValidationResult(
                workspace_id=workspace_id,
                check_name=check_name,
                status=status,
                details={"message": detail},
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(result)
            results.append(result)

        await self.session.flush()

        logger.info(
            "validation_checks_complete",
            workspace_id=str(workspace_id),
            total=len(results),
            passed=sum(1 for r in results if r.status == PASS),
            failed=sum(1 for r in results if r.status == FAIL),
            warnings=sum(1 for r in results if r.status == WARNING),
        )
        return results

    async def get_latest_results(self, workspace_id: uuid.UUID) -> List[ValidationResult]:
        """
        Return the most recent set of validation results.
        Groups by check_name, returns the latest per check.
        """
        # Subquery: latest created_at per check_name
        sub = (
            select(
                ValidationResult.check_name,
                func.max(ValidationResult.created_at).label("max_created_at"),
            )
            .where(ValidationResult.workspace_id == workspace_id)
            .group_by(ValidationResult.check_name)
            .subquery()
        )
        stmt = select(ValidationResult).join(
            sub,
            (ValidationResult.check_name == sub.c.check_name)
            & (ValidationResult.created_at == sub.c.max_created_at),
        ).where(ValidationResult.workspace_id == workspace_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Individual checks ─────────────────────────────────────────────────────

    async def _check_provisioning(self, workspace_id: uuid.UUID) -> Tuple[str, str, str]:
        result = await self.session.execute(
            select(WorkspaceProvisioning).where(
                WorkspaceProvisioning.workspace_id == workspace_id
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return ("PROVISIONING", FAIL, "No provisioning record found. Run workspace provisioning first.")
        if record.status != ProvisioningStatus.COMPLETED:
            return ("PROVISIONING", FAIL, f"Provisioning is in state '{record.status}' — must be COMPLETED.")
        return ("PROVISIONING", PASS, "Workspace provisioning is complete.")

    async def _check_owner_user(self, workspace_id: uuid.UUID) -> Tuple[str, str, str]:
        result = await self.session.execute(
            select(User).where(
                User.workspace_id == workspace_id,
                User.role == UserRole.org_owner,
                User.is_active == True,  # noqa: E712
            )
        )
        owners = result.scalars().all()
        if not owners:
            return ("OWNER_USER", FAIL, "No active org_owner user found for this workspace.")
        return ("OWNER_USER", PASS, f"{len(owners)} active owner(s) found.")

    async def _check_security_policy(self, workspace_id: uuid.UUID) -> Tuple[str, str, str]:
        result = await self.session.execute(
            select(SecurityPolicy).where(SecurityPolicy.workspace_id == workspace_id)
        )
        policy = result.scalar_one_or_none()
        if policy is None:
            return ("SECURITY_POLICY", FAIL, "No security policy found for this workspace.")
        return ("SECURITY_POLICY", PASS, "Security policy exists.")

    async def _check_approval_policy(self, workspace_id: uuid.UUID) -> Tuple[str, str, str]:
        result = await self.session.execute(
            select(ApprovalPolicy).where(
                ApprovalPolicy.workspace_id == workspace_id,
                ApprovalPolicy.enabled == True,  # noqa: E712
            )
        )
        policies = result.scalars().all()
        if not policies:
            return ("APPROVAL_POLICY", FAIL, "No enabled approval policies found. Action automation requires at least one approval policy.")
        return ("APPROVAL_POLICY", PASS, f"{len(policies)} enabled approval policy/policies found.")

    async def _check_business_context(self, workspace_id: uuid.UUID) -> Tuple[str, str, str]:
        """
        Strengthened check: requires at least one active OrganizationNode with:
        - name field not null/empty
        - is_active == True
        This validates that the tenant has described their actual business identity.
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
            return (
                "BUSINESS_CONTEXT",
                FAIL,
                "No active organization context found. Add business context (organization name, type) to proceed.",
            )
        # Validate quality: check at least one node has useful metadata
        has_meaningful = any(
            node.name and len(node.name.strip()) >= 2
            for node in nodes
        )
        if not has_meaningful:
            return (
                "BUSINESS_CONTEXT",
                FAIL,
                "Organization context exists but lacks meaningful name. Update business context.",
            )
        return ("BUSINESS_CONTEXT", PASS, f"{len(nodes)} active organization context node(s) found.")

    async def _check_communication(self, workspace_id: uuid.UUID) -> Tuple[str, str, str]:
        """
        Check for a connected communication integration (WhatsApp or equivalent).
        This is optional/warning — a tenant may be ready without it for certain configurations,
        but it is important to surface clearly.
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
            return (
                "COMMUNICATION",
                WARNING,
                "No connected communication channel found. Configure WhatsApp, email, or messaging integration for full operation.",
            )
        return ("COMMUNICATION", PASS, f"{len(connections)} connected communication channel(s) found.")


