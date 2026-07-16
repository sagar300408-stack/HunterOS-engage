from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel

from app.domain.integration.models import ConnectionStatus


class ConnectorCapabilities(BaseModel):
    supports_read: bool = False
    supports_write: bool = False
    supports_webhooks: bool = False


class ConnectorMetadata(BaseModel):
    connector_id: str
    connector_type: str
    provider: str
    name: str
    version: str
    description: str
    
    capabilities: ConnectorCapabilities
    authentication_type: str # e.g. "oauth2", "api_key", "basic"
    
    supported_actions: List[str] = []
    supported_events: List[str] = []


class IntegrationConnectionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    connector_id: str
    connector_type: str
    provider: str
    name: str
    status: str
    settings: Dict[str, Any]
    last_sync_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectRequest(BaseModel):
    connector_id: str
    name: str
    credentials: Dict[str, Any]
    settings: Dict[str, Any] = {}
