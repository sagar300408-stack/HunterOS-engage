"""
WorkspaceEngine — R7: Real Tenant Provisioning

Provisions a new workspace with all required foundational resources:
  - WorkspaceProvisioning record (tracks status)
  - Owner User (org_owner role)
  - SecurityPolicy
  - Default ApprovalPolicy

Key design properties:
  - Idempotent: repeated calls for same workspace_id converge safely
  - Concurrency-safe: uses PostgreSQL advisory lock
  - Failure-aware: partial failures captured in FAILED status
  - Tenant-scoped: every resource tagged with correct workspace_id
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.domain.onboarding.models import WorkspaceProvisioning, ProvisioningStatus
from app.domain.security.models import User, UserRole, SecurityPolicy
from app.domain.approval.models import ApprovalPolicy
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WorkspaceEngine:
    """
    Manages workspace provisioning lifecycle.

    Usage:
        engine = WorkspaceEngine(session)
        result = await engine.provision_workspace(
            workspace_id=uuid4(),
            owner_email="alice@company.com",
            owner_name="Alice",
            password_hash=hash_password("secret"),
        )
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def provision_workspace(
        self,
        workspace_id: uuid.UUID,
        owner_email: str,
        owner_name: str,
        password_hash: str,
    ) -> WorkspaceProvisioning:
        """
        Idempotent workspace provisioning.

        Returns WorkspaceProvisioning in COMPLETED state if successful, or
        FAILED state if a step fails. Repeated calls on a COMPLETED workspace
        return the existing record without modification.

        Concurrency: uses PostgreSQL pg_advisory_xact_lock scoped to workspace_id
        to prevent two simultaneous requests from creating duplicate resources.
        """
        # -- Advisory lock serializes concurrent requests for same workspace_id --
        lock_key = abs(hash(str(workspace_id))) % (2**31)
        await self.session.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))

        # -- Idempotency: return early if already completed --
        existing = await self._get_provisioning(workspace_id)
        if existing and existing.status == ProvisioningStatus.COMPLETED:
            logger.info("workspace_provisioning_already_complete", workspace_id=str(workspace_id))
            return existing

        # -- Create or resume provisioning record --
        if existing is None:
            provisioning = WorkspaceProvisioning(
                workspace_id=workspace_id,
                status=ProvisioningStatus.IN_PROGRESS,
                current_step="INITIALIZATION",
            )
            self.session.add(provisioning)
            await self.session.flush()
        else:
            # Retry of PENDING or FAILED — restart
            provisioning = existing
            provisioning.status = ProvisioningStatus.IN_PROGRESS
            provisioning.current_step = "INITIALIZATION"
            await self.session.flush()

        try:
            # Step 1: Ensure owner user
            provisioning.current_step = "OWNER_USER"
            await self.session.flush()
            await self._ensure_owner_user(workspace_id, owner_email, owner_name, password_hash)
            logger.info("workspace_step_complete", step="OWNER_USER", workspace_id=str(workspace_id))

            # Step 2: Ensure security policy
            provisioning.current_step = "SECURITY_POLICY"
            await self.session.flush()
            await self._ensure_security_policy(workspace_id)
            logger.info("workspace_step_complete", step="SECURITY_POLICY", workspace_id=str(workspace_id))

            # Step 3: Ensure default approval policy
            provisioning.current_step = "APPROVAL_POLICY"
            await self.session.flush()
            await self._ensure_approval_policy(workspace_id)
            logger.info("workspace_step_complete", step="APPROVAL_POLICY", workspace_id=str(workspace_id))

            # -- Mark complete --
            provisioning.status = ProvisioningStatus.COMPLETED
            provisioning.current_step = "COMPLETE"
            provisioning.completed_at = datetime.now(timezone.utc)
            await self.session.flush()

            logger.info(
                "workspace_provisioned",
                workspace_id=str(workspace_id),
                owner_email=owner_email,
            )
            return provisioning

        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception("Original provisioning error before rollback/flush:")
            provisioning.status = ProvisioningStatus.FAILED
            try:
                await self.session.flush()
            except Exception as flush_exc:
                logging.getLogger(__name__).error(f"Failed to flush FAILED status: {flush_exc}")
            logger.error(
                "workspace_provisioning_failed",
                workspace_id=str(workspace_id),
                step=provisioning.current_step,
                error=str(exc),
            )
            raise

    async def get_provisioning_status(self, workspace_id: uuid.UUID) -> Optional[WorkspaceProvisioning]:
        """Return the current provisioning record for a workspace."""
        return await self._get_provisioning(workspace_id)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_provisioning(self, workspace_id: uuid.UUID) -> Optional[WorkspaceProvisioning]:
        result = await self.session.execute(
            select(WorkspaceProvisioning).where(
                WorkspaceProvisioning.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def _ensure_owner_user(
        self,
        workspace_id: uuid.UUID,
        email: str,
        name: str,
        password_hash: str,
    ) -> User:
        """
        Ensure an org_owner user exists for this workspace.
        Idempotent: will not create a duplicate if already exists.
        """
        result = await self.session.execute(
            select(User).where(
                User.workspace_id == workspace_id,
                User.role == UserRole.org_owner,
                User.email == email,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Check if email is already taken globally
        result2 = await self.session.execute(
            select(User).where(User.email == email)
        )
        if result2.scalar_one_or_none():
            raise ValueError(f"Email '{email}' is already registered.")

        user = User(
            workspace_id=workspace_id,
            email=email,
            full_name=name,
            password_hash=password_hash,
            role=UserRole.org_owner,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def _ensure_security_policy(self, workspace_id: uuid.UUID) -> SecurityPolicy:
        """Ensure a SecurityPolicy row exists. SecurityPolicy.workspace_id is unique."""
        result = await self.session.execute(
            select(SecurityPolicy).where(SecurityPolicy.workspace_id == workspace_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        policy = SecurityPolicy(
            workspace_id=workspace_id,
            require_mfa=False,
            password_min_length=12,
            session_idle_timeout_minutes=60,
            max_concurrent_sessions=3,
        )
        self.session.add(policy)
        await self.session.flush()
        return policy

    async def _ensure_approval_policy(self, workspace_id: uuid.UUID) -> ApprovalPolicy:
        """Ensure at least one enabled ApprovalPolicy exists for this workspace."""
        result = await self.session.execute(
            select(ApprovalPolicy).where(
                ApprovalPolicy.workspace_id == workspace_id,
                ApprovalPolicy.enabled == True,  # noqa: E712
            )
        )
        existing = result.scalars().first()
        if existing:
            return existing

        policy = ApprovalPolicy(
            workspace_id=workspace_id,
            name="Default Action Approval Policy",
            description="Default policy requiring review of high-risk automated actions.",
            enabled=True,
            priority=100,
            matching_conditions=[{"field": "risk", "operator": "==", "value": "HIGH"}],
            stages=[{
                "stage_index": 0,
                "type": "single",
                "approver_ids": ["org_owner"],
                "required_count": 1,
            }],
            timeout_hours=48,
            require_segregation_of_duties=True,
        )
        self.session.add(policy)
        await self.session.flush()
        return policy


