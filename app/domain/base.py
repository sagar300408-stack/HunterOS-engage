"""
HunterOS Engage — Shared Declarative Base
app/domain/base.py

Provides the single shared DeclarativeBase for all SQLAlchemy domain models,
preventing circular dependencies between domain entities.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass
