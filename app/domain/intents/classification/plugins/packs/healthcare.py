"""
HunterOS Engage V1 - Healthcare Industry Plugin
"""

from __future__ import annotations

from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)
from app.domain.intents.classification.plugins.base import IndustryIntentPlugin
from app.domain.intents.classification.process.models import BusinessProcessDefinition
from app.domain.intents.classification.rules.packs.healthcare import (
    HealthcareClassificationRulePack,
)
from app.domain.intents.classification.taxonomy.models import (
    TaxonomyEdge,
    TaxonomyNode,
)


def create_healthcare_plugin() -> IndustryIntentPlugin:
    nodes = [
        TaxonomyNode(
            node_id="operational.doctor_appointment",
            category=IntentCategory.OPERATIONAL,
            display_name="Doctor Appointment",
            description="Consultation appointment with medical specialist or general physician.",
            business_domain=BusinessDomain.HEALTHCARE,
            default_process="HEALTHCARE_INTAKE",
            aliases=["DOCTOR_APPOINTMENT", "PATIENT_INTAKE"],
        ),
    ]
    edges = [
        TaxonomyEdge(source_node_id="operational", target_node_id="operational.doctor_appointment"),
    ]
    processes = [
        BusinessProcessDefinition(
            process_id="HEALTHCARE_INTAKE",
            name="Patient Intake & Triage",
            description="Patient symptom intake, triage, and physician matching.",
            business_domain=BusinessDomain.HEALTHCARE,
            sla_target_hours=1.0,
        )
    ]
    return IndustryIntentPlugin(
        plugin_id="healthcare",
        name="Healthcare Industry Plugin",
        version="1.0.0",
        description="Healthcare intent taxonomy, rules, and patient triage workflows.",
        business_domain=BusinessDomain.HEALTHCARE,
        taxonomy_nodes=nodes,
        taxonomy_edges=edges,
        rule_pack=HealthcareClassificationRulePack(version="1.0.0"),
        business_processes=processes,
    )
