"""
HunterOS Engage — Memory Query Pagination Models

Provides Offset Pagination and Workspace-Isolated Keyset Cursor Pagination
to guarantee zero cross-tenant cursor leakage and high-throughput scrolling.
"""

import base64
import json
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID
from pydantic import BaseModel, Field


T = TypeVar("T")


class OffsetPaginationParams(BaseModel):
    """Parameters for traditional offset pagination."""
    page: int = Field(1, ge=1, description="1-indexed page number")
    page_size: int = Field(50, ge=1, le=200, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class OffsetPaginatedResult(BaseModel, Generic[T]):
    """Result envelope for offset-paginated queries."""
    items: List[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def create(cls, items: List[T], total_count: int, page: int, page_size: int) -> "OffsetPaginatedResult[T]":
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        return cls(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class CursorPaginationParams(BaseModel):
    """Parameters for workspace-isolated keyset cursor pagination."""
    cursor: Optional[str] = Field(None, description="Opaque base64 cursor token")
    limit: int = Field(50, ge=1, le=200, description="Number of items to fetch")


class CursorPaginatedResult(BaseModel, Generic[T]):
    """Result envelope for keyset cursor queries."""
    items: List[T]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_more: bool = False
    limit: int = 50


class CursorCodec:
    """Encodes and decodes workspace-isolated keyset cursor tokens."""

    @staticmethod
    def encode_cursor(updated_at: datetime, item_id: UUID, workspace_id: Optional[UUID] = None) -> str:
        """Serialize updated_at, item_id, and workspace_id into a base64 token."""
        ts_str = updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at)
        payload = {
            "u": ts_str,
            "id": str(item_id),
            "w": str(workspace_id) if workspace_id else None,
        }
        json_bytes = json.dumps(payload).encode("utf-8")
        return base64.urlsafe_b64encode(json_bytes).decode("ascii")

    @staticmethod
    def decode_cursor(token: str, expected_workspace_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Decode and validate cursor token.
        Raises ValueError if token is corrupted or cross-workspace mismatch is detected.
        """
        try:
            json_bytes = base64.urlsafe_b64decode(token.encode("ascii"))
            data = json.loads(json_bytes.decode("utf-8"))
            updated_at_str = data.get("u")
            item_id_str = data.get("id")
            token_ws_str = data.get("w")

            if not updated_at_str or not item_id_str:
                raise ValueError("Incomplete cursor token payload")

            # Cross-tenant cursor boundary protection
            if expected_workspace_id is not None and token_ws_str is not None:
                if token_ws_str != str(expected_workspace_id):
                    raise ValueError(f"Cross-workspace cursor boundary violation: expected {expected_workspace_id}, got {token_ws_str}")

            return {
                "updated_at": datetime.fromisoformat(updated_at_str),
                "id": UUID(item_id_str),
                "workspace_id": UUID(token_ws_str) if token_ws_str else None,
            }
        except Exception as e:
            raise ValueError(f"Invalid cursor token: {str(e)}") from e


__all__ = [
    "OffsetPaginationParams",
    "OffsetPaginatedResult",
    "CursorPaginationParams",
    "CursorPaginatedResult",
    "CursorCodec",
]
