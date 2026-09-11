import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.scheduling.schemas import CreateEventRequest
from app.domain.scheduling.service import create_event
import app.domain.customers.models  # Required for SQLAlchemy relationship mapping

# Requires a real database to test pg_advisory_xact_lock

@pytest.mark.asyncio
async def test_concurrent_booking_prevents_overlap(pg_session_factory):
    workspace_id = uuid4()
    assigned_to = uuid4()
    target_time = datetime(2027, 10, 10, 14, 0, tzinfo=timezone.utc)
    
    # We will simulate two concurrent requests to create an event for the same assignee at the same time
    
    customer_id = uuid4()
    
    req1 = CreateEventRequest(
        workspace_id=workspace_id,
        customer_id=customer_id,
        event_type="meeting",
        title="Test Meeting 1",
        scheduled_for=target_time,
        duration_minutes=30,
        assignment_strategy="manual",
        assigned_to=assigned_to
    )
    
    req2 = CreateEventRequest(
        workspace_id=workspace_id,
        customer_id=customer_id,
        event_type="meeting",
        title="Test Meeting 2",
        scheduled_for=target_time,
        duration_minutes=30,
        assignment_strategy="manual",
        assigned_to=assigned_to
    )
    
    async def setup_db():
        async with pg_session_factory() as session:
            async with session.begin():
                from app.domain.security.models import User
                from app.domain.customers.models import Customer
                
                # Create user
                user = User(
                    id=assigned_to,
                    workspace_id=workspace_id,
                    email=f"test-{uuid4()}@example.com",
                    full_name="Test User",
                    password_hash="test",
                    role="sales"
                )
                session.add(user)
                
                import random
                # Create customer
                cust_id = req1.customer_id
                customer = Customer(
                    id=cust_id,
                    workspace_id=workspace_id,
                    email=f"cust-{uuid4()}@example.com",
                    name="Test Customer",
                    phone=f"{random.randint(1000000000, 9999999999)}"
                )
                session.add(customer)
    
    await setup_db()

    async def run_create(req):
        async with pg_session_factory() as session:
            try:
                # Need to run in a transaction for xact_lock to work
                async with session.begin():
                    event = await create_event(session, req, actor_id=assigned_to, actor_type="user", is_demo=False)
                    return event, None
            except Exception as e:
                return None, e
                
    # Run concurrently
    results = await asyncio.gather(run_create(req1), run_create(req2))
    
    successes = 0
    failures = 0
    
    for event, err in results:
        if event:
            successes += 1
        else:
            print(f"Error: {repr(err)}")
            if err and "Double booking" in str(err):
                failures += 1
            
    assert successes == 1, "Exactly one booking should succeed"
    assert failures == 1, "Exactly one booking should fail with a double booking error"
