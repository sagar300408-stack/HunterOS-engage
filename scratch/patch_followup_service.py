import re

path = 'app/domain/followup/service.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''    # 2. Evaluate
    decision = evaluate(
        customer_id=customer_id,
        conversation_id=conversation_id,
        last_outgoing_at=last_out,
        last_incoming_at=last_in,
        last_followup_sent_at=last_fu,
        followup_attempt_count=fu_count,
        buying_stage=latest_intent.buying_stage if latest_intent else None,
        urgency=latest_intent.urgency.value if latest_intent and latest_intent.urgency else None,
        has_open_proposal=False,  # Stubbed for now, integrate with CRM later
        has_confirmed_meeting=False,
        next_meeting_at=None,
        has_missed_meeting=False,
        callback_requested=False,
        approval_pending=False,
        budget_mentioned=False,
        budget_paused=False,
        max_attempts=max_attempts,
    )

    if not decision.should_follow_up:
        return None

    # Cancel any existing scheduled follow-ups
    existing = await session.execute(
        select(FollowUpQueue).where(FollowUpQueue.customer_id == customer_id, FollowUpQueue.status == "scheduled")
    )
    for ext in existing.scalars().all():
        ext.status = transition(ext.status, "cancelled")
        ext.cancellation_reason = "Superseded by new evaluation"'''

replacement = '''    # 2. Check Opt-Out & Evaluate
    last_in_msg = await session.scalar(
        select(Message.content).join(Conversation).where(
            Conversation.customer_id == customer_id, Message.direction == "incoming"
        ).order_by(Message.timestamp.desc()).limit(1)
    )
    is_opted_out = False
    if last_in_msg:
        cleaned_msg = last_in_msg.strip().upper()
        if cleaned_msg in {"STOP", "UNSUBSCRIBE", "OPT OUT", "OPTOUT", "QUIT", "CANCEL"}:
            is_opted_out = True

    from app.domain.customers.models import Customer, CustomerStatus
    customer_record = await session.get(Customer, customer_id)
    if customer_record and customer_record.status == CustomerStatus.inactive:
        is_opted_out = True
    elif is_opted_out and customer_record:
        customer_record.status = CustomerStatus.inactive

    decision = evaluate(
        customer_id=customer_id,
        conversation_id=conversation_id,
        last_outgoing_at=last_out,
        last_incoming_at=last_in,
        last_followup_sent_at=last_fu,
        followup_attempt_count=fu_count,
        buying_stage=latest_intent.buying_stage if latest_intent else None,
        urgency=latest_intent.urgency.value if latest_intent and latest_intent.urgency else None,
        has_open_proposal=False,  # Stubbed for now, integrate with CRM later
        has_confirmed_meeting=False,
        next_meeting_at=None,
        has_missed_meeting=False,
        callback_requested=False,
        approval_pending=False,
        budget_mentioned=False,
        budget_paused=False,
        max_attempts=max_attempts,
        is_opted_out=is_opted_out,
    )

    # Cancel any existing scheduled follow-ups (DEF-10 Fix: must run before returning None)
    existing = await session.execute(
        select(FollowUpQueue).where(FollowUpQueue.customer_id == customer_id, FollowUpQueue.status == "scheduled")
    )
    cancellation_reason = (
        "Customer opted out" if is_opted_out else (
            f"Follow-up criteria not met: {decision.reason}" if not decision.should_follow_up
            else "Superseded by new evaluation"
        )
    )
    for ext in existing.scalars().all():
        ext.status = transition(ext.status, "cancelled")
        ext.cancellation_reason = cancellation_reason

    if not decision.should_follow_up:
        return None'''

assert target in content, "Target block not found in service.py"
updated = content.replace(target, replacement, 1)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(updated)

print("Updated app/domain/followup/service.py successfully.")
