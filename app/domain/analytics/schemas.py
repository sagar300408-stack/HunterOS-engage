from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalyticsMetricResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    target_type: str
    target_id: UUID
    metric_date: date
    metric_name: str
    value: int

    model_config = ConfigDict(from_attributes=True)
