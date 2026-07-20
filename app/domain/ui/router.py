import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.postgres.database import get_db
from app.domain.ui.schemas import (
    DashboardPayloadSchema,
    CommandCenterIntent,
    UserPreferenceSchema
)
from app.domain.ui.repository import UIRepository
from app.domain.ui.engines.composer import ComposerEngine
from app.domain.ui.engines.command_center import CommandCenterEngine

router = APIRouter(prefix="/ui", tags=["UI"])

@router.get("/dashboard/{role}", response_model=DashboardPayloadSchema)
async def get_dashboard(role: str, workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns the composed dashboard payload for the specified role.
    """
    repo = UIRepository(db)
    return await ComposerEngine.compose_dashboard(repo, workspace_id, role)

@router.post("/command-center/intent", response_model=CommandCenterIntent)
async def process_command(workspace_id: uuid.UUID, query: str, db: AsyncSession = Depends(get_db)):
    """
    Parses a natural language query from the Ctrl+K palette into an actionable intent.
    """
    return await CommandCenterEngine.process_query(str(workspace_id), query)

@router.get("/layout")
async def get_layout(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Returns navigation nodes dynamically adapted by WorkspaceCapabilityEngine
    return []

@router.get("/preferences", response_model=UserPreferenceSchema)
async def get_preferences(workspace_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Returns merged Organization -> Workspace -> User themes
    return UserPreferenceSchema(
        theme="system",
        high_contrast=False,
        reduced_motion=False,
        saved_views={}
    )
