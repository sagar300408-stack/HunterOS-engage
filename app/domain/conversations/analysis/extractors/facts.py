"""
HunterOS Engage — Key Fact Extractors (Phase 2.2.1)

Implements deterministic extractors for all structured fact categories:
- Customer Information
- Company Information
- Product References
- Property References
- Budget References
- Date References
- Location References
- Contact Information
- Documents Mentioned
- Custom Facts
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional

from app.domain.conversations.analysis.extractors.base import AbstractFactExtractor
from app.domain.conversations.analysis.models import (
    ArtifactProvenance,
    CanonicalValue,
    ExtractedFact,
    ExtractionMethod,
    FactCategory,
    NormalizedMessage,
    SourceMessageRef,
)


class ContactInfoExtractor(AbstractFactExtractor):
    """Extracts email addresses and phone numbers."""

    @property
    def target_category(self) -> FactCategory:
        return FactCategory.CONTACT_INFO

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        seen_values = set()

        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        phone_pattern = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"

        for msg in messages:
            content = msg.cleaned_content

            # Emails
            for email in re.findall(email_pattern, content):
                if email.lower() not in seen_values:
                    seen_values.add(email.lower())
                    facts.append(
                        ExtractedFact(
                            category=FactCategory.CONTACT_INFO,
                            key="email_address",
                            raw_value=email,
                            canonical_value=CanonicalValue(
                                raw_value=email,
                                normalized_value=email.lower().strip(),
                                data_type="email",
                                formatted=email.lower().strip(),
                            ),
                            provenance=ArtifactProvenance(
                                pipeline_stage="FactExtractionStage",
                                confidence=1.0,
                                source_messages=[
                                    SourceMessageRef(
                                        message_id=msg.id,
                                        timestamp=msg.timestamp,
                                        text_snippet=content[:80],
                                    )
                                ],
                                extraction_method=ExtractionMethod.PATTERN_MATCHER,
                            ),
                        )
                    )

            # Phones
            for match in re.finditer(phone_pattern, content):
                phone_raw = match.group(0).strip()
                digits_only = re.sub(r"\D", "", phone_raw)
                # Valid phone number length heuristic
                if 7 <= len(digits_only) <= 15 and phone_raw not in seen_values:
                    seen_values.add(phone_raw)
                    facts.append(
                        ExtractedFact(
                            category=FactCategory.CONTACT_INFO,
                            key="phone_number",
                            raw_value=phone_raw,
                            canonical_value=CanonicalValue(
                                raw_value=phone_raw,
                                normalized_value=digits_only,
                                data_type="phone",
                                formatted=phone_raw,
                            ),
                            provenance=ArtifactProvenance(
                                pipeline_stage="FactExtractionStage",
                                confidence=0.95,
                                source_messages=[
                                    SourceMessageRef(
                                        message_id=msg.id,
                                        timestamp=msg.timestamp,
                                        text_snippet=content[:80],
                                    )
                                ],
                                extraction_method=ExtractionMethod.PATTERN_MATCHER,
                            ),
                        )
                    )
        return facts


class BudgetExtractor(AbstractFactExtractor):
    """Extracts budgets, price references, and currency amounts."""

    @property
    def target_category(self) -> FactCategory:
        return FactCategory.BUDGET_REFERENCE

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        seen = set()

        patterns = [
            # e.g., ₹85 lakh, Rs. 1.5 Cr, INR 75,00,000, 85L, 2.5 Crore
            r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lac|l|crores?|cr)?\b",
            r"\b([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lac|crores?|cr)\b",
            # e.g., $50,000, 50k USD, €200,000, 100k GBP, 50000 AED
            r"(?:\$|€|£|AED|USD|EUR|GBP)\s*([\d,]+(?:\.\d+)?)\s*(?:k|m|million)?\b",
            r"\b([\d,]+(?:\.\d+)?)\s*(?:k|m|million)\s*(?:USD|EUR|GBP|INR|AED|\$|€|£)?\b",
            r"\bbudget\s*(?:is|of|around|approx)?\s*[:=]?\s*([^\n,.]+)",
        ]

        for msg in messages:
            content = msg.cleaned_content
            for pat in patterns:
                for match in re.finditer(pat, content, flags=re.IGNORECASE):
                    full_span = match.group(0).strip()
                    if full_span.lower() not in seen and len(full_span) > 1:
                        seen.add(full_span.lower())
                        facts.append(
                            ExtractedFact(
                                category=FactCategory.BUDGET_REFERENCE,
                                key="budget_amount",
                                raw_value=full_span,
                                canonical_value=CanonicalValue(
                                    raw_value=full_span,
                                    normalized_value=full_span,
                                    data_type="currency",
                                ),
                                provenance=ArtifactProvenance(
                                    pipeline_stage="FactExtractionStage",
                                    confidence=0.9,
                                    source_messages=[
                                        SourceMessageRef(
                                            message_id=msg.id,
                                            timestamp=msg.timestamp,
                                            text_snippet=content[:80],
                                        )
                                    ],
                                    extraction_method=ExtractionMethod.PATTERN_MATCHER,
                                ),
                            )
                        )
        return facts


class PropertyExtractor(AbstractFactExtractor):
    """Extracts real estate property types, configurations, and dimensions."""

    @property
    def target_category(self) -> FactCategory:
        return FactCategory.PROPERTY_REFERENCE

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        seen = set()

        patterns = [
            # e.g., 3 BHK, 2BHK, 4-bedroom villa, studio apartment, penthouse
            r"\b(\d\s*[- ]?BHK|\d\s*[- ]?bedroom(?:\s+(?:apartment|villa|flat|house))?)\b",
            r"\b(villa|penthouse|studio apartment|commercial plot|office space|residential plot|duplex)\b",
            # e.g., 1500 sqft, 2200 sq.ft, 120 sq yards
            r"\b(\d+(?:,\d+)?\s*(?:sq\.?\s*ft|sqft|square feet|sq\s*meters|sq\s*yards))\b",
        ]

        for msg in messages:
            content = msg.cleaned_content
            for pat in patterns:
                for match in re.finditer(pat, content, flags=re.IGNORECASE):
                    val = match.group(0).strip()
                    if val.lower() not in seen:
                        seen.add(val.lower())
                        facts.append(
                            ExtractedFact(
                                category=FactCategory.PROPERTY_REFERENCE,
                                key="property_specification",
                                raw_value=val,
                                canonical_value=CanonicalValue(
                                    raw_value=val,
                                    normalized_value=val.upper() if "bhk" in val.lower() else val.title(),
                                    data_type="property_spec",
                                    formatted=val,
                                ),
                                provenance=ArtifactProvenance(
                                    pipeline_stage="FactExtractionStage",
                                    confidence=0.95,
                                    source_messages=[
                                        SourceMessageRef(
                                            message_id=msg.id,
                                            timestamp=msg.timestamp,
                                            text_snippet=content[:80],
                                        )
                                    ],
                                    extraction_method=ExtractionMethod.PATTERN_MATCHER,
                                ),
                            )
                        )
        return facts


class LocationExtractor(AbstractFactExtractor):
    """Extracts cities, sectors, and location references."""

    @property
    def target_category(self) -> FactCategory:
        return FactCategory.LOCATION_REFERENCE

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        seen = set()

        patterns = [
            r"\b(?:in|at|near|around|located in|area of)\s+([A-Z][a-zA-Z0-9\s,-]+?)(?:\.|\,|$|\b(?:for|with|and|is)\b)",
            r"\b(Bangalore|Mumbai|Delhi|Gurgaon|Noida|Hyderabad|Pune|Chennai|Dubai|London|New York|San Francisco|Sector\s*\d+[A-Za-z]?|Whitefield|Koramangala|Indiranagar|HSR Layout|Bandra|BKC)\b",
        ]

        for msg in messages:
            content = msg.cleaned_content
            for pat in patterns:
                for match in re.finditer(pat, content, flags=re.IGNORECASE):
                    loc_val = match.group(1).strip() if match.groups() else match.group(0).strip()
                    if loc_val.lower() not in seen and len(loc_val) > 2:
                        seen.add(loc_val.lower())
                        facts.append(
                            ExtractedFact(
                                category=FactCategory.LOCATION_REFERENCE,
                                key="location",
                                raw_value=loc_val,
                                canonical_value=CanonicalValue(
                                    raw_value=loc_val,
                                    normalized_value=loc_val.title(),
                                    data_type="location",
                                    formatted=loc_val.title(),
                                ),
                                provenance=ArtifactProvenance(
                                    pipeline_stage="FactExtractionStage",
                                    confidence=0.88,
                                    source_messages=[
                                        SourceMessageRef(
                                            message_id=msg.id,
                                            timestamp=msg.timestamp,
                                            text_snippet=content[:80],
                                        )
                                    ],
                                    extraction_method=ExtractionMethod.PATTERN_MATCHER,
                                ),
                            )
                        )
        return facts


class DateExtractor(AbstractFactExtractor):
    """Extracts date and time coordination references."""

    @property
    def target_category(self) -> FactCategory:
        return FactCategory.DATE_REFERENCE

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        seen = set()

        patterns = [
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?:\s+\d{4})?)\b",
            r"\b(tomorrow|next week|next Monday|next Tuesday|next Wednesday|next Thursday|next Friday|next Saturday|next Sunday|this weekend|by Monday|by Friday)\b",
            r"\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\b",
        ]

        for msg in messages:
            content = msg.cleaned_content
            for pat in patterns:
                for match in re.finditer(pat, content, flags=re.IGNORECASE):
                    val = match.group(0).strip()
                    if val.lower() not in seen:
                        seen.add(val.lower())
                        facts.append(
                            ExtractedFact(
                                category=FactCategory.DATE_REFERENCE,
                                key="date_reference",
                                raw_value=val,
                                canonical_value=CanonicalValue(
                                    raw_value=val,
                                    normalized_value=val,
                                    data_type="date",
                                    formatted=val,
                                ),
                                provenance=ArtifactProvenance(
                                    pipeline_stage="FactExtractionStage",
                                    confidence=0.9,
                                    source_messages=[
                                        SourceMessageRef(
                                            message_id=msg.id,
                                            timestamp=msg.timestamp,
                                            text_snippet=content[:80],
                                        )
                                    ],
                                    extraction_method=ExtractionMethod.PATTERN_MATCHER,
                                ),
                            )
                        )
        return facts


class CompanyInfoExtractor(AbstractFactExtractor):
    """Extracts organization and company mentions."""

    @property
    def target_category(self) -> FactCategory:
        return FactCategory.COMPANY_INFO

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        seen = set()

        patterns = [
            r"\b(?:from|at|with|working at)\s+([A-Z][a-zA-Z0-9\s&.-]+?(?:Inc|LLC|Ltd|Corp|Technologies|Solutions|Group|Enterprises|Systems|Pvt Ltd)?)(?:\.|\,|$|\b(?:and|for)\b)",
            r"\b([A-Z][a-zA-Z0-9\s&.-]+?(?:Inc\.|LLC|Ltd\.|Corp\.|Technologies|Solutions|Group|Enterprises|Systems|Pvt Ltd))\b",
        ]

        for msg in messages:
            content = msg.cleaned_content
            for pat in patterns:
                for match in re.finditer(pat, content):
                    comp_name = match.group(1).strip() if match.groups() else match.group(0).strip()
                    if comp_name.lower() not in seen and len(comp_name) > 3:
                        seen.add(comp_name.lower())
                        facts.append(
                            ExtractedFact(
                                category=FactCategory.COMPANY_INFO,
                                key="company_name",
                                raw_value=comp_name,
                                canonical_value=CanonicalValue(
                                    raw_value=comp_name,
                                    normalized_value=comp_name.strip(),
                                    data_type="company",
                                    formatted=comp_name.strip(),
                                ),
                                provenance=ArtifactProvenance(
                                    pipeline_stage="FactExtractionStage",
                                    confidence=0.85,
                                    source_messages=[
                                        SourceMessageRef(
                                            message_id=msg.id,
                                            timestamp=msg.timestamp,
                                            text_snippet=content[:80],
                                        )
                                    ],
                                    extraction_method=ExtractionMethod.PATTERN_MATCHER,
                                ),
                            )
                        )
        return facts


class CustomerInfoExtractor(AbstractFactExtractor):
    """Extracts customer name introductions and explicit preferences."""

    @property
    def target_category(self) -> FactCategory:
        return FactCategory.CUSTOMER_INFO

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        seen = set()

        patterns = [
            r"\b(?:my name is|i am|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
            r"\b(?:speaking with|reaching out from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        ]

        for msg in messages:
            if msg.direction == "OUTGOING":
                continue  # Only extract customer self-identifications from incoming/customer turns
            content = msg.cleaned_content
            for pat in patterns:
                for match in re.finditer(pat, content, flags=re.IGNORECASE):
                    name_val = match.group(1).strip()
                    if name_val.lower() not in seen and len(name_val) > 2:
                        seen.add(name_val.lower())
                        facts.append(
                            ExtractedFact(
                                category=FactCategory.CUSTOMER_INFO,
                                key="customer_name",
                                raw_value=name_val,
                                canonical_value=CanonicalValue(
                                    raw_value=name_val,
                                    normalized_value=name_val.title(),
                                    data_type="string",
                                    formatted=name_val.title(),
                                ),
                                provenance=ArtifactProvenance(
                                    pipeline_stage="FactExtractionStage",
                                    confidence=0.92,
                                    source_messages=[
                                        SourceMessageRef(
                                            message_id=msg.id,
                                            timestamp=msg.timestamp,
                                            text_snippet=content[:80],
                                        )
                                    ],
                                    extraction_method=ExtractionMethod.PATTERN_MATCHER,
                                ),
                            )
                        )
        return facts


class ProductExtractor(AbstractFactExtractor):
    """Extracts product references and tier designations."""

    @property
    def target_category(self) -> FactCategory:
        return FactCategory.PRODUCT_REFERENCE

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        seen = set()

        patterns = [
            r"\b(HunterOS\s*Engage|Enterprise\s*Plan|Pro\s*Tier|Basic\s*Plan|Starter\s*Tier|API\s*Gateway|CRM\s*Sync)\b",
        ]

        for msg in messages:
            content = msg.cleaned_content
            for pat in patterns:
                for match in re.finditer(pat, content, flags=re.IGNORECASE):
                    prod = match.group(0).strip()
                    if prod.lower() not in seen:
                        seen.add(prod.lower())
                        facts.append(
                            ExtractedFact(
                                category=FactCategory.PRODUCT_REFERENCE,
                                key="product_name",
                                raw_value=prod,
                                canonical_value=CanonicalValue(
                                    raw_value=prod,
                                    normalized_value=prod.title(),
                                    data_type="product",
                                    formatted=prod.title(),
                                ),
                                provenance=ArtifactProvenance(
                                    pipeline_stage="FactExtractionStage",
                                    confidence=0.95,
                                    source_messages=[
                                        SourceMessageRef(
                                            message_id=msg.id,
                                            timestamp=msg.timestamp,
                                            text_snippet=content[:80],
                                        )
                                    ],
                                    extraction_method=ExtractionMethod.PATTERN_MATCHER,
                                ),
                            )
                        )
        return facts


class DocumentMentionExtractor(AbstractFactExtractor):
    """Extracts mentions of files, PDFs, brochures, contracts, and proposals."""

    @property
    def target_category(self) -> FactCategory:
        return FactCategory.DOCUMENT_MENTIONED

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        seen = set()

        patterns = [
            r"\b([a-zA-Z0-9_-]+\.(?:pdf|docx?|xlsx?|csv|png|jpe?g))\b",
            r"\b(brochure|floor\s*plan|master\s*plan|cost\s*sheet|proposal|contract|agreement|invoice|quotation|NDA|SLA)\b",
        ]

        for msg in messages:
            content = msg.cleaned_content
            for pat in patterns:
                for match in re.finditer(pat, content, flags=re.IGNORECASE):
                    doc = match.group(0).strip()
                    if doc.lower() not in seen:
                        seen.add(doc.lower())
                        facts.append(
                            ExtractedFact(
                                category=FactCategory.DOCUMENT_MENTIONED,
                                key="document_reference",
                                raw_value=doc,
                                canonical_value=CanonicalValue(
                                    raw_value=doc,
                                    normalized_value=doc.lower() if "." in doc else doc.title(),
                                    data_type="document",
                                    formatted=doc,
                                ),
                                provenance=ArtifactProvenance(
                                    pipeline_stage="FactExtractionStage",
                                    confidence=0.9,
                                    source_messages=[
                                        SourceMessageRef(
                                            message_id=msg.id,
                                            timestamp=msg.timestamp,
                                            text_snippet=content[:80],
                                        )
                                    ],
                                    extraction_method=ExtractionMethod.PATTERN_MATCHER,
                                ),
                            )
                        )
        return facts


class CustomFactExtractor(AbstractFactExtractor):
    """Generic customizable fact extractor for user-provided patterns."""

    def __init__(self, key: str = "custom_fact", patterns: Optional[List[str]] = None) -> None:
        self._key = key
        self._patterns = patterns or []

    @property
    def target_category(self) -> FactCategory:
        return FactCategory.CUSTOM

    def extract_facts(
        self,
        messages: List[NormalizedMessage],
        context: Optional[Any] = None,
    ) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        if not self._patterns:
            return facts

        seen = set()
        for msg in messages:
            content = msg.cleaned_content
            for pat in self._patterns:
                for match in re.finditer(pat, content, flags=re.IGNORECASE):
                    val = match.group(0).strip()
                    if val.lower() not in seen:
                        seen.add(val.lower())
                        facts.append(
                            ExtractedFact(
                                category=FactCategory.CUSTOM,
                                key=self._key,
                                raw_value=val,
                                canonical_value=CanonicalValue(
                                    raw_value=val,
                                    normalized_value=val,
                                    data_type="custom",
                                    formatted=val,
                                ),
                                provenance=ArtifactProvenance(
                                    pipeline_stage="FactExtractionStage",
                                    confidence=0.85,
                                    source_messages=[
                                        SourceMessageRef(
                                            message_id=msg.id,
                                            timestamp=msg.timestamp,
                                            text_snippet=content[:80],
                                        )
                                    ],
                                    extraction_method=ExtractionMethod.RULE_BASED,
                                ),
                            )
                        )
        return facts
