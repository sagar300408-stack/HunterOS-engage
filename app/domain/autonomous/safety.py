from typing import Tuple
from datetime import datetime, timezone
import pytz

from app.domain.autonomous.models import PlanStep


class SafetyEnforcer:
    
    @staticmethod
    def evaluate_dispatch(step: PlanStep, workspace_settings: dict) -> Tuple[bool, str]:
        """
        Validation pipeline that evaluates whether a step is safe to dispatch.
        Returns (is_safe, reason).
        """
        # 1. Workspace Status
        if not workspace_settings.get("is_active", True):
            return False, "Workspace is currently inactive."

        # 2. Maintenance Window
        if workspace_settings.get("maintenance_mode", False):
            return False, "Workspace is in maintenance mode."

        # 3. Business Hours (example)
        # In a real system, we'd use timezone-aware checks against the workspace's configured business hours.
        # Here we mock a basic check for demonstration purposes if 'enforce_business_hours' is True.
        if workspace_settings.get("enforce_business_hours", False):
            now = datetime.now(pytz.UTC) # simplified, should use workspace TZ
            if now.weekday() >= 5: # 5=Sat, 6=Sun
                return False, "Outside business hours (weekend)."

        # 4. Quotas
        monthly_executions = workspace_settings.get("current_monthly_executions", 0)
        max_executions = workspace_settings.get("max_monthly_executions", 1000)
        if monthly_executions >= max_executions:
            return False, f"Monthly execution quota exceeded ({monthly_executions}/{max_executions})."

        # 5. Concurrency
        current_concurrent = workspace_settings.get("current_concurrent_plans", 0)
        max_concurrent = workspace_settings.get("max_concurrent_plans", 10)
        if current_concurrent >= max_concurrent:
            return False, f"Concurrency limit exceeded ({current_concurrent}/{max_concurrent})."

        # 6. Retry Budget (per step)
        attempts = step.inputs.get("_attempts", 0)
        max_retries = step.retry_policy.get("max_retries", 3)
        if attempts >= max_retries:
            return False, f"Retry budget exceeded ({attempts}/{max_retries})."

        return True, "Safety checks passed."
