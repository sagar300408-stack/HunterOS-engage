"""
Memory Domain - Interfaces
"""

from app.domain.memory.interfaces.repository import AbstractMemoryRepository
from app.domain.memory.interfaces.service import AbstractMemoryService

__all__ = [
    "AbstractMemoryRepository",
    "AbstractMemoryService",
]
