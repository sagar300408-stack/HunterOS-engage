"""
Tests: Webhook verification and signature validation.

Covers:
1. Correct GET verification token returns the expected challenge.
2. Incorrect GET verification token is rejected.
3. Valid HMAC-SHA256 signature using the Meta App Secret is accepted.
4. Invalid signature is rejected.
5. Missing signature is rejected.
6. Missing App Secret is rejected.
7. A WhatsApp access token is never accepted as a substitute signing secret.
8. Verification logs do not expose tokens, secrets, or challenge values.
9. Invalid POST requests do not publish events.
10. Valid POST requests continue through the existing event pipeline.
"""

import hashlib
import hmac
import json
import logging
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.events.message_events import RawWebhookEvent
from app.events.model.actor_types import ActorType
from app.events.model.integration_types import IntegrationType
from app.application.context.interfaces import ResolvedContext
from app.integrations.meta.webhook import (
    verify_hub_challenge,
    verify_webhook_signature,
)
from app.integrations.postgres.database import get_db


class TestWebhookGetVerification:
    """Tests for the Meta hub.challenge handshake (Cases 1 & 2)."""

    def test_valid_verification_returns_challenge(self, client):
        """Case 1: Correct GET verification token returns the expected challenge."""
        with patch(
            "app.api.v1.webhook.verify_hub_challenge",
            return_value="challenge_abc123",
        ):
            response = client.get(
                "/api/v1/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "test_verify_token",
                    "hub.challenge": "challenge_abc123",
                },
            )
        assert response.status_code == 200
        assert response.text == "challenge_abc123"
        assert response.headers["content-type"].startswith("text/plain")

    def test_valid_verification_end_to_end(self, client, mock_settings):
        """Case 1 (E2E): Full GET flow with real verify_hub_challenge returning challenge."""
        with patch("app.integrations.meta.webhook.get_settings", return_value=mock_settings):
            response = client.get(
                "/api/v1/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": mock_settings.whatsapp_verify_token,
                    "hub.challenge": "challenge_e2e_123",
                },
            )
        assert response.status_code == 200
        assert response.text == "challenge_e2e_123"

    def test_get_verification_token_correct_unit(self, mock_settings):
        """Case 1 (Unit): verify_hub_challenge directly returns challenge on match."""
        with patch("app.integrations.meta.webhook.get_settings", return_value=mock_settings):
            result = verify_hub_challenge(
                mode="subscribe",
                token=mock_settings.whatsapp_verify_token,
                challenge="challenge_xyz789",
            )
            assert result == "challenge_xyz789"

    def test_invalid_token_returns_403(self, client):
        """Case 2: Incorrect GET verification token is rejected."""
        with patch(
            "app.api.v1.webhook.verify_hub_challenge",
            return_value=None,
        ):
            response = client.get(
                "/api/v1/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "wrong_token",
                    "hub.challenge": "any_challenge",
                },
            )
        assert response.status_code == 403

    def test_missing_params_returns_403(self, client):
        """Case 2 (Missing): Missing hub params returns 403."""
        with patch(
            "app.api.v1.webhook.verify_hub_challenge",
            return_value=None,
        ):
            response = client.get("/api/v1/webhook")
        assert response.status_code == 403

    def test_get_verification_token_incorrect_unit(self, mock_settings):
        """Case 2 (Unit): verify_hub_challenge returns None on mismatch or invalid mode."""
        with patch("app.integrations.meta.webhook.get_settings", return_value=mock_settings):
            assert verify_hub_challenge("subscribe", "wrong_token", "challenge_xyz") is None
            assert verify_hub_challenge("unsubscribe", mock_settings.whatsapp_verify_token, "challenge_xyz") is None
            assert verify_hub_challenge(None, mock_settings.whatsapp_verify_token, "challenge_xyz") is None


