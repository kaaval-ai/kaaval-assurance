import pytest

from kaaval_assurance.metrics import EwmaTracker, aggregate, percentile
from kaaval_assurance.models import TrajectoryRow


def make_row(
    request_id: str,
    category: str = "severity_classification",
    tier: str = "local",
    passed: bool = True,
    failures: list[str] | None = None,
    escalated: bool = False,
    latency_ms: float = 5.0,
    cost_usd: float = 0.0,
) -> TrajectoryRow:
    return TrajectoryRow(
        request_id=request_id,
        category=category,
        contract_id="telecom.severity_classification",
        contract_version="1.0",
        tier=tier,
        provider="mock",
        model_id="m",
        verifier_passed=passed,
        verifier_failures=failures or [],
        escalated=escalated,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )


class TestEwmaTracker:
    def test_first_observation_seeds(self):
        t = EwmaTracker(alpha=0.3)
        assert t.value == 0.0
        assert t.update(1.0) == 1.0

    def test_known_sequence(self):
        t = EwmaTracker(alpha=0.3)
        for v in [0.0, 0.0, 1.0, 1.0]:
            t.update(v)
        # e3 = 0.3*1 + 0.7*0 = 0.3; e4 = 0.3*1 + 0.7*0.3 = 0.51
        assert t.value == pytest.approx(0.51)

    def test_invalid_alpha_rejected(self):
        with pytest.raises(ValueError):
            EwmaTracker(alpha=0.0)
        with pytest.raises(ValueError):
            EwmaTracker(alpha=1.5)


class TestPercentile:
    def test_interpolation(self):
        values = [float(i) for i in range(1, 11)]
        assert percentile(values, 50) == pytest.approx(5.5)
        assert percentile(values, 95) == pytest.approx(9.55)
        assert percentile(values, 0) == 1.0
        assert percentile(values, 100) == 10.0

    def test_empty_and_single(self):
        assert percentile([], 95) == 0.0
        assert percentile([7.0], 50) == 7.0


class TestAggregate:
    def rows_mixed(self) -> list[TrajectoryRow]:
        return [
            make_row("r1", passed=True),
            make_row("r2", passed=False, failures=["enum:severity"]),
            make_row(
                "r2",
                tier="remote",
                passed=True,
                escalated=True,
                latency_ms=50.0,
                cost_usd=0.001,
            ),
            make_row("r3", passed=True),
        ]

    def test_pass_and_escalation_rates(self):
        m = aggregate(self.rows_mixed())
        assert m.requests == 3
        assert m.attempts == 4
        assert m.pass_rate == pytest.approx(1.0)  # all final attempts passed
        assert m.escalation_rate == pytest.approx(1 / 3)

    def test_failure_counts_by_check_id(self):
        m = aggregate(self.rows_mixed())
        assert m.failure_counts == {"enum:severity": 1}

    def test_latency_percentiles_request_level(self):
        m = aggregate(self.rows_mixed())
        # request latencies: r1=5, r2=55, r3=5 -> sorted [5, 5, 55]
        assert m.latency_ms_p50 == pytest.approx(5.0)
        assert m.latency_ms_p95 == pytest.approx(50.0)  # 5 + 0.9*(55-5)

    def test_cost_per_verified_answer(self):
        m = aggregate(self.rows_mixed())
        assert m.total_cost_usd == pytest.approx(0.001)
        assert m.cost_per_verified_usd == pytest.approx(0.001 / 3)

    def test_cost_per_verified_none_when_nothing_verified(self):
        rows = [make_row("r1", passed=False, failures=["json_parse"], cost_usd=0.002)]
        m = aggregate(rows)
        assert m.pass_rate == 0.0
        assert m.cost_per_verified_usd is None

    def test_ewma_drift_per_category(self):
        # local attempts in order: pass(0), fail(1), pass(0) with alpha 0.5
        m = aggregate(self.rows_mixed(), alpha=0.5)
        cat = m.by_category["severity_classification"]
        assert cat.ewma_drift == pytest.approx(0.25)  # 0 -> 0.5 -> 0.25
        assert cat.local_pass_rate == pytest.approx(2 / 3)

    def test_remote_attempts_do_not_feed_drift(self):
        rows = [
            make_row("r1", passed=False, failures=["enum:severity"]),
            make_row("r1", tier="remote", passed=True, escalated=True),
        ]
        m = aggregate(rows, alpha=0.5)
        # only the failed local attempt feeds EWMA -> drift = 1.0
        assert m.by_category["severity_classification"].ewma_drift == 1.0

    def test_categories_separated(self):
        rows = [
            make_row("r1", category="severity_classification", passed=False,
                     failures=["enum:severity"]),
            make_row("r2", category="incident_summary", passed=True),
        ]
        m = aggregate(rows)
        assert set(m.by_category) == {"severity_classification", "incident_summary"}
        assert m.by_category["incident_summary"].ewma_drift == 0.0
        assert m.by_category["severity_classification"].ewma_drift == 1.0

    def test_empty_rows(self):
        m = aggregate([])
        assert m.requests == 0
        assert m.pass_rate == 0.0
        assert m.cost_per_verified_usd is None
        assert m.by_category == {}
