from pathlib import Path

path = Path("app/api/v1/webhook.py")
content = path.read_text(encoding="utf-8")

old_part = """from app.integrations.meta.webhook import verify_hub_challenge"""
new_part = """from app.integrations.meta.webhook import verify_hub_challenge, verify_webhook_signature
import json"""

content_lf = content.replace("\r\n", "\n")
old_part_lf = old_part.replace("\r\n", "\n")
assert old_part_lf in content_lf, "import target not found"
content_lf = content_lf.replace(old_part_lf, new_part.replace("\r\n", "\n"), 1)

old_body = """    try:
        payload = await request.json()
        if payload.get("is_demo"):
            is_demo_context.set(True)

        logger.info("[WHATSAPP INBOUND] webhook received")"""

new_body = """    try:
        raw_body = await request.body()
        signature_header = request.headers.get("X-Hub-Signature-256") or request.headers.get("x-hub-signature-256")
        if signature_header:
            if not verify_webhook_signature(signature_header, raw_body):
                logger.warning(
                    "webhook_signature_verification_failed",
                    received_prefix=signature_header[:16] if signature_header else None,
                )
                return Response(status_code=403, content="Invalid webhook signature")
            logger.info("[WHATSAPP INBOUND] signature verified successfully")

        payload = json.loads(raw_body) if raw_body else {}
        if payload.get("is_demo"):
            is_demo_context.set(True)

        logger.info("[WHATSAPP INBOUND] webhook received")"""

old_body_lf = old_body.replace("\r\n", "\n")
assert old_body_lf in content_lf, "body target not found"
content_lf = content_lf.replace(old_body_lf, new_body.replace("\r\n", "\n"), 1)

if "\r\n" in content:
    path.write_text(content_lf.replace("\n", "\r\n"), encoding="utf-8")
else:
    path.write_text(content_lf, encoding="utf-8")

print("Successfully patched app/api/v1/webhook.py")