class TestWebhookSignatureUnit:
    """Tests for HMAC signature verification logic (Cases 3-8)."""

    def test_valid_hmac_signature_accepted(self, monkeypatch):
        """Case 3: Valid HMAC-SHA256 signature using the Meta App Secret is accepted."""
        secret = "test_meta_app_secret_12345"
        monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
        monkeypatch.delenv("META_APP_SECRET", raising=False)
        body = b'{"object":"whatsapp_business_account"}'
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        signature_header = f"sha256={digest}"

        assert verify_webhook_signature(signature_header, body) is True

    def test_valid_hmac_signature_fallback_meta_app_secret(self, monkeypatch):
        """Case 3 (Fallback): META_APP_SECRET accepted when WHATSAPP_APP_SECRET is not set."""
        secret = "test_fallback_secret_67890"
        monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
        monkeypatch.setenv("META_APP_SECRET", secret)
        body = b'{"object":"whatsapp_business_account"}'
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        signature_header = f"sha256={digest}"

        assert verify_webhook_signature(signature_header, body) is True

    def test_invalid_signature_rejected(self, monkeypatch):
        """Case 4: Invalid signature is rejected."""
        monkeypatch.setenv("WHATSAPP_APP_SECRET", "test_app_secret")
        body = b'{"object":"whatsapp_business_account"}'

        # Bad hash value
        assert verify_webhook_signature("sha256=0000000000000000000000000000000000000000000000000000000000000000", body) is False
        # Bad prefix
        assert verify_webhook_signature("sha1=badbadbad", body) is False
        # Missing prefix
        assert verify_webhook_signature("badbadbad", body) is False
        # Empty hash
        assert verify_webhook_signature("sha256=", body) is False

    def test_missing_signature_rejected(self, monkeypatch):
        """Case 5: Missing signature is rejected."""
        monkeypatch.setenv("WHATSAPP_APP_SECRET", "test_app_secret")
        body = b'{"object":"whatsapp_business_account"}'

        assert verify_webhook_signature(None, body) is False
        assert verify_webhook_signature("", body) is False

    def test_settings_model_reads_whatsapp_app_secret(self, monkeypatch):
        """Settings model correctly reads WHATSAPP_APP_SECRET."""
        monkeypatch.setenv("WHATSAPP_APP_SECRET", "model_test_secret_123")
        monkeypatch.delenv("META_APP_SECRET", raising=False)
        from app.config import Settings
        s = Settings()
        assert s.whatsapp_app_secret == "model_test_secret_123"

    def test_settings_model_reads_meta_app_secret_fallback(self):
        """Settings model falls back to META_APP_SECRET when WHATSAPP_APP_SECRET is unset."""
        from app.config import Settings
        s = Settings(WHATSAPP_APP_SECRET=None, META_APP_SECRET="model_fallback_secret_456")
        assert s.whatsapp_app_secret == "model_fallback_secret_456"

    def test_verifier_reads_app_secret_from_settings(self, monkeypatch):
        """Verifier reads App Secret from settings when os.environ is not directly set."""
        monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
        monkeypatch.delenv("META_APP_SECRET", raising=False)
        secret = "settings_configured_secret_789"
        mock_settings = MagicMock()
        mock_settings.whatsapp_app_secret = secret

        with patch("app.integrations.meta.webhook.get_settings", return_value=mock_settings):
            body = b'{"object":"whatsapp_business_account"}'
            digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            signature_header = f"sha256={digest}"

            assert verify_webhook_signature(signature_header, body) is True

    def test_missing_app_secret_rejected(self, monkeypatch):
        """Case 6: Missing App Secret is rejected when neither env nor settings has it."""
        monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
        monkeypatch.delenv("META_APP_SECRET", raising=False)
        mock_settings = MagicMock()
        mock_settings.whatsapp_app_secret = None

        with patch("app.integrations.meta.webhook.get_settings", return_value=mock_settings):
            body = b'{"object":"whatsapp_business_account"}'
            digest = hmac.new(b"some_secret", body, hashlib.sha256).hexdigest()

            assert verify_webhook_signature(f"sha256={digest}", body) is False

    def test_access_token_never_accepted_as_signing_secret(self, monkeypatch, mock_settings):
        """Case 7: A WhatsApp access token is never accepted as a substitute signing secret."""
        access_token = "EAABtestaccesstoken123456"
        app_secret = "real_app_secret_789"
        monkeypatch.setenv("WHATSAPP_APP_SECRET", app_secret)
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", access_token)
        mock_settings.whatsapp_access_token = access_token

        body = b'{"object":"whatsapp_business_account"}'
        token_digest = hmac.new(access_token.encode("utf-8"), body, hashlib.sha256).hexdigest()
        token_sig = f"sha256={token_digest}"

        # Signature calculated with access token must NOT match when app_secret is set
        assert verify_webhook_signature(token_sig, body) is False

        # Even when WHATSAPP_APP_SECRET is unset, access token must NEVER be used
        monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
        monkeypatch.delenv("META_APP_SECRET", raising=False)
        assert verify_webhook_signature(token_sig, body) is False

    def test_verification_logs_do_not_expose_sensitive_values(self, monkeypatch, caplog, mock_settings):
        """Case 8: Verification logs do not expose tokens, secrets, or challenge values."""
        sensitive_token = "SUPER_SECRET_VERIFY_TOKEN_999"
        sensitive_challenge = "SENSITIVE_CHALLENGE_STRING_888"
        sensitive_app_secret = "MY_TOP_SECRET_APP_KEY_777"
        sensitive_payload = b'{"sensitive_credit_card": "411111111111"}'
        received_sig = "sha256=11223344556677889900aabbccddeeff"

        mock_settings.whatsapp_verify_token = sensitive_token
        monkeypatch.setenv("WHATSAPP_APP_SECRET", sensitive_app_secret)

        with caplog.at_level(logging.DEBUG):
            with patch("app.integrations.meta.webhook.get_settings", return_value=mock_settings):
                verify_hub_challenge("subscribe", sensitive_token, sensitive_challenge)
                verify_hub_challenge("subscribe", "wrong_token_val", sensitive_challenge)

            verify_webhook_signature(received_sig, sensitive_payload)

        captured_text = caplog.text
        assert sensitive_token not in captured_text
        assert sensitive_challenge not in captured_text
        assert sensitive_app_secret not in captured_text
        assert "411111111111" not in captured_text
        assert "11223344556677889900aabbccddeeff" not in captured_text


