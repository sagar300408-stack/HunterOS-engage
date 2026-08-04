import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.domain.scheduling.schemas import CreateEventRequest
from app.domain.security.models import User
from app.api.v1.auth_deps import get_current_user
from app.integrations.postgres.database import get_db_session


def test_schema_timezone_aware_datetime():
    req = CreateEventRequest(
        event_type="meeting",
        title="Test",
        scheduled_for="2026-07-24T14:25:00+05:30"
    )
    assert req.scheduled_for.tzinfo is not None
    assert req.scheduled_for.isoformat().endswith("+00:00")


def test_schema_utc_datetime():
    req = CreateEventRequest(
        event_type="meeting",
        title="Test",
        scheduled_for="2026-07-24T14:25:00Z"
    )
    assert req.scheduled_for.tzinfo is not None


def test_schema_naive_datetime():
    with pytest.raises(ValidationError) as exc_info:
        CreateEventRequest(
            event_type="meeting",
            title="Test",
            scheduled_for="2026-07-24T14:25:00"
        )
    assert "Input should have timezone info" in str(exc_info.value)


def test_schema_invalid_datetime_format():
    with pytest.raises(ValidationError):
        CreateEventRequest(
            event_type="meeting",
            title="Test",
            scheduled_for="not-a-datetime"
        )


def test_api_naive_datetime_returns_422():
    """
    POST /api/v1/scheduling/events with a naive datetime must return HTTP 422.
    """
    mock_settings = MagicMock()
    mock_settings.whatsapp_verify_token = "x"
    mock_settings.whatsapp_access_token = "x"
    mock_settings.whatsapp_phone_number_id = "1"
    mock_settings.whatsapp_api_version = "v20.0"
    mock_settings.openai_api_key = "sk-test"
    mock_settings.openai_model = "gpt-4o"
    mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
    mock_settings.app_env = "testing"
    mock_settings.log_level = "DEBUG"
    mock_settings.active_prompt_version = "v1"
    mock_settings.is_production = False
    mock_settings.is_development = False

    with (
        patch("app.config.get_settings", return_value=mock_settings),
        patch("app.main.get_settings", return_value=mock_settings),
        patch("app.main.create_tables", new=AsyncMock()),
        patch("app.main.dispose_engine", new=AsyncMock()),
        patch("app.integrations.postgres.database.create_tables", new=AsyncMock()),
        patch("app.integrations.postgres.database.dispose_engine", new=AsyncMock()),
    ):
        from app.main import create_app
        test_app = create_app()

        # Build a mock user; patch role_can to always return True
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.workspace_id = uuid4()
        mock_user.is_active = True

        async def _mock_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = _mock_get_current_user

        with (
            patch("app.api.v1.auth_deps.role_can", return_value=True),
            TestClient(test_app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/api/v1/scheduling/events",
                headers={"Authorization": "Bearer dummy-token-for-test"},
                json={
                    "event_type": "meeting",
                    "title": "Naive test",
                    "scheduled_for": "2026-07-24T14:25:00",  # no tz offset → 422
                },
            )

        test_app.dependency_overrides.clear()

        assert response.status_code == 422, (
            f"Expected 422 for naive datetime, got {response.status_code}: {response.text}"
        )
        body = response.text.lower()
        assert "timezone" in body or "input should have timezone info" in body
