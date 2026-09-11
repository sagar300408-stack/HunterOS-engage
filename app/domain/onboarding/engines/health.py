"""
OnboardingHealthEngine — R8/R9: Integration Health Checks

Evaluates the health of all configured integrations for a workspace.
Uses the existing connector registry (health_check()) rather than
creating a second health check mechanism.

Required vs Optional:
  - calendar integrations (google_calendar_v1, outlook_calendar_v1) are REQUIRED
    only if the workspace has scheduling/calendar capability enabled
  - communication integrations are REQUIRED for messaging
  - All other integrations: degraded but not blocking
"""
import uuid
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.integration.models import IntegrationConnection, ConnectionStatus
from app.domain.integration.credentials import JsonCredentialProvider
from app.domain.integration.connectors.registry import connector_registry
from app.domain.onboarding.models import OnboardingIntegrationConnection, IntegrationStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Connector types that are required for specific capabilities
CALENDAR_CONNECTORS = {"google_calendar_v1", "outlook_calendar_v1"}
COMMUNICATION_CONNECTORS = {"mock_email_v1", "mock_slack_v1"}  # extend as more are added


class OnboardingHealthEngine:
    """
    Evaluates integration health for a workspace during onboarding / readiness assessment.

    Uses the existing IntegrationConnection records and connector registry's
    health_check() method. Does not create a second health mechanism.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._cred_provider = JsonCredentialProvider()

    async def check_integrations(self, workspace_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Check health of all configured integrations for the workspace.

        Returns a list of health result dicts per integration:
        {
          "connector_id": str,
          "name": str,
          "status": "connected" | "degraded" | "error" | "disconnected",
          "health_detail": str,
          "required": bool,
        }
        """
        result = await self.session.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.workspace_id == workspace_id,
            )
        )
        connections = result.scalars().all()

        health_results = []
        for conn in connections:
            health_result = await self._check_single_integration(conn)
            health_results.append(health_result)

        logger.info(
            "integration_health_checked",
            workspace_id=str(workspace_id),
            total=len(health_results),
            healthy=sum(1 for r in health_results if r["status"] in ("connected", "degraded")),
        )
        return health_results

    async def has_required_integrations_healthy(
        self,
        workspace_id: uuid.UUID,
        required_connector_types: List[str],
    ) -> tuple[bool, str]:
        """
        Check whether all required integrations (by connector_type) are healthy.

        Returns (is_satisfied, explanation).
        """
        if not required_connector_types:
            return True, "No required integrations specified."

        results = await self.check_integrations(workspace_id)
        connected_types = {
            r["connector_type"] for r in results
            if r["status"] in ("connected", "degraded")
        }

        missing = [t for t in required_connector_types if t not in connected_types]
        if missing:
            return False, f"Required integrations not connected: {', '.join(missing)}"
        return True, "All required integrations are connected."

    # ── Private ───────────────────────────────────────────────────────────────

    async def _check_single_integration(self, conn: IntegrationConnection) -> Dict[str, Any]:
        """Run health_check on a single IntegrationConnection using the connector registry."""
        connector = connector_registry.get(conn.connector_id)
        if connector is None:
            return {
                "connector_id": conn.connector_id,
                "connector_type": conn.connector_type,
                "name": conn.name,
                "status": "error",
                "health_detail": f"Connector '{conn.connector_id}' not found in registry.",
                "required": False,
            }

        try:
            credentials = self._cred_provider.retrieve_credentials(conn)
            status, detail = connector.health_check(credentials, conn.settings or {})
            return {
                "connector_id": conn.connector_id,
                "connector_type": conn.connector_type,
                "name": conn.name,
                "status": status,
                "health_detail": detail or "OK",
                "required": False,
            }
        except Exception as exc:
            logger.warning(
                "integration_health_check_error",
                connector_id=conn.connector_id,
                error=str(exc),
            )
            return {
                "connector_id": conn.connector_id,
                "connector_type": conn.connector_type,
                "name": conn.name,
                "status": "error",
                "health_detail": f"Health check raised exception: {exc}",
                "required": False,
            }


