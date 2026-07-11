"""Mock-only reproducible demo: grounding catch -> recovery -> EWMA closure.

Zero cloud access: MockProvider both tiers, in-memory SQLite. Walks one
regional-outage stress case through three equivalent requests to show the
deterministic Layer 1 grounding-rule engine catching an operationally
under-severe answer, the router recovering it via escalation, and the
online Layer-2 EWMA closure adapting routing after repeated local failures.

    python -m kaaval_assurance.grounding_ewma_demo

`undersevere` is a mock-tier-only failure mode (see providers/mock.py) used
here purely to exercise the catch/recover/adapt path deterministically. It
does not represent real Gemma model behavior.
"""

import json

from .eval.dataset import load_dataset
from .pipeline import AssurancePipeline
from .providers import MockProvider
from .router import Router
from .trajectory import TrajectoryStore

STRESS_DATASET = "data/eval/telecom_stress.jsonl"
CASE_ID = "sev-stress-001"
CATEGORY = "severity_classification"


def run_demo() -> int:
    cases = {c.case_id: c for c in load_dataset(STRESS_DATASET)}
    case = cases[CASE_ID]

    store = TrajectoryStore(":memory:")
    try:
        router = Router()
        pipeline = AssurancePipeline(
            router=router,
            local_provider=MockProvider(tier="local", failure_mode="undersevere"),
            remote_provider=MockProvider(tier="remote", model_id="mock-remote-strong"),
            store=store,
        )

        print("kaaval-assurance mock-only demo: grounding catch -> recovery -> "
              "EWMA routing adaptation")
        print(f"case: {case.case_id} ({case.contract_id}) | local tier: mock "
              "(failure_mode=undersevere)")
        print()

        print("[1] first request: local mock tier returns a structurally valid "
              "but under-severe P2 for a full regional outage")
        r1 = pipeline.handle_request(case.task_input, case.contract_id, request_id="demo-1")
        local_row_1, remote_row_1 = store.rows_for_request("demo-1")
        print(f"    local Layer 1 result: {'pass' if local_row_1.verifier_passed else 'FAIL'} "
              f"({', '.join(local_row_1.verifier_failures)})")
        print(f"    routing reason: {r1.routing.reason}")
        remote_severity = json.loads(remote_row_1.raw_text).get("severity")
        print(f"    escalated to remote mock tier -> "
              f"{'pass' if remote_row_1.verifier_passed else 'FAIL'} "
              f"(severity={remote_severity})")
        print(f"    final verification: {r1.verification.passed} (attempts={r1.attempts})")
        print(f"    online EWMA drift ({CATEGORY}): {router.online_drift_for(CATEGORY):.2f}")
        print()

        print("[2] second equivalent request: local mock tier fails the same way again")
        r2 = pipeline.handle_request(case.task_input, case.contract_id, request_id="demo-2")
        print(f"    routing reason: {r2.routing.reason}")
        print(f"    final verification: {r2.verification.passed} (attempts={r2.attempts})")
        print(f"    online EWMA drift ({CATEGORY}): {router.online_drift_for(CATEGORY):.2f}")
        print(f"    current policy: {router.current_policy_for(CATEGORY).action}")
        print()

        print("[3] third equivalent request: category now pre-routes to remote")
        r3 = pipeline.handle_request(case.task_input, case.contract_id, request_id="demo-3")
        print(f"    routing reason: {r3.routing.reason}")
        print(f"    response tier: {r3.response.tier} (attempts={r3.attempts})")
        print(f"    final verification: {r3.verification.passed}")
        print()

        print("summary:")
        print(f"    grounding check that caught the under-severe mock answer: "
              f"grounding:regional_outage_requires_p1")
        print(f"    drift trajectory: 0.00 -> {router.online_drift_for(CATEGORY):.2f} "
              "(0.30 after request 1, 0.51 after request 2)")
        print(f"    final routing policy for {CATEGORY}: "
              f"{router.current_policy_for(CATEGORY).action}")
        print("    every response above came from the deterministic mock local/remote "
              "tiers only; no network provider was invoked.")
        return 0
    finally:
        store.close()


def main() -> int:
    return run_demo()


if __name__ == "__main__":
    raise SystemExit(main())
