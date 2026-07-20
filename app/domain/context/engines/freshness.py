from datetime import datetime, timezone
from typing import Any, Tuple

class ContextFreshnessEngine:
    """
    Detects stale knowledge that requires re-verification.
    """

    @classmethod
    def evaluate(cls, entity: Any) -> Tuple[bool, int]:
        """
        Returns (is_stale, days_since_verified)
        """
        last_verified = getattr(entity, 'last_verified_at', None)
        threshold = getattr(entity, 'stale_threshold_days', 90)
        
        if not last_verified:
            return True, 999
            
        days_since = (datetime.now(timezone.utc) - last_verified).days
        is_stale = days_since > threshold
        
        return is_stale, days_since
