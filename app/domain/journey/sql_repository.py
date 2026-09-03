import uuid
import pickle
from typing import Dict, List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.journey.models import (
    JourneyState,
    JourneyStageCode,
    JourneyStatus,
    JourneyStageTransition,
    JourneyTimeline,
    JourneyTimelineEvent,
)
from app.domain.journey.repository import JourneyReadRepository, JourneyWriteRepository
from app.domain.journey.sql_models import JourneyStateModel


class PostgreSQLJourneyRepository(JourneyReadRepository, JourneyWriteRepository):
    """Async PostgreSQL implementation of JourneyReadRepository and JourneyWriteRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _key(self, journey_instance_id: Union[uuid.UUID, str]) -> str:
        return str(journey_instance_id)

    # ── Read Operations ──────────────────────────────────────────────────

    async def get_journey(self, journey_instance_id: Union[uuid.UUID, str]) -> Optional[JourneyState]:
        stmt = select(JourneyStateModel).where(JourneyStateModel.journey_instance_id == uuid.UUID(str(journey_instance_id)))
        res = await self.session.execute(stmt)
        result = res.scalars().first()
        if not result:
            return None
        return pickle.loads(result.state_data)

    async def get_current_stage(self, journey_instance_id: Union[uuid.UUID, str]) -> Optional[JourneyStageCode]:
        journey = await self.get_journey(journey_instance_id)
        return journey.current_stage if journey else None

    async def get_stage_history(self, journey_instance_id: Union[uuid.UUID, str]) -> List[JourneyStageCode]:
        journey = await self.get_journey(journey_instance_id)
        return list(journey.stage_history) if journey else []

    async def get_transitions(self, journey_instance_id: Union[uuid.UUID, str]) -> List[JourneyStageTransition]:
        journey = await self.get_journey(journey_instance_id)
        return list(journey.transitions) if journey else []

    async def get_timeline(self, journey_instance_id: Union[uuid.UUID, str]) -> Optional[JourneyTimeline]:
        journey = await self.get_journey(journey_instance_id)
        return journey.timeline if journey else None

    async def query_by_stage(self, workspace_id: Union[uuid.UUID, str], stage: JourneyStageCode) -> List[JourneyState]:
        stmt = select(JourneyStateModel).where(
            JourneyStateModel.workspace_id == uuid.UUID(str(workspace_id)),
            JourneyStateModel.current_stage == stage.value,
        )
        res = await self.session.execute(stmt)
        results = res.scalars().all()
        return [pickle.loads(r.state_data) for r in results]

    async def query_by_status(self, workspace_id: Union[uuid.UUID, str], status: JourneyStatus) -> List[JourneyState]:
        stmt = select(JourneyStateModel).where(
            JourneyStateModel.workspace_id == uuid.UUID(str(workspace_id)),
            JourneyStateModel.status == status.value,
        )
        res = await self.session.execute(stmt)
        results = res.scalars().all()
        return [pickle.loads(r.state_data) for r in results]

    async def query_by_workspace(self, workspace_id: Union[uuid.UUID, str]) -> List[JourneyState]:
        stmt = select(JourneyStateModel).where(
            JourneyStateModel.workspace_id == uuid.UUID(str(workspace_id)),
        )
        res = await self.session.execute(stmt)
        results = res.scalars().all()
        return [pickle.loads(r.state_data) for r in results]

    # ── Write Operations ─────────────────────────────────────────────────

    async def _persist(self, state: JourneyState) -> None:
        stmt = select(JourneyStateModel).where(JourneyStateModel.journey_instance_id == state.journey_instance_id)
        res = await self.session.execute(stmt)
        model = res.scalars().first()
        
        if not model:
            model = JourneyStateModel(
                journey_instance_id=state.journey_instance_id,
                workspace_id=uuid.UUID(str(state.workspace_id)) if state.workspace_id else None,
                entity_id=state.entity_id,
                current_stage=state.current_stage.value,
                status=state.status.value,
                state_data=pickle.dumps(state),
            )
            self.session.add(model)
        else:
            model.current_stage = state.current_stage.value
            model.status = state.status.value
            model.state_data = pickle.dumps(state)
        await self.session.flush()

    async def create_journey(self, state: JourneyState) -> None:
        await self._persist(state)

    async def save_journey_state(self, state: JourneyState) -> None:
        await self._persist(state)

    async def append_transition(
        self, journey_instance_id: Union[uuid.UUID, str], transition: JourneyStageTransition,
    ) -> None:
        journey = await self.get_journey(journey_instance_id)
        if journey is not None:
            if transition not in journey.transitions:
                journey.transitions.append(transition)
                await self._persist(journey)

    async def append_timeline_event(
        self, journey_instance_id: Union[uuid.UUID, str], event: JourneyTimelineEvent,
    ) -> None:
        journey = await self.get_journey(journey_instance_id)
        if journey is not None and journey.timeline is not None:
            current_events = list(journey.timeline.events)
            current_events.append(event)
            journey.timeline = JourneyTimeline(
                timeline_id=journey.timeline.timeline_id,
                journey_instance_id=journey.journey_instance_id,
                workspace_id=journey.workspace_id,
                events=current_events,
            )
            await self._persist(journey)

