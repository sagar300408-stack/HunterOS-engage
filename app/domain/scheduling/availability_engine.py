"""
HunterOS Engage — Availability Engine

Provider-independent slot generation for scheduling.
Synthesizes Working Hours, Timezone, Customer Preferences, and internal/external busy slots
into a set of bookable timeslots.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import zoneinfo
from typing import List, Optional

from app.domain.scheduling.models import CustomerAvailabilityPreferences


@dataclass
class BusySlot:
    """Normalized representation of a busy time period from any source (internal or external)."""
    start: datetime
    end: datetime


def calculate_availability(
    target_date: datetime,
    duration_minutes: int,
    preferences: Optional[CustomerAvailabilityPreferences] = None,
    internal_slots: List[BusySlot] = None,
    external_slots: List[BusySlot] = None,
) -> List[datetime]:
    """
    Generate bookable slots for a specific date in the customer's timezone.
    
    Args:
        target_date: The day to generate slots for (can be any datetime, uses the date part).
        duration_minutes: Duration of the proposed event.
        preferences: Optional customer preferences (dictates timezone and preferred time of day).
        internal_slots: Busy slots from HunterOS ScheduledEvents.
        external_slots: Busy slots from Google/Outlook.
        
    Returns:
        List of timezone-aware datetimes representing available start times.
    """
    internal = internal_slots or []
    external = external_slots or []
    all_busy = internal + external
    
    # Timezone resolution
    tz_name = preferences.timezone if preferences and preferences.timezone else "Asia/Kolkata"
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        
    # Standard working hours: 9 AM to 5 PM in local timezone
    # Convert target_date to the requested timezone to get the correct 'day' boundaries
    local_target = target_date.astimezone(tz)
    
    # If the day is an unavailable day in preferences, return empty
    if preferences and preferences.unavailable_days:
        day_name = local_target.strftime("%A")
        if day_name in preferences.unavailable_days:
            return []

    # Define boundaries (9 AM to 5 PM)
    work_start = datetime(local_target.year, local_target.month, local_target.day, 9, 0, tzinfo=tz)
    work_end = datetime(local_target.year, local_target.month, local_target.day, 17, 0, tzinfo=tz)
    
    # Filter boundaries based on preferred time of day if requested
    if preferences and preferences.preferred_time_of_day:
        pref = preferences.preferred_time_of_day.lower()
        if pref == "morning":
            work_end = datetime(local_target.year, local_target.month, local_target.day, 12, 0, tzinfo=tz)
        elif pref == "afternoon":
            work_start = datetime(local_target.year, local_target.month, local_target.day, 12, 0, tzinfo=tz)
        elif pref == "evening":
            # Push working hours slightly for evening if required, or just limit to 4-5 PM
            work_start = datetime(local_target.year, local_target.month, local_target.day, 16, 0, tzinfo=tz)
            work_end = datetime(local_target.year, local_target.month, local_target.day, 20, 0, tzinfo=tz)

    available_start_times = []
    
    # Generate slots every 30 minutes
    current_time = work_start
    while current_time + timedelta(minutes=duration_minutes) <= work_end:
        slot_end = current_time + timedelta(minutes=duration_minutes)
        
        # Check against all busy slots
        is_conflict = False
        for busy in all_busy:
            # Overlap condition: start < end AND end > start
            if current_time < busy.end and slot_end > busy.start:
                is_conflict = True
                break
                
        # Also ensure the slot isn't in the past
        if not is_conflict and current_time > datetime.now(tz):
            available_start_times.append(current_time)
            
        current_time += timedelta(minutes=30)  # Next possible slot
        
    return available_start_times
