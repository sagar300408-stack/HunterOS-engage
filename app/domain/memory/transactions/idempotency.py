"""
HunterOS Engage — Memory Idempotency Manager

Provides request deduplication, replay suppression, and safe retry support
with configurable TTL expiration (expires_at).
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.models import MemoryDomainError, MemoryIdempotencyRecord

logger = logging.getLogger(__name__)


class MemoryIdempotencyError(MemoryDomainError):
    """Raised when an idempotency key conflict or collision occurs."""
    pass


class IdempotencyManager:
    """
    Manages idempotency keys, request hashes, and cached responses.
    """

    def __init__(self, ttl_hours: int = 24):
        self.ttl_hours = ttl_hours

    @staticmethod
    def compute_request_hash(data: Any) -> str:
        """Computes SHA-256 hash of normalized request content."""
        if data is None:
            raw = "{}"
        elif isinstance(data, dict):
            raw = json.dumps(data, sort_keys=True, default=str)
        else:
            raw = str(data)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def get_cached_response(
        self, session: AsyncSession, idempotency_key: str, request_hash: str
    ) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Checks if an active, unexpired idempotency record exists.
        Returns (response_status, response_body) if cached, or None.
        Raises MemoryIdempotencyError if the key exists with a different payload.
        """
        stmt = select(MemoryIdempotencyRecord).where(
            MemoryIdempotencyRecord.idempotency_key == idempotency_key
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            return None

        # Check expiration
        if record.is_expired():
            logger.info(f"Idempotency record '{idempotency_key}' expired. Treating as fresh request.")
            return None

        # Payload hash verification
        if record.request_hash != request_hash:
            raise MemoryIdempotencyError(
                f"Idempotency key '{idempotency_key}' was already used with different request parameters."
            )

        logger.info(f"Returning cached response for idempotency key '{idempotency_key}'.")
        return record.response_status, record.response_body

    async def save_response(
        self,
        session: AsyncSession,
        idempotency_key: str,
        request_hash: str,
        response_status: int,
        response_body: Dict[str, Any],
    ) -> MemoryIdempotencyRecord:
        """Saves response record with future expires_at."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.ttl_hours)

        record = MemoryIdempotencyRecord(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            response_status=response_status,
            response_body=response_body,
            created_at=now,
            expires_at=expires_at,
        )
        session.add(record)
        return record


# Default singleton
_default_idempotency_manager: Optional[IdempotencyManager] = None


def get_idempotency_manager() -> IdempotencyManager:
    global _default_idempotency_manager
    if _default_idempotency_manager is None:
        _default_idempotency_manager = IdempotencyManager()
    return _default_idempotency_manager
