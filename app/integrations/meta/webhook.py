"""
Meta webhook utilities — verification handshake and signature validation.

Meta sends an X-Hub-Signature-256 header on every webhook POST.
Verifying it ensures the request genuinely originates from Meta,
not a spoofed source.

Reference:
    https://developers.facebook.com/docs/graph-api/webhooks/getting-started
"""

import hashlib
import hmac
from typing import Optional

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def verify_hub_challenge(
    mode: Optional[str],
    token: Optional[str],
    challenge: Optional[str],
) -> Optional[str]:
    """
    Handle the Meta webhook verification GET handshake.

    Meta sends:  ?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
    We return:   hub.challenge as plain text (200 OK)
    On mismatch: return None (caller raises 403)
    """
    settings = get_settings()

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("webhook_verified", mode=mode)
        return challenge

    logger.warning(
        "webhook_verification_failed",
        mode=mode,
        token_matches=(token == settings.whatsapp_verify_token),
    )
    return None


def verify_webhook_signature(
    signature_header: Optional[str],
    raw_body: bytes,
) -> bool:
    """
    Validate the X-Hub-Signature-256 header from Meta.

    Uses HMAC-SHA256 with the WhatsApp access token as the secret.
    Always use hmac.compare_digest to prevent timing attacks.

    Returns True if the signature is valid, False otherwise.
    """
    settings = get_settings()

    if not signature_header or not signature_header.startswith("sha256="):
        logger.warning(
            "webhook_signature_missing_or_malformed",
            header_present=bool(signature_header),
        )
        return False

    received_sig = signature_header[7:]  # strip "sha256=" prefix

    expected_sig = hmac.new(
        settings.whatsapp_access_token.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    is_valid = hmac.compare_digest(received_sig, expected_sig)

    if not is_valid:
        logger.warning(
            "webhook_signature_invalid",
            received_prefix=received_sig[:8],
        )

    return is_valid
