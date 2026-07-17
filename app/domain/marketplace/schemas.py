from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel


class ConnectorDefinitionSchema(BaseModel):
    id: UUID
    connector_id: str
    name: str
    description: Optional[str] = None
    vendor: str
    category: str
    certification: str
    connector_type: str
    status: str
    version: str
    supported_platform_versions: str
    icon_url: Optional[str] = None
    documentation_url: Optional[str] = None
    supported_capabilities: List[str]
    required_credentials: Dict[str, Any]
    configuration_schema: Dict[str, Any]

    class Config:
        from_attributes = True


class InstalledConnectorSchema(BaseModel):
    id: UUID
    workspace_id: UUID
    connector_id: str
    installation_version: str
    status: str
    configuration: Dict[str, Any]
    credential_reference: Optional[str] = None
    enabled: bool
    last_synchronized_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectorHealthRecordSchema(BaseModel):
    id: UUID
    installation_id: UUID
    status: str
    response_time_ms: Optional[int] = None
    latency_bucket: Optional[str] = None
    failure_count: int
    message: Optional[str] = None
    checked_at: datetime

    class Config:
        from_attributes = True


class InstallConnectorRequest(BaseModel):
    connector_id: str
    version: str
    requested_by: str


class ConfigureConnectorRequest(BaseModel):
    configuration: Dict[str, Any]
    credential_reference: Optional[str] = None


class UpgradeConnectorRequest(BaseModel):
    target_version: str
