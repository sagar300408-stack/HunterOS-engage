"""
Pydantic schemas for the Customer domain.

Used for API I/O, internal service DTOs, and inter-module communication.
No layer touches ORM models directly — it goes through these schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerStatusEnum(str, Enum):
    new = "new"
    active = "active"
    inactive = "inactive"
    qualified = "qualified"


# ── Read schemas ──────────────────────────────────────────────────────────────

class CustomerSchema(BaseModel):
    """Full customer read model returned by service layer."""

    id: UUID
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    status: CustomerStatusEnum = CustomerStatusEnum.new
    preferred_language: str = "en"
    notes: Optional[str] = None
    created_at: datetime
    last_interaction: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Internal DTOs ─────────────────────────────────────────────────────────────

class CreateCustomerDTO(BaseModel):
    """
    Passed to customer_service.get_or_create_customer().
    Keeps the pipeline decoupled from ORM models.
    """
    phone: str
    name: Optional[str] = None


class UpdateCustomerDTO(BaseModel):
    """
    Passed to customer_service.update_customer_profile().
    All fields optional — only provided fields are updated.
    """
    name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[CustomerStatusEnum] = None
    preferred_language: Optional[str] = None
    notes: Optional[str] = None
