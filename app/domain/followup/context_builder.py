from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

class FollowUpContext:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

async def build_context(
    session: AsyncSession,
    customer_id: UUID,
    conversation_id: Optional[UUID],
    follow_up_reason: str,
    follow_up_strategy: str,
    strategy_instructions: str,
    attempt_number: int,
    workspace_id: UUID,
) -> FollowUpContext:
    
    return FollowUpContext(
        customer_id=customer_id,
        reason=follow_up_reason,
        strategy=follow_up_strategy,
        instructions=strategy_instructions,
        attempt=attempt_number
    )
