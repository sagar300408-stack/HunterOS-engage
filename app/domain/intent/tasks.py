import asyncio
from uuid import UUID
from datetime import datetime
from app.celery_app import celery_app
from app.integrations.postgres.database import get_session
from app.utils.logger import get_logger

logger = get_logger(__name__)

@celery_app.task(bind=True, name="app.domain.intent.tasks.retry_intent_extraction", max_retries=3, default_retry_delay=10)
def retry_intent_extraction(
    self, 
    customer_id_str: str, 
    conversation_id_str: str, 
    message_id_str: str, 
    user_content: str, 
    conversation_history: list, 
    memory_summary: str,
    workspace_id_str: str = None
):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    async def _run():
        from app.domain.intent.service import _call_intent_extraction_api, _map_intent_to_action, _safe_intent, _safe_urgency
        from app.domain.intent.models import IntentHistory, IntentDLQ
        from app.domain.customers import service as customer_service
        from app.domain.intent.schemas import IntentResult
        
        async with get_session() as session:
            try:
                result_dict = await _call_intent_extraction_api(
                    user_content,
                    conversation_history,
                    memory_summary,
                    workspace_id_str,
                    throw_on_error=True
                )
                
                # Update IntentHistory
                from sqlalchemy import update
                
                intent_enum = _safe_intent(result_dict.get("intent", "other"))
                urgency_enum = _safe_urgency(result_dict.get("urgency", "unknown"))
                buying_stage = result_dict.get("buying_stage")
                next_action = _map_intent_to_action(intent_enum, urgency_enum, buying_stage)
                
                stmt = (
                    update(IntentHistory)
                    .where(IntentHistory.message_id == UUID(message_id_str))
                    .values(
                        detected_intent=intent_enum,
                        confidence=result_dict.get("confidence", 0.0),
                        budget=str(result_dict.get("budget", {}).get("value")) if result_dict.get("budget") else None,
                        timeline=str(result_dict.get("timeline", {}).get("value")) if result_dict.get("timeline") else None,
                        interest=str(result_dict.get("interest", {}).get("value")) if result_dict.get("interest") else None,
                        location=str(result_dict.get("location", {}).get("value")) if result_dict.get("location") else None,
                        urgency=urgency_enum,
                        buying_stage=buying_stage,
                        next_action=next_action,
                        is_fallback=False,
                        extracted_json=result_dict,
                        reasoning=result_dict.get("reasoning"),
                        memory_influenced=result_dict.get("memory_influenced"),
                        detected_keywords=result_dict.get("detected_keywords")
                    )
                )
                await session.execute(stmt)
                
                if buying_stage:
                    await customer_service.update_buying_stage(
                        session=session,
                        customer_id=UUID(customer_id_str),
                        buying_stage=buying_stage,
                    )
                await session.commit()
            except Exception as e:
                is_transient = "timeout" in str(e).lower() or "connection" in str(e).lower() or "rate" in str(e).lower()
                if is_transient and self.request.retries < self.max_retries:
                    raise self.retry(exc=e)
                else:
                    # DLQ
                    dlq = IntentDLQ(
                        workspace_id=UUID(workspace_id_str) if workspace_id_str else None,
                        customer_id=UUID(customer_id_str),
                        conversation_id=UUID(conversation_id_str),
                        message_id=UUID(message_id_str),
                        payload={
                            "user_content": user_content,
                            "conversation_history": conversation_history,
                            "memory_summary": memory_summary
                        },
                        error_message=str(e)
                    )
                    session.add(dlq)
                    await session.commit()

    loop.run_until_complete(_run())
