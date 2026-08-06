"""
HunterOS Engage — Fact Normalizer Layer (Phase 2.2.1)

Provides canonical transformation for extracted raw facts, standardizing currencies,
numbers, units, phone numbers, dates, emails, and identifiers into canonical representations.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from app.domain.conversations.analysis.models import (
    CanonicalValue,
    ExtractedFact,
    FactCategory,
)


class FactNormalizer:
    """
    Transforms extracted raw facts into structured CanonicalValue representations
    so that downstream intelligence modules always receive uniform, standardized data.
    """

    def normalize(self, fact: ExtractedFact) -> ExtractedFact:
        """Process a single fact and return updated fact with canonical value."""
        cat = fact.category
        raw = str(fact.raw_value).strip()

        if cat == FactCategory.BUDGET_REFERENCE:
            canonical = self._normalize_currency(raw)
        elif cat == FactCategory.CONTACT_INFO:
            if "@" in raw:
                canonical = self._normalize_email(raw)
            else:
                canonical = self._normalize_phone(raw)
        elif cat == FactCategory.DATE_REFERENCE:
            canonical = self._normalize_date(raw)
        elif cat == FactCategory.PROPERTY_REFERENCE:
            canonical = self._normalize_property(raw)
        else:
            canonical = CanonicalValue(
                raw_value=fact.raw_value,
                normalized_value=raw,
                data_type="string",
                formatted=raw,
            )

        # Return a new fact instance with updated canonical value
        return ExtractedFact(
            fact_id=fact.fact_id,
            category=fact.category,
            key=fact.key,
            raw_value=fact.raw_value,
            canonical_value=canonical,
            provenance=fact.provenance,
            metadata=fact.metadata,
        )

    def _normalize_currency(self, text: str) -> CanonicalValue:
        """
        Normalize currency strings (e.g. '₹85 lakh' -> 8500000 INR, '$50,000' -> 50000 USD).
        """
        # 1. Detect currency
        currency = "INR"  # default
        if "$" in text or "usd" in text.lower():
            currency = "USD"
        elif "€" in text or "eur" in text.lower():
            currency = "EUR"
        elif "£" in text or "gbp" in text.lower():
            currency = "GBP"
        elif "aed" in text.lower():
            currency = "AED"
        elif "₹" in text or "rs" in text.lower() or "inr" in text.lower() or "lakh" in text.lower() or "cr" in text.lower():
            currency = "INR"

        # 2. Extract number and multiplier
        clean_text = text.lower().replace(",", "")
        
        # Match number part
        num_match = re.search(r"(\d+(?:\.\d+)?)", clean_text)
        if not num_match:
            return CanonicalValue(
                raw_value=text,
                normalized_value=text,
                data_type="currency",
                unit=currency,
                formatted=text,
            )

        num_val = float(num_match.group(1))

        # Check multipliers
        if "crore" in clean_text or "cr" in clean_text:
            num_val *= 10000000
        elif "lakh" in clean_text or "lac" in clean_text or " l " in f" {clean_text} " or clean_text.endswith("l"):
            num_val *= 100000
        elif "million" in clean_text or "m" in clean_text:
            num_val *= 1000000
        elif "k" in clean_text or "thousand" in clean_text:
            num_val *= 1000

        # Integer if whole number
        final_amount: Any = int(num_val) if num_val.is_integer() else num_val
        formatted_str = f"{final_amount:,.0f} {currency}" if isinstance(final_amount, int) else f"{final_amount:,.2f} {currency}"

        return CanonicalValue(
            raw_value=text,
            normalized_value=final_amount,
            data_type="currency",
            unit=currency,
            formatted=formatted_str,
        )

    def _normalize_phone(self, text: str) -> CanonicalValue:
        """Normalize phone numbers to standard format."""
        digits = re.sub(r"\D", "", text)
        if len(digits) == 10:
            # Assume India if 10 digits
            formatted = f"+91{digits}"
        elif text.strip().startswith("+"):
            formatted = f"+{digits}"
        else:
            formatted = f"+{digits}"

        return CanonicalValue(
            raw_value=text,
            normalized_value=digits,
            data_type="phone",
            unit="E.164",
            formatted=formatted,
        )

    def _normalize_email(self, text: str) -> CanonicalValue:
        """Normalize email addresses to lowercased trimmed strings."""
        clean = text.lower().strip()
        return CanonicalValue(
            raw_value=text,
            normalized_value=clean,
            data_type="email",
            formatted=clean,
        )

    def _normalize_date(self, text: str) -> CanonicalValue:
        """Normalize date strings to canonical representations."""
        clean = text.strip()
        # ISO match (YYYY-MM-DD)
        iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", clean)
        if iso_match:
            iso_str = iso_match.group(1)
            return CanonicalValue(
                raw_value=text,
                normalized_value=iso_str,
                data_type="date",
                unit="ISO8601",
                formatted=iso_str,
            )

        return CanonicalValue(
            raw_value=text,
            normalized_value=clean.title(),
            data_type="date",
            formatted=clean.title(),
        )

    def _normalize_property(self, text: str) -> CanonicalValue:
        """Normalize property spec strings (e.g. 3bhk -> 3 BHK)."""
        clean = text.strip()
        bhk_match = re.search(r"(\d)\s*[- ]?bhk", clean, flags=re.IGNORECASE)
        if bhk_match:
            bhk_formatted = f"{bhk_match.group(1)} BHK"
            return CanonicalValue(
                raw_value=text,
                normalized_value=bhk_formatted,
                data_type="property_spec",
                formatted=bhk_formatted,
            )

        return CanonicalValue(
            raw_value=text,
            normalized_value=clean.title(),
            data_type="property_spec",
            formatted=clean.title(),
        )


# Global default instance
default_fact_normalizer = FactNormalizer()
