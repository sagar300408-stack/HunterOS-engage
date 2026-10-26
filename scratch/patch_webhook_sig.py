from pathlib import Path

path = Path("app/integrations/meta/webhook.py")
content = path.read_text(encoding="utf-8")

old_def = """def verify_webhook_signature(
    signature_header: Optional[str],
    raw_body: bytes,
) -> bool:
    \"\"\"
    Validate the X-Hub-Signature-256 header from Meta.

    Uses HMAC-SHA256 with the WhatsApp access token as the secret.
    Always use hmac.compare_digest to prevent timing attacks.

    Returns True if the signature is valid, False otherwise.
    \"\"\"
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

    return is_valid"""

new_def = """def verify_webhook_signature(
    signature_header: Optional[str],
    raw_body: bytes,
) -> bool:
    \"\"\"
    Validate the X-Hub-Signature-256 header from Meta.

    Uses HMAC-SHA256 with configured secret (WHATSAPP_APP_SECRET or WhatsApp access token).
    Always use hmac.compare_digest to prevent timing attacks.

    Returns True if the signature is valid, False otherwise.
    \"\"\"
    import os
    settings = get_settings()

    if not signature_header or not signature_header.startswith("sha256="):
        logger.warning(
            "webhook_signature_missing_or_malformed",
            header_present=bool(signature_header),
        )
        return False

    received_sig = signature_header[7:]  # strip "sha256=" prefix

    secrets_to_try = []
    app_secret = os.environ.get("WHATSAPP_APP_SECRET") or os.environ.get("META_APP_SECRET")
    if app_secret:
        secrets_to_try.append(app_secret)
    if settings.whatsapp_access_token:
        secrets_to_try.append(settings.whatsapp_access_token)

    for secret in secrets_to_try:
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        if hmac.compare_digest(received_sig, expected_sig):
            return True

    logger.warning(
        "webhook_signature_invalid",
        received_prefix=received_sig[:8],
    )
    return False"""

# Handle both CRLF and LF
content_lf = content.replace("\r\n", "\n")
old_def_lf = old_def.replace("\r\n", "\n")
assert old_def_lf in content_lf, "old_def not found in content"

new_content_lf = content_lf.replace(old_def_lf, new_def.replace("\r\n", "\n"))
if "\r\n" in content:
    path.write_text(new_content_lf.replace("\n", "\r\n"), encoding="utf-8")
else:
    path.write_text(new_content_lf, encoding="utf-8")

print("Successfully patched app/integrations/meta/webhook.py")
