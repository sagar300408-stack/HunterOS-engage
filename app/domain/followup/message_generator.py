from app.domain.followup.schemas import GeneratedMessage
from app.domain.followup.context_builder import FollowUpContext

async def generate_message(ctx: FollowUpContext) -> GeneratedMessage:
    # Stub: Normally we would call OpenAI here using ctx.instructions
    return GeneratedMessage(
        content=f"Hi there, this is a {ctx.strategy.replace('_', ' ')}. {ctx.instructions}",
        confidence=90
    )
