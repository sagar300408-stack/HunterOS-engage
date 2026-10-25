path = 'app/events/followup_subscribers.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''from app.events.message_events import MessageStored, ReplySent'''
replacement = '''from app.events.message_events import MessageStored, MessageReceived, ReplySent'''

assert target in content
content = content.replace(target, replacement, 1)

target2 = '''class FollowUpMessageStoredConsumer(EventConsumer):
    """Triggered when a customer message is received and saved."""
    
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [MessageStored]
        
    def get_execution_policy(self) -> ExecutionPolicy:
        # Background task that shouldn't block the main webhook pipeline
        return ExecutionPolicy.BACKGROUND

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not isinstance(event, MessageStored):
            return
            
        if not event.conversation_id:
            return

        try:
            async with get_session() as session:
                # 1. Get customer ID
                conv = await session.get(Conversation, event.conversation_id)
                if not conv or not conv.customer_id:
                    return
                
                customer_id = conv.customer_id
                
                # 2. Update health score
                await upsert_health_score(session, customer_id, DEFAULT_WORKSPACE_ID)
                
                # 3. Re-evaluate follow-up needs
                await schedule_followup(session, customer_id, event.conversation_id, DEFAULT_WORKSPACE_ID)
                
                # 4. Record customer replied milestone
                await record_customer_replied(session, customer_id, DEFAULT_WORKSPACE_ID)'''

replacement2 = '''class FollowUpMessageStoredConsumer(EventConsumer):
    """Triggered when a customer message is received and saved."""
    
    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [MessageReceived, MessageStored]
        
    def get_execution_policy(self) -> ExecutionPolicy:
        # Background task that shouldn't block the main webhook pipeline
        return ExecutionPolicy.BACKGROUND

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not isinstance(event, (MessageReceived, MessageStored)):
            return
            
        if not event.conversation_id:
            return

        try:
            async with get_session() as session:
                # 1. Get customer ID
                conv = await session.get(Conversation, event.conversation_id)
                if not conv or not conv.customer_id:
                    return
                
                customer_id = conv.customer_id
                target_workspace_id = event.workspace_id or getattr(conv, "workspace_id", None) or DEFAULT_WORKSPACE_ID
                
                # 2. Update health score
                await upsert_health_score(session, customer_id, target_workspace_id)
                
                # 3. Re-evaluate follow-up needs
                await schedule_followup(session, customer_id, event.conversation_id, target_workspace_id)
                
                # 4. Record customer replied milestone
                await record_customer_replied(session, customer_id, target_workspace_id)'''

assert target2 in content
content = content.replace(target2, replacement2, 1)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Updated app/events/followup_subscribers.py successfully.")
