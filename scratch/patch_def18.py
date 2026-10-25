path = 'app/worker/followup_worker.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''        # 3. Publish MessageReadyToSendEvent
        from app.events.message_events import MessageReadyToSendEvent
        ready_event = MessageReadyToSendEvent(
            to_phone=customer.phone,
            content=message,
            conversation_id=str(conversation_id),
            workspace_id=fu.workspace_id,
            customer_id=fu.customer_id,
            message_id=outgoing_msg.id,
            actor_type=ActorType.SYSTEM,
            correlation_id=fu.id,
            causation_id=fu.id,
        )'''

replacement = '''        # 3. Publish MessageReadyToSendEvent
        from app.events.message_events import MessageReadyToSendEvent
        ready_event = MessageReadyToSendEvent(
            to_phone=customer.phone,
            content=message,
            conversation_id=str(conversation_id),
            workspace_id=fu.workspace_id,
            customer_id=fu.customer_id,
            actor_type=ActorType.SYSTEM,
            correlation_id=fu.id,
            causation_id=fu.id,
            metadata={"message_id": str(outgoing_msg.id)},
        )'''

assert target in content, "Target block not found in followup_worker.py"
content = content.replace(target, replacement, 1)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Applied DEF-18 patch to app/worker/followup_worker.py successfully.")
