"""
HunterOS Engage — Assignment Strategy Pattern

Phase 5: Only ManualAssignmentStrategy is implemented.
All other strategies exist as stubs — Phase 6 activates them.

Usage:
    strategy = get_assignment_strategy("manual", user_id=some_uuid)
    user_id  = await strategy.assign(session, event, workspace_id)
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── Abstract base ──────────────────────────────────────────────────────────────

class AssignmentStrategy(ABC):
    """Base class for all assignment strategies."""

    @abstractmethod
    async def assign(
        self,
        session:      AsyncSession,
        event,                        # ScheduledEvent ORM object
        workspace_id: UUID,
    ) -> Optional[UUID]:
        """
        Determine and return the user_id to assign to this event.
        Returns None if no assignment can be made.
        """


# ── Implementations ────────────────────────────────────────────────────────────

class ManualAssignmentStrategy(AssignmentStrategy):
    """
    Phase 5: Explicit user_id assignment.
    The caller provides the exact user to assign.
    """
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def assign(
        self,
        session:      AsyncSession,
        event,
        workspace_id: UUID,
    ) -> Optional[UUID]:
        logger.debug(
            "assignment_manual",
            event_id=str(event.id),
            user_id=str(self._user_id),
        )
        return self._user_id


class RoundRobinStrategy(AssignmentStrategy):
    """Phase 6 stub — assigns to next available representative in rotation."""

    async def assign(
        self,
        session:      AsyncSession,
        event,
        workspace_id: UUID,
    ) -> Optional[UUID]:
        raise NotImplementedError(
            "RoundRobinStrategy is not implemented in Phase 5. "
            "Use ManualAssignmentStrategy or wait for Phase 6."
        )


class AIAssignmentStrategy(AssignmentStrategy):
    """Phase 6 stub — AI selects the best representative based on customer profile."""

    async def assign(
        self,
        session:      AsyncSession,
        event,
        workspace_id: UUID,
    ) -> Optional[UUID]:
        raise NotImplementedError(
            "AIAssignmentStrategy is not implemented in Phase 5."
        )


class TerritoryStrategy(AssignmentStrategy):
    """Phase 6 stub — assigns based on geographic territory rules."""

    async def assign(
        self,
        session:      AsyncSession,
        event,
        workspace_id: UUID,
    ) -> Optional[UUID]:
        raise NotImplementedError(
            "TerritoryStrategy is not implemented in Phase 5."
        )


class SkillBasedStrategy(AssignmentStrategy):
    """Phase 6 stub — assigns based on representative skills and event requirements."""

    async def assign(
        self,
        session:      AsyncSession,
        event,
        workspace_id: UUID,
    ) -> Optional[UUID]:
        raise NotImplementedError(
            "SkillBasedStrategy is not implemented in Phase 5."
        )


# ── Factory ────────────────────────────────────────────────────────────────────

def get_assignment_strategy(
    strategy_name: str,
    **kwargs,
) -> AssignmentStrategy:
    """
    Factory — return the correct assignment strategy by name.

    Args:
        strategy_name: "manual" | "round_robin" | "ai" | "territory" | "skill_based"
        **kwargs:       Strategy-specific arguments (e.g. user_id for manual)

    Raises:
        ValueError: If strategy_name is unknown.
        NotImplementedError: If the strategy is a Phase 6 stub.
    """
    strategies = {
        "manual":      ManualAssignmentStrategy,
        "round_robin": RoundRobinStrategy,
        "ai":          AIAssignmentStrategy,
        "territory":   TerritoryStrategy,
        "skill_based": SkillBasedStrategy,
    }

    cls = strategies.get(strategy_name)
    if cls is None:
        raise ValueError(
            f"Unknown assignment strategy '{strategy_name}'. "
            f"Valid: {list(strategies.keys())}"
        )

    return cls(**kwargs)
