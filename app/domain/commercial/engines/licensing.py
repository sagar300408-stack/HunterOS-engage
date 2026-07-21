import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.commercial.models import License, LicenseStatus, Edition

logger = logging.getLogger("hunteros.commercial")

# Edition defaults: seat limits and feature entitlements per tier
EDITION_DEFAULTS: Dict[Edition, Dict[str, Any]] = {
    Edition.trial: {
        "seat_limit": 5,
        "entitlements": {
            "ai_recommendations": True,
            "integrations": 1,
            "friction_engine": True,
            "context_graph": False,
            "advanced_analytics": False,
            "sla_monitoring": False,
        }
    },
    Edition.starter: {
        "seat_limit": 25,
        "entitlements": {
            "ai_recommendations": True,
            "integrations": 3,
            "friction_engine": True,
            "context_graph": False,
            "advanced_analytics": False,
            "sla_monitoring": True,
        }
    },
    Edition.professional: {
        "seat_limit": 100,
        "entitlements": {
            "ai_recommendations": True,
            "integrations": 10,
            "friction_engine": True,
            "context_graph": True,
            "advanced_analytics": True,
            "sla_monitoring": True,
        }
    },
    Edition.enterprise: {
        "seat_limit": 9999,  # effectively unlimited
        "entitlements": {
            "ai_recommendations": True,
            "integrations": -1,     # unlimited
            "friction_engine": True,
            "context_graph": True,
            "advanced_analytics": True,
            "sla_monitoring": True,
            "custom_workflows": True,
            "dedicated_support": True,
        }
    },
}


class LicensingEngine:
    """
    Manages license generation, entitlement enforcement, and upgrade/downgrade operations.
    """

    @staticmethod
    async def provision_license(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        edition: Edition,
        trial_days: int = 0
    ) -> License:
        """
        Issues a new license for a workspace. Feature access is driven entirely by this record.
        """
        defaults = EDITION_DEFAULTS[edition]
        expires_at = None
        status = LicenseStatus.active

        if edition == Edition.trial or trial_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=trial_days or 30)
            status = LicenseStatus.trial

        license_record = License(
            workspace_id=workspace_id,
            edition=edition,
            status=status,
            seat_limit=defaults["seat_limit"],
            entitlements=defaults["entitlements"],
            expires_at=expires_at,
        )
        db.add(license_record)
        await db.commit()
        await db.refresh(license_record)
        logger.info(f"Provisioned {edition} license for workspace {workspace_id}")
        return license_record

    @staticmethod
    async def get_entitlements(db: AsyncSession, workspace_id: uuid.UUID) -> Dict[str, Any]:
        """
        Returns the current entitlements for a workspace. Always query this — never hardcode feature checks.
        """
        stmt = select(License).where(License.workspace_id == workspace_id)
        result = await db.execute(stmt)
        license_record = result.scalar_one_or_none()

        if not license_record or license_record.status in (LicenseStatus.expired, LicenseStatus.suspended):
            return {}  # No entitlements if license is invalid

        return license_record.entitlements

    @staticmethod
    async def upgrade_license(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        new_edition: Edition
    ) -> License:
        """
        Upgrades a workspace to a higher edition, applying new entitlements immediately.
        """
        stmt = select(License).where(License.workspace_id == workspace_id)
        result = await db.execute(stmt)
        license_record = result.scalar_one_or_none()

        if not license_record:
            raise ValueError(f"No license found for workspace {workspace_id}")

        defaults = EDITION_DEFAULTS[new_edition]
        license_record.edition = new_edition
        license_record.status = LicenseStatus.active
        license_record.seat_limit = defaults["seat_limit"]
        license_record.entitlements = defaults["entitlements"]
        license_record.expires_at = None  # Full licenses don't expire

        await db.commit()
        logger.info(f"Upgraded workspace {workspace_id} to {new_edition}")
        return license_record
