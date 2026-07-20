"""
Seed default SLA policies for the Business Friction Engine.
Run once:  python scripts/seed_friction.py

Creates sensible default SLA policies for the default workspace.
These can be overridden via the API: POST /api/v1/friction/sla/{workspace_id}
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from app.integrations.postgres.database import get_session_factory, create_tables
from app.domain.friction.models import SLAPolicy
from app.domain.dashboard.models import DEFAULT_WORKSPACE_ID


DEFAULT_SLA_POLICIES = [
    {
        "policy_name": "New Lead — First Response",
        "event_trigger": "lead.created",
        "target_metric": "first_contact_minutes",
        "description": "First outbound contact must happen within 30 minutes of lead creation.",
        "warning_threshold_minutes": 30,
        "critical_threshold_minutes": 120,
    },
    {
        "policy_name": "Proposal Delivery",
        "event_trigger": "lead.proposal_requested",
        "target_metric": "proposal_sent_minutes",
        "description": "Proposal must be delivered within 24 hours of request.",
        "warning_threshold_minutes": 60 * 12,    # 12 hours
        "critical_threshold_minutes": 60 * 24,   # 24 hours
    },
    {
        "policy_name": "Meeting Confirmation",
        "event_trigger": "meeting.scheduled",
        "target_metric": "confirmation_sent_minutes",
        "description": "Meeting confirmation must be sent within 2 hours of scheduling.",
        "warning_threshold_minutes": 60,
        "critical_threshold_minutes": 120,
    },
    {
        "policy_name": "Approval Response",
        "event_trigger": "approval.requested",
        "target_metric": "approval_decision_minutes",
        "description": "Approval decisions must be made within 12 hours.",
        "warning_threshold_minutes": 60 * 4,    # 4 hours
        "critical_threshold_minutes": 60 * 12,  # 12 hours
    },
    {
        "policy_name": "Missed Follow-up",
        "event_trigger": "followup.missed",
        "target_metric": "followup_overdue_minutes",
        "description": "Follow-ups must not remain unexecuted for more than 60 minutes past schedule.",
        "warning_threshold_minutes": 30,
        "critical_threshold_minutes": 60,
    },
]


async def seed():
    await create_tables()

    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            for policy_data in DEFAULT_SLA_POLICIES:
                existing = await session.scalar(
                    select(SLAPolicy).where(
                        SLAPolicy.workspace_id == DEFAULT_WORKSPACE_ID,
                        SLAPolicy.policy_name == policy_data["policy_name"],
                    )
                )
                if existing:
                    print(f"  ✅ Already exists: {policy_data['policy_name']}")
                    continue

                policy = SLAPolicy(
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    **policy_data,
                    is_active=True,
                )
                session.add(policy)
                print(f"  ➕ Created: {policy_data['policy_name']}")

    print("\n✅ SLA policies seeded successfully.")
    print(f"   Workspace: {DEFAULT_WORKSPACE_ID}")


if __name__ == "__main__":
    asyncio.run(seed())
