"""
Tests: Webhook verification endpoint — GET /api/v1/webhook
"""

from unittest.mock import patch


class TestWebhookVerification:
    """Tests for the Meta hub.challenge handshake."""

    def test_valid_verification_returns_challenge(self, client):
        """A valid token and mode must echo back the hub.challenge."""
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

    def test_invalid_token_returns_403(self, client):
        """A wrong verify token must be rejected with 403."""
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
        """Missing hub params must result in a 403."""
        with patch(
            "app.api.v1.webhook.verify_hub_challenge",
            return_value=None,
        ):
            response = client.get("/api/v1/webhook")

        assert response.status_code == 403


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


class TestWebhookPost:
    """Tests for the POST /api/v1/webhook message handler."""

    def test_non_whatsapp_payload_is_ignored(self, client):
        """Payloads from other Meta products must be gracefully ignored."""
        response = client.post(
            "/api/v1/webhook",
            json={"object": "instagram", "entry": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    def test_valid_payload_returns_200(self, client, whatsapp_text_payload):
        """A valid WhatsApp payload must always return 200."""
        with (
            patch("app.api.v1.webhook.receive", return_value=None),
        ):
            response = client.post(
                "/api/v1/webhook",
                json=whatsapp_text_payload,
            )

        assert response.status_code == 200
