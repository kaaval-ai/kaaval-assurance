"""Initial task contracts: telecom incident triage, four categories.

These four cover the eval harness categories (4 strategies x ~60 telecom-triage
requests later in the week). Versioned so Layer 2 trends and Layer 3 audits can
reference exactly which contract a response was judged against.
"""

from .base import FieldSpec, GroundingRule, TaskContract

SEVERITY_CLASSIFICATION = TaskContract(
    contract_id="telecom.severity_classification",
    version="1.0",
    category="severity_classification",
    description="Classify a telecom incident report into a severity tier.",
    semantic_intent=(
        "The severity label must match the operational impact described in the "
        "incident text. Cascading faults, full-site outages, and safety issues "
        "are P1; degraded-but-serving is P2/P3; cosmetic or informational is P4. "
        "The rationale must cite evidence from the incident text, not generic "
        "boilerplate, and confidence must reflect genuine ambiguity."
    ),
    fields=[
        FieldSpec(name="severity", type="string", enum=["P1", "P2", "P3", "P4"]),
        FieldSpec(name="confidence", type="number", min_value=0.0, max_value=1.0),
        FieldSpec(name="rationale", type="string"),
    ],
    grounding_rules=[
        GroundingRule(
            id="regional_outage_requires_p1",
            required_input_phrases=[
                "all BGP sessions",
                "lost upstream connectivity",
                "customer impact",
            ],
            output_field="severity",
            allowed_values=["P1"],
            description=(
                "A full regional outage (all BGP sessions dropped, upstream "
                "connectivity lost) with confirmed customer impact must be "
                "classified P1, not a lower severity."
            ),
        ),
    ],
)

COMPONENT_EXTRACTION = TaskContract(
    contract_id="telecom.component_extraction",
    version="1.0",
    category="component_extraction",
    description="Extract the network components involved in an incident report.",
    semantic_intent=(
        "Every component actually named or unambiguously implied in the incident "
        "text must appear in components; nothing may be invented. "
        "primary_component is the root-cause component, not merely the first "
        "one mentioned. Missing secondary components is a violation."
    ),
    fields=[
        FieldSpec(name="components", type="array", min_items=1),
        FieldSpec(name="primary_component", type="string"),
    ],
)

INCIDENT_SUMMARY = TaskContract(
    contract_id="telecom.incident_summary",
    version="1.0",
    category="incident_summary",
    description="Summarize a telecom incident for a NOC handover note.",
    semantic_intent=(
        "The summary must be faithful to the incident text: no invented causes, "
        "no dropped impact statements. impact states who/what is affected. "
        "affected_services lists only services the text supports; an empty or "
        "speculative list when the text names services is a violation."
    ),
    fields=[
        FieldSpec(name="summary", type="string"),
        FieldSpec(name="impact", type="string"),
        FieldSpec(name="affected_services", type="array", min_items=0),
    ],
)

NEXT_ACTION_RECOMMENDATION = TaskContract(
    contract_id="telecom.next_action_recommendation",
    version="1.0",
    category="next_action_recommendation",
    description="Recommend the next operational action for an ongoing incident.",
    semantic_intent=(
        "The action must be justified by the incident evidence — no unsupported "
        "diagnostic leaps. urgency must be consistent with the stated severity "
        "and customer impact: an outage with customer impact cannot be 'monitor'. "
        "justification must reference the incident facts that drove the choice."
    ),
    fields=[
        FieldSpec(name="action", type="string"),
        FieldSpec(
            name="urgency", type="string", enum=["immediate", "scheduled", "monitor"]
        ),
        FieldSpec(name="justification", type="string"),
    ],
    grounding_rules=[
        GroundingRule(
            id="no_redundancy_requires_immediate",
            required_input_phrases=["no redundancy", "subscribers"],
            output_field="urgency",
            allowed_values=["immediate"],
            description=(
                "An incident with no remaining redundancy affecting subscribers "
                "requires immediate action, not scheduled or monitor."
            ),
        ),
    ],
)

ALL_CONTRACTS = [
    SEVERITY_CLASSIFICATION,
    COMPONENT_EXTRACTION,
    INCIDENT_SUMMARY,
    NEXT_ACTION_RECOMMENDATION,
]
