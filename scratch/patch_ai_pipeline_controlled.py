from pathlib import Path

path = Path("app/pipeline/ai.py")
content = path.read_text(encoding="utf-8")

old_block = """    # ── Call OpenAI conversational response ───────────────────────────────────
    import os
    t0 = time.monotonic()
    if os.environ.get("ENABLE_WHATSAPP_TEST_AUTO_REPLY", "").lower() == "true":
        logger.info(f"[WHATSAPP TEST] sending test response conversation_id={conversation_id}")
        ai_result = {
            "content": "Welcome to Originyx Business Automation Companies, India. THIS IS A TEST MESSAGE FROM originyx.in",
            "model": "test-mock-model",
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0,
            "estimated_cost_usd": 0.0,
            "finish_reason": "stop",
            "prompt_version": "v1"
        }
    else:
        ai_result = await get_ai_provider().get_ai_response(
            conversation_history=full_history,
            user_message=user_content,
        )
    t_ai = int((time.monotonic() - t0) * 1000)"""

new_block = """    # ── Controlled Test-Only Auto-Reply Check ─────────────────────────────────
    import os
    from app.utils.helpers import normalize_phone

    test_mode_enabled = (
        os.environ.get("ENABLE_WHATSAPP_TEST_AUTO_REPLY", "").lower() == "true"
        or os.environ.get("WHATSAPP_TEST_AUTO_REPLY", "").lower() == "true"
    )
    authorized_recipient = normalize_phone(os.environ.get("WHATSAPP_TEST_RECIPIENT_PHONE", "919108976764"))
    sender_phone = normalize_phone(customer.phone) if customer and customer.phone else ""
    is_authorized_recipient = bool(sender_phone and sender_phone == authorized_recipient)
    is_hi_message = bool(user_content and user_content.strip().lower() == "hi")

    # Verify event has not already been processed for this test
    is_test_already_processed = False
    if test_mode_enabled and is_authorized_recipient and is_hi_message:
        from sqlalchemy import select
        from app.events.store.models import EventRecord
        
        existing_event_stmt = select(EventRecord.event_id).where(
            EventRecord.causation_id == message_id,
            EventRecord.event_name.in_(["MessageReadyToSendEvent", "ReplySent", "AIResponded"]),
        ).limit(1)
        res = await session.execute(existing_event_stmt)
        if res.scalar_one_or_none() is not None:
            is_test_already_processed = True
            logger.info(
                "whatsapp_test_reply_already_processed",
                message_id=str(message_id),
                conversation_id=str(conversation_id),
            )

    is_test_reply_triggered = (
        test_mode_enabled
        and is_authorized_recipient
        and is_hi_message
        and not is_test_already_processed
    )

    t0 = time.monotonic()
    if is_test_reply_triggered:
        test_response_text = "TEST SUCCESSFULL, THIS WAS A TEST MESSAGE FROM HUNTEROS ENGAGE"
        logger.info(
            f"[WHATSAPP TEST] triggered controlled test response conversation_id={conversation_id} recipient={sender_phone}"
        )
        ai_result = {
            "content": test_response_text,
            "model": "test-controlled-response",
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0,
            "estimated_cost_usd": 0.0,
            "finish_reason": "stop",
            "prompt_version": "v1"
        }
    else:
        ai_result = await get_ai_provider().get_ai_response(
            conversation_history=full_history,
            user_message=user_content,
        )
    t_ai = int((time.monotonic() - t0) * 1000)"""

content_lf = content.replace("\r\n", "\n")
old_block_lf = old_block.replace("\r\n", "\n")
assert old_block_lf in content_lf, "old_block not found in ai.py"
content_lf = content_lf.replace(old_block_lf, new_block.replace("\r\n", "\n"), 1)

if "\r\n" in content:
    path.write_text(content_lf.replace("\n", "\r\n"), encoding="utf-8")
else:
    path.write_text(content_lf, encoding="utf-8")

print("Successfully patched app/pipeline/ai.py")
