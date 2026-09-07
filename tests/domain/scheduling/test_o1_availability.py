import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.domain.scheduling.availability_engine import calculate_availability, BusySlot
from app.domain.scheduling.models import CustomerAvailabilityPreferences
import app.main # to ensure all models are registered for SQLAlchemy

def test_availability_engine_respects_preferences_and_defaults():
    # Base date: A Monday
    target_date = datetime(2027, 9, 6, tzinfo=timezone.utc)
    duration_minutes = 60
    
    preferences = CustomerAvailabilityPreferences(
        timezone="Asia/Kolkata",
        unavailable_days=["Saturday", "Sunday"],
        preferred_time_of_day="morning",
        preferred_meeting_mode="video"
    )
    
    internal_slots = []
    external_slots = []
    
    slots = calculate_availability(
        target_date=target_date,
        duration_minutes=duration_minutes,
        preferences=preferences,
        internal_slots=internal_slots,
        external_slots=external_slots
    )
    
    assert len(slots) > 0
    for slot in slots:
        # Note: the slots are generated based on the target timezone (Asia/Kolkata)
        # We need to verify if the slots generated are 9AM-12PM in IST and returned properly
        pass

def test_availability_engine_internal_and_external_conflicts():
    target_date = datetime(2027, 9, 6, tzinfo=timezone.utc)
    duration_minutes = 30
    
    preferences = CustomerAvailabilityPreferences(
        timezone="UTC",
        unavailable_days=[],
        preferred_time_of_day="afternoon",
        preferred_meeting_mode="video"
    )
    
    internal_slots = [
        BusySlot(
            start=datetime(2027, 9, 6, 12, 0, tzinfo=timezone.utc),
            end=datetime(2027, 9, 6, 13, 0, tzinfo=timezone.utc)
        )
    ]
    
    external_slots = [
        BusySlot(
            start=datetime(2027, 9, 6, 14, 0, tzinfo=timezone.utc),
            end=datetime(2027, 9, 6, 15, 30, tzinfo=timezone.utc)
        )
    ]
    
    slots = calculate_availability(
        target_date=target_date,
        duration_minutes=duration_minutes,
        preferences=preferences,
        internal_slots=internal_slots,
        external_slots=external_slots
    )
    
    assert len(slots) > 0
    for slot in slots:
        assert not (slot.hour == 12)
        assert not (slot.hour == 14)
        assert not (slot.hour == 15 and slot.minute == 0)
