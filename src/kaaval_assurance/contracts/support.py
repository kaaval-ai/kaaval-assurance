"""Generic customer-support task contracts, second domain alongside telecom.

Two contracts chosen because every reviewer has lived them: triaging a
support ticket, and deciding a refund under a policy cap. Layer 1 enforces
the output shape, enum/range constraints, and a small set of explicit
phrase-triggered rules. It does not pretend to be a full policy engine.
"""

from .base import FieldSpec, GroundingRule, TaskContract

TICKET_TRIAGE = TaskContract(
    contract_id="support.ticket_triage",
    version="1.0",
    category="ticket_triage",
    description="Triage a customer support ticket into a priority tier.",
    semantic_intent=(
        "The priority must match the customer and business impact described in "
        "the ticket, not the customer's tone. A calm report of a total outage or "
        "a security concern is urgent; an angry complaint about a cosmetic issue "
        "is not. When one ticket contains several issues, priority follows the "
        "most impactful one. The rationale must cite the ticket's facts, and "
        "confidence must reflect genuine ambiguity."
    ),
    fields=[
        FieldSpec(
            name="priority",
            type="string",
            enum=["urgent", "high", "normal", "low"],
        ),
        FieldSpec(name="confidence", type="number", min_value=0.0, max_value=1.0),
        FieldSpec(name="rationale", type="string"),
    ],
)

REFUND_DECISION = TaskContract(
    contract_id="support.refund_decision",
    version="1.0",
    category="refund_decision",
    description=(
        "Decide a refund request under policy: approve, deny, or escalate to a "
        "human. Approved amounts are capped by policy at $500."
    ),
    semantic_intent=(
        "The decision must follow the refund policy evidenced in the request, "
        "never the emotional pressure of the message. The refunded amount must "
        "be supported by the purchase facts in the text — inventing or inflating "
        "an amount is a violation. Requests above the $500 policy cap, or with "
        "missing/contradictory purchase evidence, must be escalated to a human, "
        "not approved. deny requires citing the policy reason. The justification "
        "must reference the specific facts that drove the decision."
    ),
    fields=[
        FieldSpec(
            name="decision",
            type="string",
            enum=["approve", "deny", "escalate_to_human"],
        ),
        # The policy cap is the contract: no accepted answer can approve more
        # than $500, regardless of what the model generates.
        FieldSpec(
            name="refund_amount_usd", type="number", min_value=0.0, max_value=500.0
        ),
        FieldSpec(name="justification", type="string"),
    ],
    grounding_rules=[
        GroundingRule(
            id="missing_purchase_evidence_requires_human",
            required_input_phrases=[
                "No order number",
                "no amount",
                "no date",
                "doesn't match any purchase record",
            ],
            output_field="decision",
            allowed_values=["escalate_to_human"],
            description=(
                "A refund request with no verifiable purchase identifiers must "
                "not be approved or denied automatically."
            ),
        ),
        GroundingRule(
            id="consequential_damages_requires_human",
            required_input_phrases=["$12,000", "$2,500"],
            output_field="decision",
            allowed_values=["escalate_to_human"],
            description=(
                "Consequential-damages claims above the policy cap require "
                "human review, even if the model proposes a capped amount."
            ),
        ),
        GroundingRule(
            id="outside_refund_window_requires_denial",
            required_input_phrases=["11 months ago", "refunds within 30 days"],
            output_field="decision",
            allowed_values=["deny"],
            description="Requests outside the stated 30-day refund window are denied.",
        ),
    ],
)

ALL_CONTRACTS = [
    TICKET_TRIAGE,
    REFUND_DECISION,
]
