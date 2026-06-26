"""
Pytest configuration and shared fixtures for HunterOS Engage tests.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="session")
def mock_settings():
    """Return a mock Settings object with safe test values."""
    settings = MagicMock()
    settings.whatsapp_verify_token = "test_verify_token"
    settings.whatsapp_access_token = "test_access_token"
    settings.whatsapp_phone_number_id = "123456789"
    settings.whatsapp_api_version = "v20.0"
    settings.openai_api_key = "sk-test"
    settings.openai_model = "gpt-4o"
    settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
    settings.app_env = "testing"
    settings.log_level = "DEBUG"
    settings.active_prompt_version = "v1"
    settings.is_production = False
    settings.is_development = False
    return settings


@pytest.fixture
def client(mock_settings):
    """
    Return a FastAPI TestClient with settings and DB patched out.
    Skips the lifespan (no DB connection required for unit tests).
    """
    with (
        patch("app.config.get_settings", return_value=mock_settings),
        patch("app.integrations.postgres.database.create_tables"),
        patch("app.integrations.postgres.database.dispose_engine"),
    ):
        from app.main import create_app
        test_app = create_app()

    # TestClient runs without triggering async lifespan by default
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def whatsapp_text_payload():
    """Return a valid Meta WhatsApp text message webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry_id_123",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "919876543210",
                                "phone_number_id": "123456789",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test Customer"},
                                    "wa_id": "919876543210",
                                }
                            ],
                            "messages": [
                                {
                                    "id": "wamid.test_unique_id_001",
                                    "from": "919876543210",
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": "Hello, I need help with my order."},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
