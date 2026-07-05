# communication.py

async def process_whatsapp_pipeline(payload, session):
    result = await receive(payload, session)

    if result is None:
        return {"status": "ok", "processed": False}

    conversation, message_data, customer, message = result

    ai_result = await process_with_ai(
        conversation_id=conversation.id,
        message_id=message.id,
        customer=customer,
        user_content=message_data["content"],
        session=session,
    )

    await send_response(
        to_phone=message_data["from_phone"],
        conversation_id=conversation.id,
        ai_result=ai_result,
        session=session,
    )

    await schedule_followup(
        conversation_id=str(conversation.id),
        from_phone=message_data["from_phone"],
        ai_response=ai_result["content"],
    )

    return {
        "status": "ok",
        "processed": True,
    }