from typing import Dict, Any
from app.domain.timeline.strategies.base import BaseTimelineStrategy, TimelineFormattedData
from app.domain.timeline.models import TimelineSeverity
from app.events.model.base_event import UniversalBaseEvent

class OperationalEventStrategy(BaseTimelineStrategy):
    """
    Generic strategy for handling Phase 3 Operational events in the Timeline.
    Captures provenance data and formats the timeline entry based on the event_name.
    """
    
    def __init__(self, activity_type: str, title_template: str, default_severity: TimelineSeverity = TimelineSeverity.NORMAL):
        self._activity_type = activity_type
        self._title_template = title_template
        self._default_severity = default_severity

    @property
    def default_severity(self) -> TimelineSeverity:
        return self._default_severity

    @property
    def activity_type(self) -> str:
        return self._activity_type

    def extract_structured_data(self, event: UniversalBaseEvent) -> Dict[str, Any]:
        action_id_str = None
        if hasattr(event, "action_id"):
            action_id_str = str(event.action_id)
        elif event.metadata and "action_id" in event.metadata:
            action_id_str = event.metadata["action_id"]

        data = {
            "source_event_type": event.event_name,
            "action_id": action_id_str,
            "actor_type": event.actor_type.value,
            "actor_id": event.actor_id,
            "correlation_id": str(event.correlation_id) if event.correlation_id else None,
            "causation_id": str(event.causation_id) if event.causation_id else None,
        }
        
        if event.metadata:
            data.update(event.metadata)
            
        return data

    def format_for_display(self, structured_data: Dict[str, Any]) -> TimelineFormattedData:
        action_id = structured_data.get("action_id", "Unknown")
        actor_id = structured_data.get("actor_id", "System")
        
        title = self._title_template.format(actor_id=actor_id, action_id=action_id)
        description = f"Event: {structured_data.get('source_event_type')}"
        
        if "reason" in structured_data and structured_data["reason"]:
            description += f" - {structured_data['reason']}"
        elif "failure_reason" in structured_data and structured_data["failure_reason"]:
            description += f" - Failed due to: {structured_data['failure_reason']}"
            
        return TimelineFormattedData(
            title=title,
            description=description
        )

# Define instances for registry
ActionCreatedStrategy = OperationalEventStrategy(
    activity_type="action_created", 
    title_template="Action created by {actor_id}",
    default_severity=TimelineSeverity.NORMAL
)

ActionStatusChangedStrategy = OperationalEventStrategy(
    activity_type="action_status_changed", 
    title_template="Action status changed by {actor_id}",
    default_severity=TimelineSeverity.NORMAL
)

ApprovalRequestedStrategy = OperationalEventStrategy(
    activity_type="approval_requested", 
    title_template="Approval requested by {actor_id}",
    default_severity=TimelineSeverity.NORMAL
)

ApprovalRejectedStrategy = OperationalEventStrategy(
    activity_type="approval_rejected", 
    title_template="Approval rejected by {actor_id}",
    default_severity=TimelineSeverity.HIGH
)

ApprovalApprovedStrategy = OperationalEventStrategy(
    activity_type="approval_approved", 
    title_template="Approval granted by {actor_id}",
    default_severity=TimelineSeverity.INFO
)

OrchestrationStartedStrategy = OperationalEventStrategy(
    activity_type="orchestration_started", 
    title_template="Action orchestration started",
    default_severity=TimelineSeverity.NORMAL
)

OrchestrationFailedStrategy = OperationalEventStrategy(
    activity_type="orchestration_failed", 
    title_template="Action orchestration failed",
    default_severity=TimelineSeverity.HIGH
)

ActionCompletedStrategy = OperationalEventStrategy(
    activity_type="action_completed", 
    title_template="Action completed successfully",
    default_severity=TimelineSeverity.INFO
)
