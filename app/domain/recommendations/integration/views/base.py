from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class BaseRecommendationView(BaseModel):
    """
    Base DTO model for a recommendation projection view.
    """
    id: str = Field(..., description="Unique identifier of the recommendation")
    type: str = Field(..., description="Type of the projection view")
    raw_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw assembled data")
