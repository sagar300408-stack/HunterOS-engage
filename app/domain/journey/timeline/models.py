from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from app.domain.journey.models import JourneyTimeline, JourneyTimelineEvent


@dataclass(frozen=True)
class JourneyTimelineView:
    """Read-optimized view of a journey timeline."""
    
    timeline: JourneyTimeline
    total_events: int
    first_event_at: Optional[datetime]
    last_event_at: Optional[datetime]
    stage_durations: Dict[str, float] = field(default_factory=dict)