class TestWebhookPost:
    """Tests for POST /api/v1/webhook (Cases 9 & 10)."""

    def test_invalid_post_does_not_publish_events(self, client, whatsapp_text_payload, monkeypatch):
        """Case 9: Invalid POST requests do not publish events and return 403."""
        monkeypatch.setenv("WHATSAPP_APP_SECRET", "test_app_secret")
        mock_event_bus = AsyncMock()
        client.app.state.event_bus = mock_event_bus

        # Missing signature header
        res_missing = client.post("/api/v1/webhook", json=whatsapp_text_payload)
        assert res_missing.status_code == 403
        assert res_missing.text == "Invalid webhook signature"
        mock_event_bus.publish.assert_not_called()

        # Invalid signature header
        res_invalid = client.post(
            "/api/v1/webhook",
            json=whatsapp_text_payload,
            headers={"X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000"},
        )
        assert res_invalid.status_code == 403
        assert res_invalid.text == "Invalid webhook signature"
        mock_event_bus.publish.assert_not_called()

    def test_valid_post_continues_through_pipeline(self, client, whatsapp_text_payload, monkeypatch):
        """Case 10: Valid POST requests continue through the existing event pipeline."""
        secret = "test_app_secret"
        monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)

        body_bytes = json.dumps(whatsapp_text_payload).encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        valid_sig = f"sha256={digest}"

        mock_event_bus = AsyncMock()
        client.app.state.event_bus = mock_event_bus

        mock_context = ResolvedContext(
            integration=IntegrationType.WHATSAPP,
            workspace_id=uuid.uuid4(),
            actor_type=ActorType.CUSTOMER,
            customer_id=uuid.uuid4(),
            lead_id=None,
            conversation_id=uuid.uuid4(),
        )
        mock_context_resolver = AsyncMock()
        mock_context_resolver.resolve.return_value = mock_context
        client.app.state.context_resolver = mock_context_resolver

        mock_session = AsyncMock()
        client.app.dependency_overrides[get_db] = lambda: mock_session

        try:
            response = client.post(
                "/api/v1/webhook",
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": valid_sig,
                },
            )

            assert response.status_code == 200
            assert response.json() == {"status": "ok", "processed": True}
            mock_event_bus.publish.assert_called_once()
            published_event = mock_event_bus.publish.call_args[0][1]
            assert isinstance(published_event, RawWebhookEvent)
            assert published_event.payload == whatsapp_text_payload
            mock_session.commit.assert_called_once()
        finally:
            client.app.dependency_overrides.pop(get_db, None)

    def test_non_whatsapp_payload_is_ignored(self, client, monkeypatch):
        """Payloads from other Meta products must be gracefully ignored when signature is valid."""
        secret = "test_app_secret"
        monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
        payload = {"object": "instagram", "entry": []}
        body_bytes = json.dumps(payload).encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

        response = client.post(
            "/api/v1/webhook",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={digest}",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"


class TestHealthCheck:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        data = client.get("/health").json()
        assert data["status"] == "healthy"
        assert data["service"] == "HunterOS Engage"
        assert data["version"] == "1.0.0"
        assert data["phase"] == 1
