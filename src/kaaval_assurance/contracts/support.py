"""Generic customer-support task contracts, second domain alongside telecom.

Two contracts chosen because every reviewer has lived them: triaging a
support ticket, and deciding a refund under a policy cap. The refund cap is
the demo's sharpest line — the contract's numeric range IS the business
policy, enforced deterministically before any answer is accepted.
"""

from .base import FieldSpec, TaskContract

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
)

ALL_CONTRACTS = [
    TICKET_TRIAGE,
    REFUND_DECISION,
]
