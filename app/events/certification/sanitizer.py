"""
HunterOS Engage — Sensitive Data & PII Sanitizer
app/events/certification/sanitizer.py

Recursively masks credentials, tokens, secrets, authorization headers,
and personal identifiable information (PII) from event payloads,
trace spans, metadata, and error stack traces before storage or telemetry export.
"""

import re
from typing import Any, Dict, List, Set, Union
from app.events.certification.config import certification_config


class SensitiveDataSanitizer:
    """
    High-performance recursive data sanitizer.
    """

    MASK_VALUE = "[REDACTED]"

    def __init__(self, sensitive_keys: Union[List[str], Set[str], None] = None):
        keys = sensitive_keys or certification_config.sensitive_keys
        self._sensitive_patterns = [
            re.compile(rf".*{re.escape(k)}.*", re.IGNORECASE) for k in keys
        ]
        # Regex patterns for inline strings (e.g. Bearer tokens, credit card digits)
        self._bearer_regex = re.compile(r"Bearer\s+([A-Za-z0-9\-\._~\+\/]+=*)", re.IGNORECASE)
        self._credit_card_regex = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

    def is_sensitive_key(self, key_name: str) -> bool:
        """Check if a dictionary key contains sensitive identifiers."""
        key_str = str(key_name).lower()
        return any(pattern.match(key_str) for pattern in self._sensitive_patterns)

    def sanitize_string(self, text: str) -> str:
        """Mask sensitive substrings within raw string values."""
        if not text:
            return text
        sanitized = self._bearer_regex.sub("Bearer [REDACTED_TOKEN]", text)
        sanitized = self._credit_card_regex.sub("[REDACTED_CARD]", sanitized)
        return sanitized

    def sanitize(self, data: Any) -> Any:
        """
        Recursively traverse dictionaries, lists, and primitives, masking sensitive fields.
        """
        if isinstance(data, dict):
            sanitized_dict: Dict[str, Any] = {}
            for k, v in data.items():
                if self.is_sensitive_key(str(k)):
                    sanitized_dict[k] = self.MASK_VALUE
                else:
                    sanitized_dict[k] = self.sanitize(v)
            return sanitized_dict
        elif isinstance(data, list):
            return [self.sanitize(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self.sanitize(item) for item in data)
        elif isinstance(data, set):
            return {self.sanitize(item) for item in data}
        elif isinstance(data, str):
            return self.sanitize_string(data)
        else:
            return data


# Global sanitizer singleton
data_sanitizer = SensitiveDataSanitizer()
