"""
HunterOS Engage V1 - Business Process Registry
Thread-safe extensible registry for dynamic business processes.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from app.domain.intents.classification.models import BusinessDomain
from app.domain.intents.classification.process.models import BusinessProcessDefinition


class BusinessProcessRegistry:
    """
    Registry for business processes.
    Allows industries (e.g. Healthcare, Insurance, Real Estate) to register customized processes dynamically.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._processes: Dict[str, BusinessProcessDefinition] = {}
        self._initialize_defaults()

    def register(self, definition: BusinessProcessDefinition) -> None:
        """Register or override a business process definition."""
        with self._lock:
            self._processes[definition.process_id] = definition

    def get(self, process_id: str) -> Optional[BusinessProcessDefinition]:
        """Look up a process by ID."""
        with self._lock:
            return self._processes.get(process_id)

    def list_all(self) -> List[BusinessProcessDefinition]:
        """List all registered business processes."""
        with self._lock:
            return list(self._processes.values())

    def list_by_domain(self, domain: BusinessDomain) -> List[BusinessProcessDefinition]:
        """Filter processes by business domain."""
        with self._lock:
            return [
                p for p in self._processes.values()
                if p.business_domain in (domain, BusinessDomain.CROSS_INDUSTRY)
            ]

    def _initialize_defaults(self) -> None:
        """Seed default cross-industry and initial domain processes."""
        defaults = [
            BusinessProcessDefinition(
                process_id="LEAD_CAPTURE",
                name="Lead Capture & Inbound Discovery",
                description="Initial contact, greeting, and preliminary customer requirements collection.",
                sla_target_hours=2.0,
            ),
            BusinessProcessDefinition(
                process_id="SALES_QUALIFICATION",
                name="Sales Qualification & Budget Bounds",
                description="Evaluating purchasing capability, price range, and intent alignment.",
                sla_target_hours=4.0,
            ),
            BusinessProcessDefinition(
                process_id="DEAL_CLOSING",
                name="Deal Negotiation & Closing",
                description="Commercial negotiation, terms agreement, and booking finalization.",
                sla_target_hours=24.0,
            ),
            BusinessProcessDefinition(
                process_id="APPOINTMENT_SCHEDULING",
                name="Appointment & Visit Scheduling",
                description="Scheduling meetings, site visits, and consultation calls.",
                sla_target_hours=6.0,
            ),
            BusinessProcessDefinition(
                process_id="DOCUMENT_FULFILLMENT",
                name="Document & Collateral Fulfillment",
                description="Dispatching brochures, floor plans, rate lists, and contracts.",
                sla_target_hours=1.0,
            ),
            BusinessProcessDefinition(
                process_id="CUSTOMER_ONBOARDING",
                name="Customer Onboarding",
                description="Welcoming newly booked customers and initiating onboarding workflows.",
                sla_target_hours=12.0,
            ),
            BusinessProcessDefinition(
                process_id="CUSTOMER_SUPPORT",
                name="Customer Service & Issue Resolution",
                description="Handling complaints, service tickets, and operational assistance.",
                sla_target_hours=4.0,
            ),
            BusinessProcessDefinition(
                process_id="RETENTION_RELATIONSHIP",
                name="Relationship Management & Retention",
                description="Managing referrals, partnership inquiries, and loyalty engagement.",
                sla_target_hours=48.0,
            ),
            BusinessProcessDefinition(
                process_id="GENERAL_DISCOVERY",
                name="General Information Discovery",
                description="Broad educational or informational inquiries.",
                sla_target_hours=24.0,
            ),
            # Industry examples
            BusinessProcessDefinition(
                process_id="INSURANCE_CLAIMS",
                name="Insurance Claim Processing",
                description="First notice of loss, documentation, and policy validation.",
                business_domain=BusinessDomain.FINANCIAL_SERVICES,
                sla_target_hours=8.0,
            ),
            BusinessProcessDefinition(
                process_id="HEALTHCARE_INTAKE",
                name="Patient Intake & Triage",
                description="Medical consultation booking, symptom assessment, and record collection.",
                business_domain=BusinessDomain.HEALTHCARE,
                sla_target_hours=1.0,
            ),
            BusinessProcessDefinition(
                process_id="MANUFACTURING_PROCUREMENT",
                name="Procurement & RFP Quoting",
                description="B2B supplier inquiries, specifications, and volume pricing requests.",
                business_domain=BusinessDomain.MANUFACTURING,
                sla_target_hours=48.0,
            ),
        ]
        for d in defaults:
            self.register(d)


default_business_process_registry = BusinessProcessRegistry()
