import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.api.v1.auth_deps import get_current_user
from app.domain.dashboard.models import User, UserRole

class TestDeveloperTools:
    def test_dev_tools_disabled_returns_404(self, mock_settings):
        """When ENABLE_DEVELOPER_TOOLS is false, endpoint must 404."""
        mock_settings.enable_developer_tools = False
        
        with (
            patch("app.config.get_settings", return_value=mock_settings),
            patch("app.integrations.postgres.database.create_tables"),
            patch("app.integrations.postgres.database.dispose_engine"),
        ):
            from app.main import create_app
            test_app = create_app()
            test_app.dependency_overrides[get_current_user] = lambda: User(role=UserRole.founder)
            
            with TestClient(test_app) as c:
                response = c.get("/api/v1/developer-tools/config")
                assert response.status_code == 404

    def test_dev_tools_enabled_unauthenticated_returns_401_or_403(self, mock_settings):
        """When ENABLE_DEVELOPER_TOOLS is true but no credentials, must fail auth dependency."""
        mock_settings.enable_developer_tools = True
        
        with (
            patch("app.config.get_settings", return_value=mock_settings),
            patch("app.integrations.postgres.database.create_tables"),
            patch("app.integrations.postgres.database.dispose_engine"),
        ):
            from app.main import create_app
            test_app = create_app()
            # Do not override get_current_user to simulate unauthenticated access
            
            with TestClient(test_app) as c:
                response = c.get("/api/v1/developer-tools/config")
                assert response.status_code in [401, 403]

    def test_dev_tools_non_founder_returns_403(self, mock_settings):
        """When ENABLE_DEVELOPER_TOOLS is true but user is not a Founder, must reject with 403."""
        mock_settings.enable_developer_tools = True
        
        with (
            patch("app.config.get_settings", return_value=mock_settings),
            patch("app.integrations.postgres.database.create_tables"),
            patch("app.integrations.postgres.database.dispose_engine"),
        ):
            from app.main import create_app
            test_app = create_app()
            test_app.dependency_overrides[get_current_user] = lambda: User(role=UserRole.sales)
            
            with TestClient(test_app) as c:
                response = c.get("/api/v1/developer-tools/config")
                assert response.status_code == 403

    def test_dev_tools_founder_succeeds(self, mock_settings):
        """When ENABLE_DEVELOPER_TOOLS is true and user is Founder, config query succeeds."""
        mock_settings.enable_developer_tools = True
        
        with (
            patch("app.config.get_settings", return_value=mock_settings),
            patch("app.integrations.postgres.database.create_tables"),
            patch("app.integrations.postgres.database.dispose_engine"),
        ):
            from app.main import create_app
            test_app = create_app()
            test_app.dependency_overrides[get_current_user] = lambda: User(role=UserRole.founder)
            
            with TestClient(test_app) as c:
                response = c.get("/api/v1/developer-tools/config")
                assert response.status_code == 200
                data = response.json()
                assert "openai_status" in data
                assert data["mock_ai"] is True

    def test_clock_offset_advances_simulated_time(self, mock_settings):
        """SystemClock.now() must reflect time jumps."""
        from app.utils.clock import SystemClock
        from app.developer_tools.service import simulation_state
        
        mock_settings.enable_developer_tools = True
        simulation_state.time_offset_seconds = 0
        
        t0 = SystemClock.now()
        simulation_state.time_offset_seconds = 3600
        
        t1 = SystemClock.now()
        diff = (t1 - t0).total_seconds()
        
        # Expect ~1 hour difference (allow minor system lag tolerance)
        assert 3590 < diff < 3610
        
        # Reset
        simulation_state.time_offset_seconds = 0
