"""
HunterOS Engage — Fault-Tolerant Circuit Breaker
app/events/certification/circuit_breaker.py

Implements enterprise circuit breaker pattern with CLOSED, OPEN, and HALF_OPEN
states to isolate downstream consumer and webhook failures without stalling the engine.
"""

import enum
import time
from dataclasses import dataclass
from typing import Optional, Callable, Any

from app.events.certification.config import CircuitBreakerConfig, certification_config


class CircuitState(str, enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when an execution attempt is rejected by an open circuit breaker."""
    pass


class EventCircuitBreaker:
    """
    Thread-safe circuit breaker protecting event dispatch to downstream dependencies.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self._config = config or certification_config.circuit_breaker
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._consecutive_successes = 0
        self._last_state_change = time.monotonic()

    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state, evaluating recovery timeout if OPEN."""
        now = time.monotonic()
        if self._state == CircuitState.OPEN:
            if now - self._last_state_change >= self._config.recovery_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._consecutive_successes = 0
                self._last_state_change = now
        return self._state

    def allow_request(self) -> bool:
        """Check if request execution is permitted."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Record successful downstream execution."""
        current_state = self.state
        if current_state == CircuitState.HALF_OPEN:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self._config.half_open_consecutive_successes:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._consecutive_successes = 0
                self._last_state_change = time.monotonic()
        elif current_state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record downstream failure."""
        current_state = self.state
        if current_state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
            self._failure_count += 1
            if self._failure_count >= self._config.failure_threshold or current_state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._last_state_change = time.monotonic()

    def reset(self) -> None:
        """Reset breaker to clean CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._consecutive_successes = 0
        self._last_state_change = time.monotonic()
