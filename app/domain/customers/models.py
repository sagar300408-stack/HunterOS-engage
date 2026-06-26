"""
Customer ORM model — Phase 2 stub.

Phase 2 implementation:
  1. Uncomment and populate this model.
  2. Add migration: alembic revision --autogenerate -m "add_customers_table"
  3. Add FK to Conversation:
       customer_id = Column(UUID, ForeignKey("customers.id"), nullable=True)
  4. Populate customer_service.py
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.domain.conversations.models import Base


class Customer(Base):
    """
    Customer profile.

    Phase 2: Linked from Conversation via customer_id FK.
    Phase 3: Linked from Lead via customer_id FK.
    """

    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    phone = Column(String(30), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow(),
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} phone={self.phone}>"
