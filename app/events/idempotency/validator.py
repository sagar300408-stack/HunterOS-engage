"""
HunterOS Engage — Idempotency Startup Validator
app/events/idempotency/validator.py

Validates all 5 essential idempotency subsystems at application startup.
Fails fast if any component is misconfigured or missing.
"""

from __future__ import annotations

from typing import Any, Optional
import structlog

from app.events.idempotency.decision import IdempotencyAction, IdempotencyDecision
from app.events.idempotency.generator import IdempotencyKeyGenerator
from app.events.idempotency.hasher import CanonicalHasher
from app.events.store.models import EventRecord

logger = structlog.get_logger(__name__)


class IdempotencyStartupValidationError(RuntimeError):
    """Raised when critical idempotency components fail startup validation."""
    pass


class IdempotencyStartupValidator:
    """
    Validates idempotency engine prerequisites at application initialization.
    """

    @classmethod
    def validate(
        cls,
        engine: Optional[Any] = None,
        key_generator: Optional[IdempotencyKeyGenerator] = None,
        hasher: Optional[CanonicalHasher] = None,
    ) -> None:
        """
        Performs fail-fast health checks across:
        1. Canonical hashing strategy
        2. Idempotency key generator
        3. Event Store unique constraint / column definition
        4. Replay bypass compatibility
        5. Duplicate resolution handler
        """
        logger.info("validating_idempotency_subsystems")

        # 1. Validate Canonical Hashing Strategy
        try:
            sample_1 = {"b": 2, "a": 1, "nested": {"y": [2, 1], "x": "val"}}
            sample_2 = {"a": 1, "b": 2, "nested": {"x": "val", "y": [2, 1]}}
            hash_1 = (hasher or CanonicalHasher).hash_payload(sample_1)
            hash_2 = (hasher or CanonicalHasher).hash_payload(sample_2)
            if hash_1 != hash_2:
                raise IdempotencyStartupValidationError(
                    "Canonical hashing is non-deterministic: equivalent payloads produced different hashes."
                )
        except Exception as exc:
            raise IdempotencyStartupValidationError(
                f"CanonicalHasher validation failed: {exc}"
            ) from exc

        # 2. Validate Key Generator
        try:
            gen = key_generator or (engine.key_generator if engine else IdempotencyKeyGenerator())
            sample_event = {
                "event_name": "test.startup.validation",
                "workspace_id": "00000000-0000-0000-0000-000000000000",
                "correlation_id": "11111111-1111-1111-1111-111111111111",
                "data": "test",
            }
            k1 = gen.generate_key(sample_event)
            k2 = gen.generate_key(sample_event)
            if not k1 or k1 != k2 or len(k1) != 64:
                raise IdempotencyStartupValidationError(
                    "IdempotencyKeyGenerator produced an invalid or non-deterministic key."
                )
        except Exception as exc:
            raise IdempotencyStartupValidationError(
                f"IdempotencyKeyGenerator validation failed: {exc}"
            ) from exc

        # 3. Validate Event Store Model Unique Constraint
        try:
            idemp_col = getattr(EventRecord, "idempotency_key", None)
            if idemp_col is None:
                raise IdempotencyStartupValidationError(
                    "EventRecord model is missing the 'idempotency_key' column."
                )
            if not getattr(idemp_col, "unique", False):
                raise IdempotencyStartupValidationError(
                    "EventRecord.idempotency_key must have unique=True constraint defined."
                )
        except Exception as exc:
            raise IdempotencyStartupValidationError(
                f"Event Store unique constraint validation failed: {exc}"
            ) from exc

        # 4. Validate Replay Bypass Configuration
        try:
            decision = IdempotencyDecision(
                action=IdempotencyAction.REPLAY_BYPASS,
                key="test_replay_key",
                reason="Test bypass validation",
            )
            if not decision.is_persisted or decision.is_duplicate:
                raise IdempotencyStartupValidationError(
                    "IdempotencyDecision REPLAY_BYPASS logic is invalid."
                )
        except Exception as exc:
            raise IdempotencyStartupValidationError(
                f"Replay bypass configuration validation failed: {exc}"
            ) from exc

        # 5. Validate Duplicate Resolution Handler Actions
        try:
            dup_decision = IdempotencyDecision(
                action=IdempotencyAction.DUPLICATE,
                key="test_dup_key",
                reason="Test duplicate validation",
            )
            race_decision = IdempotencyDecision(
                action=IdempotencyAction.RACE_RECOVERED,
                key="test_race_key",
                reason="Test race validation",
            )
            if not dup_decision.is_duplicate or not race_decision.is_duplicate:
                raise IdempotencyStartupValidationError(
                    "Duplicate resolution handler decision contracts are invalid."
                )
        except Exception as exc:
            raise IdempotencyStartupValidationError(
                f"Duplicate handler validation failed: {exc}"
            ) from exc

        logger.info("idempotency_subsystems_validated_successfully")
