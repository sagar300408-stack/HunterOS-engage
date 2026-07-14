class StateTransitionError(Exception):
    pass

# scheduled -> executing -> sent
#                        -> scheduled (retry)
#                        -> cancelled (failed)
# scheduled -> cancelled
# sent -> replied

TRANSITIONS = {
    "scheduled": ["executing", "cancelled"],
    "executing": ["sent", "scheduled", "cancelled"],
    "sent": ["replied"],
    "cancelled": [],
    "replied": []
}

def transition(current: str, target: str) -> str:
    if target in TRANSITIONS.get(current, []):
        return target
    raise StateTransitionError(f"Cannot transition from {current} to {target}")

def can_retry(current_attempt: int, max_attempts: int) -> bool:
    return current_attempt < max_attempts
