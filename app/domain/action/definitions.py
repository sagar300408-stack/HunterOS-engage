from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.domain.integration.schemas import ConnectorMetadata


class ActionDefinition(BaseModel):
    action_type: str
    description: str
    supported_connector_types: List[str]
    required_parameters: List[str]
    expected_result_keys: List[str] = []

    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        missing = [p for p in self.required_parameters if p not in parameters]
        if missing:
            raise ValueError(f"Missing required parameters for action {self.action_type}: {missing}")


@dataclass(frozen=True)
class ExecutionContext:
    """
    Immutable context passed throughout the execution pipeline.
    """
    workspace_id: UUID
    action_id: UUID
    correlation_id: Optional[UUID]
    idempotency_key: str
    connector_metadata: ConnectorMetadata
    request_metadata: Dict[str, Any] = field(default_factory=dict)


class ActionRegistry:
    def __init__(self):
        self._actions: Dict[str, ActionDefinition] = {}

    def register(self, definition: ActionDefinition) -> None:
        self._actions[definition.action_type] = definition

    def get(self, action_type: str) -> Optional[ActionDefinition]:
        return self._actions.get(action_type)


action_registry = ActionRegistry()

# Register Standard Actions
action_registry.register(ActionDefinition(
    action_type="create_lead",
    description="Creates a new lead in a CRM system.",
    supported_connector_types=["crm"],
    required_parameters=["email", "first_name", "last_name"]
))

action_registry.register(ActionDefinition(
    action_type="send_email",
    description="Sends an email via an email provider.",
    supported_connector_types=["email"],
    required_parameters=["to_address", "subject", "body"]
))
