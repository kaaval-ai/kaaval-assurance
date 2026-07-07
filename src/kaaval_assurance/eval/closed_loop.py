"""Closed-loop routing demo: drift detected -> routing tightens -> quality holds.

Three phases over the same gold dataset and trajectory store, mock local tier:

  A  healthy local tier      -> low drift everywhere, all-local routing
  B  local tier degrades     -> Layer-1 failures escalate, drift rises in the
                                affected categories, router still on defaults
  C  policy applied          -> affected categories pre-route to the remote
                                tier; unaffected categories stay local-first

The policy step between B and C is routing_policy.policy_from_drift over
phase-B per-category EWMA drift — deterministic, no model involvement.
"""

import uuid

from pydantic import BaseModel

from ..metrics import DEFAULT_EWMA_ALPHA
from ..pipeline import AssurancePipeline
from ..providers import MockProvider, Provider
from ..router import Router
from ..routing_policy import CategoryPolicy, apply_policy, policy_from_drift
from ..trajectory import TrajectoryStore
from .dataset import EvalCase
from .runner import EvalRunReport, run_eval


class ClosedLoopDemoReport(BaseModel):
    demo_id: str
    phase_a: EvalRunReport  # healthy baseline
    phase_b: EvalRunReport  # degraded, default routing
    phase_c: EvalRunReport  # degraded, adapted routing
    policy_after_b: dict[str, CategoryPolicy]


def run_closed_loop_demo(
    cases: list[EvalCase],
    store: TrajectoryStore,
    remote_provider: Provider,
    failure_mode: str = "bad_enum",
    failure_rate: float = 1.0,
    seed: int = 0,
    ewma_alpha: float = DEFAULT_EWMA_ALPHA,
) -> ClosedLoopDemoReport:
    demo_id = uuid.uuid4().hex[:8]
    router = Router()

    healthy_local = MockProvider(tier="local")
    degraded_local = MockProvider(
        tier="local",
        failure_mode=failure_mode,
        failure_rate=failure_rate,
        seed=seed,
    )

    # Phase A: healthy baseline establishes low drift.
    pipeline_a = AssurancePipeline(router, healthy_local, remote_provider, store)
    phase_a = run_eval(pipeline_a, cases, ewma_alpha, run_id=f"{demo_id}-a")

    # Phase B: local tier degrades; router still on default thresholds.
    pipeline_b = AssurancePipeline(router, degraded_local, remote_provider, store)
    phase_b = run_eval(pipeline_b, cases, ewma_alpha, run_id=f"{demo_id}-b")

    # Closed loop: phase-B drift -> deterministic policy -> router tightens.
    drift_by_category = {
        category: cat.ewma_drift
        for category, cat in phase_b.metrics.by_category.items()
    }
    policy_after_b = policy_from_drift(drift_by_category)
    apply_policy(router, policy_after_b)

    # Phase C: degradation persists, but affected categories now pre-route.
    pipeline_c = AssurancePipeline(router, degraded_local, remote_provider, store)
    phase_c = run_eval(pipeline_c, cases, ewma_alpha, run_id=f"{demo_id}-c")

    return ClosedLoopDemoReport(
        demo_id=demo_id,
        phase_a=phase_a,
        phase_b=phase_b,
        phase_c=phase_c,
        policy_after_b=policy_after_b,
    )
