import pathlib

def replace_all():
    p = pathlib.Path("app/domain/dashboard/service.py")
    content = p.read_text(encoding="utf-8")
    
    # get_overview_metrics
    content = content.replace(
        "    total_customers = await session.scalar(select(func.count(Customer.id)))",
        "    total_customers = await session.scalar(select(func.count(Customer.id)).where(Customer.workspace_id == workspace_id))"
    )
    content = content.replace(
        "    new_today = await session.scalar(\n        select(func.count(Customer.id)).where(Customer.created_at >= today_start)\n    )",
        "    new_today = await session.scalar(\n        select(func.count(Customer.id)).where(Customer.workspace_id == workspace_id, Customer.created_at >= today_start)\n    )"
    )
    content = content.replace(
        "    qualified = await session.scalar(\n        select(func.count(Customer.id)).where(\n            Customer.buying_stage.notin_([\"Research\", None])\n        )\n    )",
        "    qualified = await session.scalar(\n        select(func.count(Customer.id)).where(\n            Customer.workspace_id == workspace_id,\n            Customer.buying_stage.notin_([\"Research\", None])\n        )\n    )"
    )
    content = content.replace(
        "    purchase_ready = await session.scalar(\n        select(func.count(Customer.id)).where(\n            Customer.buying_stage == \"Purchase Ready\"\n        )\n    )",
        "    purchase_ready = await session.scalar(\n        select(func.count(Customer.id)).where(\n            Customer.workspace_id == workspace_id,\n            Customer.buying_stage == \"Purchase Ready\"\n        )\n    )"
    )
    content = content.replace(
        "    active_convos = await session.scalar(\n        select(func.count(func.distinct(Message.conversation_id))).where(\n            Message.timestamp >= cutoff\n        )\n    )",
        "    active_convos = await session.scalar(\n        select(func.count(func.distinct(Message.conversation_id)))\n        .join(Conversation, Message.conversation_id == Conversation.id)\n        .where(\n            Conversation.workspace_id == workspace_id,\n            Message.timestamp >= cutoff\n        )\n    )"
    )
    content = content.replace(
        "    avg_latency = await session.scalar(\n        select(func.avg(AIMetadata.latency_ms)).where(\n            AIMetadata.latency_ms.isnot(None)\n        )\n    )",
        "    avg_latency = await session.scalar(\n        select(func.avg(AIMetadata.latency_ms))\n        .join(Message, AIMetadata.message_id == Message.id)\n        .join(Conversation, Message.conversation_id == Conversation.id)\n        .where(\n            Conversation.workspace_id == workspace_id,\n            AIMetadata.latency_ms.isnot(None)\n        )\n    )"
    )
    content = content.replace(
        "    total_ai = await session.scalar(select(func.count(AIMetadata.id)))",
        "    total_ai = await session.scalar(\n        select(func.count(AIMetadata.id))\n        .join(Message, AIMetadata.message_id == Message.id)\n        .join(Conversation, Message.conversation_id == Conversation.id)\n        .where(Conversation.workspace_id == workspace_id)\n    )"
    )
    content = content.replace(
        "    success_ai = await session.scalar(\n        select(func.count(AIMetadata.id)).where(AIMetadata.finish_reason == \"stop\")\n    )",
        "    success_ai = await session.scalar(\n        select(func.count(AIMetadata.id))\n        .join(Message, AIMetadata.message_id == Message.id)\n        .join(Conversation, Message.conversation_id == Conversation.id)\n        .where(\n            Conversation.workspace_id == workspace_id,\n            AIMetadata.finish_reason == \"stop\"\n        )\n    )"
    )
    content = content.replace(
        "    mem_updates = await session.scalar(\n        select(func.count(CustomerMemoryEvent.id)).where(\n            CustomerMemoryEvent.created_at >= today_start,\n            CustomerMemoryEvent.event_type == \"memory_summarized\",\n        )\n    )",
        "    mem_updates = await session.scalar(\n        select(func.count(CustomerMemoryEvent.id))\n        .join(Customer, CustomerMemoryEvent.customer_id == Customer.id)\n        .where(\n            Customer.workspace_id == workspace_id,\n            CustomerMemoryEvent.created_at >= today_start,\n            CustomerMemoryEvent.event_type == \"memory_summarized\",\n        )\n    )"
    )
    content = content.replace(
        "    cost_today = await session.scalar(\n        select(func.sum(AIMetadata.estimated_cost_usd)).join(\n            Message, AIMetadata.message_id == Message.id\n        ).where(Message.timestamp >= today_start)\n    )",
        "    cost_today = await session.scalar(\n        select(func.sum(AIMetadata.estimated_cost_usd)).join(\n            Message, AIMetadata.message_id == Message.id\n        ).join(Conversation, Message.conversation_id == Conversation.id).where(\n            Conversation.workspace_id == workspace_id,\n            Message.timestamp >= today_start\n        )\n    )"
    )
    content = content.replace(
        "            select(func.count(ScheduledEvent.id)).where(\n                ScheduledEvent.status.in_([\"pending\", \"confirmed\"]),\n                ScheduledEvent.scheduled_for >= today_start\n            )",
        "            select(func.count(ScheduledEvent.id))\n            .join(Customer, ScheduledEvent.customer_id == Customer.id)\n            .where(\n                Customer.workspace_id == workspace_id,\n                ScheduledEvent.status.in_([\"pending\", \"confirmed\"]),\n                ScheduledEvent.scheduled_for >= today_start\n            )"
    )
    content = content.replace(
        "            select(func.count(ScheduledEvent.id)).where(\n                ScheduledEvent.status == \"pending\",\n                ScheduledEvent.event_type == \"callback\"\n            )",
        "            select(func.count(ScheduledEvent.id))\n            .join(Customer, ScheduledEvent.customer_id == Customer.id)\n            .where(\n                Customer.workspace_id == workspace_id,\n                ScheduledEvent.status == \"pending\",\n                ScheduledEvent.event_type == \"callback\"\n            )"
    )
    content = content.replace(
        "            select(func.count(FollowUpQueue.id)).where(\n                FollowUpQueue.status.in_([\"scheduled\", \"executing\"])\n            )",
        "            select(func.count(FollowUpQueue.id))\n            .join(Customer, FollowUpQueue.customer_id == Customer.id)\n            .where(\n                Customer.workspace_id == workspace_id,\n                FollowUpQueue.status.in_([\"scheduled\", \"executing\"])\n            )"
    )

    # get_conversations
    content = content.replace(
        "    base_q = (\n        select(Conversation)\n        .options(selectinload(Conversation.messages), selectinload(Conversation.customer))\n        .order_by(Conversation.created_at.desc())\n    )",
        "    base_q = (\n        select(Conversation)\n        .options(selectinload(Conversation.messages), selectinload(Conversation.customer))\n        .where(Conversation.workspace_id == workspace_id)\n        .order_by(Conversation.created_at.desc())\n    )"
    )

    # get_conversation_detail
    content = content.replace(
        "async def get_conversation_detail(\n    session: AsyncSession,\n    conversation_id: UUID,\n) -> Optional[ConversationDetail]:\n    result = await session.execute(\n        select(Conversation)\n        .where(Conversation.id == conversation_id)",
        "async def get_conversation_detail(\n    session: AsyncSession,\n    conversation_id: UUID,\n    workspace_id: UUID,\n) -> Optional[ConversationDetail]:\n    result = await session.execute(\n        select(Conversation)\n        .where(Conversation.id == conversation_id, Conversation.workspace_id == workspace_id)"
    )

    # get_customers
    content = content.replace(
        "    q = select(Customer).order_by(Customer.created_at.desc())",
        "    q = select(Customer).where(Customer.workspace_id == workspace_id).order_by(Customer.created_at.desc())"
    )

    # get_customer_profile
    content = content.replace(
        "async def get_customer_profile(\n    session: AsyncSession,\n    customer_id: UUID,\n) -> Optional[CustomerProfile]:\n    result = await session.execute(\n        select(Customer)\n        .where(Customer.id == customer_id)",
        "async def get_customer_profile(\n    session: AsyncSession,\n    customer_id: UUID,\n    workspace_id: UUID,\n) -> Optional[CustomerProfile]:\n    result = await session.execute(\n        select(Customer)\n        .where(Customer.id == customer_id, Customer.workspace_id == workspace_id)"
    )

    # update_customer
    content = content.replace(
        "    result = await session.execute(select(Customer).where(Customer.id == customer_id))\n    customer = result.scalar_one_or_none()",
        "    result = await session.execute(select(Customer).where(Customer.id == customer_id, Customer.workspace_id == workspace_id))\n    customer = result.scalar_one_or_none()"
    )

    # get_lead_pipeline
    content = content.replace(
        "    result = await session.execute(\n        select(Customer).where(Customer.buying_stage.isnot(None))\n    )",
        "    result = await session.execute(\n        select(Customer).where(Customer.workspace_id == workspace_id, Customer.buying_stage.isnot(None))\n    )"
    )

    # update_lead_stage
    content = content.replace(
        "async def update_lead_stage(\n    session: AsyncSession,\n    customer_id: UUID,\n    new_stage: str,\n    actor_user_id: Optional[UUID] = None,\n    reason: Optional[str] = None,\n    ip_address: Optional[str] = None,\n    workspace_id: Optional[UUID] = None,\n) -> None:\n    result = await session.execute(select(Customer).where(Customer.id == customer_id))\n    customer = result.scalar_one_or_none()",
        "async def update_lead_stage(\n    session: AsyncSession,\n    customer_id: UUID,\n    new_stage: str,\n    actor_user_id: Optional[UUID] = None,\n    reason: Optional[str] = None,\n    ip_address: Optional[str] = None,\n    workspace_id: Optional[UUID] = None,\n) -> None:\n    result = await session.execute(select(Customer).where(Customer.id == customer_id, Customer.workspace_id == workspace_id))\n    customer = result.scalar_one_or_none()"
    )

    # get_analytics
    content = content.replace(
        "        .where(Conversation.created_at.between(from_dt, to_dt))\n        .group_by(text(\"day\"))",
        "        .where(Conversation.workspace_id == workspace_id, Conversation.created_at.between(from_dt, to_dt))\n        .group_by(text(\"day\"))"
    )
    content = content.replace(
        "        .where(Customer.created_at.between(from_dt, to_dt))\n        .group_by(text(\"day\"))",
        "        .where(Customer.workspace_id == workspace_id, Customer.created_at.between(from_dt, to_dt))\n        .group_by(text(\"day\"))"
    )
    content = content.replace(
        "        .where(IntentHistory.created_at.between(from_dt, to_dt))\n        .group_by(IntentHistory.detected_intent)",
        "        .where(IntentHistory.workspace_id == workspace_id, IntentHistory.created_at.between(from_dt, to_dt))\n        .group_by(IntentHistory.detected_intent)"
    )
    content = content.replace(
        "        .where(Message.timestamp.between(from_dt, to_dt))\n        .group_by(text(\"day\"))",
        "        .where(Conversation.workspace_id == workspace_id, Message.timestamp.between(from_dt, to_dt))\n        .group_by(text(\"day\"))"
    )
    content = content.replace(
        "        .where(Message.timestamp.between(from_dt, to_dt))\n    )",
        "        .where(Conversation.workspace_id == workspace_id, Message.timestamp.between(from_dt, to_dt))\n    )"
    )
    content = content.replace(
        "    total_customers_period = await session.scalar(\n        select(func.count(Customer.id)).where(Customer.created_at.between(from_dt, to_dt))\n    ) or 1",
        "    total_customers_period = await session.scalar(\n        select(func.count(Customer.id)).where(Customer.workspace_id == workspace_id, Customer.created_at.between(from_dt, to_dt))\n    ) or 1"
    )
    content = content.replace(
        "    qualified_period = await session.scalar(\n        select(func.count(Customer.id)).where(\n            Customer.created_at.between(from_dt, to_dt),\n            Customer.buying_stage.notin_([\"Research\", None]),\n        )\n    ) or 1",
        "    qualified_period = await session.scalar(\n        select(func.count(Customer.id)).where(\n            Customer.workspace_id == workspace_id,\n            Customer.created_at.between(from_dt, to_dt),\n            Customer.buying_stage.notin_([\"Research\", None]),\n        )\n    ) or 1"
    )

    # get_activity_feed
    content = content.replace(
        "    result = await session.execute(\n        select(CustomerMemoryEvent)\n        .order_by(CustomerMemoryEvent.created_at.desc())\n        .limit(limit)\n    )",
        "    result = await session.execute(\n        select(CustomerMemoryEvent)\n        .join(Customer, CustomerMemoryEvent.customer_id == Customer.id)\n        .where(Customer.workspace_id == workspace_id)\n        .order_by(CustomerMemoryEvent.created_at.desc())\n        .limit(limit)\n    )"
    )

    # get_queue_status
    content = content.replace(
        "    pending  = await session.scalar(select(func.count(BackgroundJob.id)).where(BackgroundJob.status == JobStatus.pending))",
        "    pending  = await session.scalar(select(func.count(BackgroundJob.id)).where(BackgroundJob.workspace_id == workspace_id, BackgroundJob.status == JobStatus.pending))"
    )
    content = content.replace(
        "    running  = await session.scalar(select(func.count(BackgroundJob.id)).where(BackgroundJob.status == JobStatus.running))",
        "    running  = await session.scalar(select(func.count(BackgroundJob.id)).where(BackgroundJob.workspace_id == workspace_id, BackgroundJob.status == JobStatus.running))"
    )
    content = content.replace(
        "    failed   = await session.scalar(select(func.count(BackgroundJob.id)).where(BackgroundJob.status == JobStatus.failed))",
        "    failed   = await session.scalar(select(func.count(BackgroundJob.id)).where(BackgroundJob.workspace_id == workspace_id, BackgroundJob.status == JobStatus.failed))"
    )
    content = content.replace(
        "    done_today = await session.scalar(\n        select(func.count(BackgroundJob.id)).where(\n            BackgroundJob.status == JobStatus.completed,\n            BackgroundJob.completed_at >= today_start,\n        )\n    )",
        "    done_today = await session.scalar(\n        select(func.count(BackgroundJob.id)).where(\n            BackgroundJob.workspace_id == workspace_id,\n            BackgroundJob.status == JobStatus.completed,\n            BackgroundJob.completed_at >= today_start,\n        )\n    )"
    )
    content = content.replace(
        "    recent_jobs_result = await session.execute(\n        select(BackgroundJob).order_by(BackgroundJob.scheduled_at.desc()).limit(20)\n    )",
        "    recent_jobs_result = await session.execute(\n        select(BackgroundJob).where(BackgroundJob.workspace_id == workspace_id).order_by(BackgroundJob.scheduled_at.desc()).limit(20)\n    )"
    )

    # get_audit_log
    content = content.replace(
        "    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)",
        "    q = select(AuditLog).where(AuditLog.workspace_id == workspace_id).order_by(AuditLog.created_at.desc()).limit(limit)"
    )

    # search_everything
    content = content.replace(
        "    customer_rows = await session.execute(\n        select(Customer).where(\n            or_(\n                Customer.name.ilike(pattern),",
        "    customer_rows = await session.execute(\n        select(Customer).where(\n            Customer.workspace_id == workspace_id,\n            or_(\n                Customer.name.ilike(pattern),"
    )
    content = content.replace(
        "    msg_rows = await session.execute(\n        select(Message)\n        .where(Message.content.ilike(pattern))",
        "    msg_rows = await session.execute(\n        select(Message)\n        .join(Conversation, Message.conversation_id == Conversation.id)\n        .where(Conversation.workspace_id == workspace_id, Message.content.ilike(pattern))"
    )
    content = content.replace(
        "    intent_rows = await session.execute(\n        select(IntentHistory).where(\n            or_(\n                IntentHistory.reasoning.ilike(pattern),",
        "    intent_rows = await session.execute(\n        select(IntentHistory).where(\n            IntentHistory.workspace_id == workspace_id,\n            or_(\n                IntentHistory.reasoning.ilike(pattern),"
    )

    p.write_text(content, encoding="utf-8")

if __name__ == "__main__":
    replace_all()
