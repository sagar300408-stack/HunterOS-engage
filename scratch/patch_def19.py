path = 'app/domain/integration/consumers/whatsapp_send_consumer.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''        try:
            # ── Send via WhatsApp ─────────────────────────────────────────────────────
            wa_message_id = await self.whatsapp_provider.send_text_message(
                to=event.to_phone, 
                body=event.content
            )

            logger.info(
                f"reply_sent to_phone={event.to_phone} wa_message_id={wa_message_id} reply_to_id={event.response_message_id}"
            )
            
            # Additional log for test verification
            if "THIS IS A TEST MESSAGE" in event.content:
                logger.info(f"[WHATSAPP TEST] response sent successfully wa_message_id={wa_message_id}")

            async with get_session() as session:
                reply_event = ReplySent(
                    workspace_id=event.workspace_id,
                    actor_type=event.actor_type,
                    correlation_id=event.correlation_id,
                    to_phone=event.to_phone,
                    content=event.content,
                    wa_message_id=wa_message_id,
                )
                
                from app.events.store.service import EventStoreService
                from app.events.store.repository import EventStoreRepository
                from app.events.bus.event_bus import EventBus
                
                local_bus = EventBus(EventStoreService(EventStoreRepository()))
                await local_bus.publish(session, reply_event)
                await session.commit()
                
        except Exception as e:
            logger.error(f"whatsapp_send_error: {str(e)}")
            # Publish ErrorOccurred
            async with get_session() as session:
                error_event = ErrorOccurred(
                    workspace_id=event.workspace_id,
                    actor_type=event.actor_type,
                    correlation_id=event.correlation_id,
                    stage="whatsapp_send",
                    error_message=str(e),
                    error_type=type(e).__name__,
                    from_phone=event.to_phone
                )
                from app.events.store.service import EventStoreService
                from app.events.store.repository import EventStoreRepository
                from app.events.bus.event_bus import EventBus
                
                local_bus = EventBus(EventStoreService(EventStoreRepository()))
                await local_bus.publish(session, error_event)
                await session.commit()
            raise'''

replacement = '''        wa_message_id = None
        try:
            # ── 1. Send via WhatsApp Provider ─────────────────────────────────────────
            wa_message_id = await self.whatsapp_provider.send_text_message(
                to=event.to_phone, 
                body=event.content
            )

            logger.info(
                f"reply_sent to_phone={event.to_phone} wa_message_id={wa_message_id} correlation_id={event.correlation_id}"
            )
            
            # Additional log for test verification
            if "THIS IS A TEST MESSAGE" in event.content:
                logger.info(f"[WHATSAPP TEST] response sent successfully wa_message_id={wa_message_id}")

        except Exception as e:
            # Provider failure: message was NOT sent. Record ErrorOccurred and re-raise for retry.
            logger.error(f"whatsapp_send_error: {str(e)}")
            try:
                async with get_session() as session:
                    error_event = ErrorOccurred(
                        workspace_id=event.workspace_id,
                        actor_type=event.actor_type,
                        correlation_id=event.correlation_id,
                        stage="whatsapp_send",
                        error_message=str(e),
                        error_type=type(e).__name__,
                        from_phone=event.to_phone
                    )
                    from app.events.store.service import EventStoreService
                    from app.events.store.repository import EventStoreRepository
                    from app.events.bus.event_bus import EventBus
                    
                    local_bus = EventBus(EventStoreService(EventStoreRepository()))
                    await local_bus.publish(session, error_event)
                    await session.commit()
            except Exception as store_err:
                logger.error(f"failed_to_publish_error_event: {store_err}")
            raise

        # ── 2. Post-delivery event publication ────────────────────────────────────────
        # The external message has already been accepted by Meta (wa_message_id is known).
        # Any subsequent failure in publishing ReplySent must NOT re-raise to Celery/caller,
        # avoiding unexamined duplicate message sends on worker retries.
        try:
            async with get_session() as session:
                reply_event = ReplySent(
                    workspace_id=event.workspace_id,
                    actor_type=event.actor_type,
                    correlation_id=event.correlation_id,
                    to_phone=event.to_phone,
                    content=event.content,
                    wa_message_id=wa_message_id,
                )
                
                from app.events.store.service import EventStoreService
                from app.events.store.repository import EventStoreRepository
                from app.events.bus.event_bus import EventBus
                
                local_bus = EventBus(EventStoreService(EventStoreRepository()))
                await local_bus.publish(session, reply_event)
                await session.commit()
        except Exception as post_err:
            logger.error(
                f"whatsapp_post_send_event_error: External message sent (wa_message_id={wa_message_id}) "
                f"but failed to record ReplySent: {post_err}",
                exc_info=True
            )'''

assert target in content, "Target block not found in whatsapp_send_consumer.py"
content = content.replace(target, replacement, 1)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Applied DEF-19 patch to app/domain/integration/consumers/whatsapp_send_consumer.py successfully.")
