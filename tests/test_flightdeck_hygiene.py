"""Static claims-integrity guard for the Flight Deck frontend.

Fails if fabricated-claim vocabulary or generic mock providers reappear in
apps/flight-deck/src, and if judge-facing metrics regain simulated variation.
"""

from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "apps" / "flight-deck" / "src"

BANNED_STRINGS = [
    "SEV-SNP",
    "cryptographic attestation",
    "launch digest",
    "launchDigest",
    "hardware tamper",
    "GPT-4o",
    "fabricated-premium-provider",
    "AWS Nitro",
    "PII Redaction",
    "hallucinationRate",
    "Sigstore",
    "Presidio",
    "Pending until a real AMD probe artifact exists",
]


def _source_files():
    files = [
        p
        for p in SRC.rglob("*")
        if p.suffix in (".ts", ".tsx", ".css", ".html") and p.is_file()
    ]
    assert files, "flight deck source not found"
    return files


def test_no_fabricated_claim_strings():
    offenders = []
    for path in _source_files():
        content = path.read_text(encoding="utf-8")
        for banned in BANNED_STRINGS:
            if banned in content:
                offenders.append(f"{path.name}: {banned}")
    assert not offenders, f"fabricated-claim strings found: {offenders}"


def test_no_simulated_variation_in_metrics():
    offenders = [
        p.name for p in _source_files() if "Math.random(" in p.read_text("utf-8")
    ]
    assert not offenders, f"Math.random in judge-facing UI: {offenders}"


def test_connected_live_run_does_not_send_mock_compatibility_fields():
    panel = (SRC / "components" / "LiveRunPanel.tsx").read_text(encoding="utf-8")

    assert "local_provider: 'mock'" not in panel
    assert "remote_provider: 'mock'" not in panel
    assert "failure_mode:" not in panel
    assert "remote_failure_mode:" not in panel
    assert "primary_connection_id: primary.connection_id" in panel


def test_runtime_modal_does_not_guess_local_model_ids():
    modal = (SRC / "components" / "RuntimeConnectionModal.tsx").read_text(
        encoding="utf-8"
    )

    assert "ollama: ''," in modal
    assert "vllm: ''," in modal
    assert "gemma3:4b" not in modal
    assert "gemma-3-1b-it" not in modal


def test_live_result_is_readable_without_horizontal_scrolling():
    panel = (SRC / "components" / "LiveRunPanel.tsx").read_text(encoding="utf-8")

    assert "function AcceptedAnswer" in panel
    assert "useState<'pretty' | 'json'>('pretty')" in panel
    assert 'aria-label="Answer format"' in panel
    assert "whitespace-pre-wrap break-words" in panel
    assert "whitespace-pre-wrap break-all" in panel
    assert '<AcceptedAnswer answer={run.result.answer} />' in panel


def test_captured_hierarchy_has_one_rail_and_one_visible_receipt():
    dashboard = (SRC / "components" / "SummaryDashboard.tsx").read_text(
        encoding="utf-8"
    )

    assert dashboard.count("<DemoScriptRail") == 1
    assert dashboard.count("<CostAvoidanceReceipt") == 1
    rail = dashboard.index("<DemoScriptRail")
    receipt = dashboard.index("<CostAvoidanceReceipt")
    deep_dive = dashboard.index("ENGINEERING DEEP DIVE")
    assert rail < receipt < deep_dive


def test_live_failures_and_receipt_are_visible_before_internal_details():
    panel = (SRC / "components" / "LiveRunPanel.tsx").read_text(encoding="utf-8")
    receipt = (SRC / "components" / "LiveAssuranceReceipt.tsx").read_text(
        encoding="utf-8"
    )

    pipeline = panel.index("<PipelinePanel")
    telemetry = panel.index("<TelemetryTruth")
    kaaval_receipt = panel.index("<LiveAssuranceReceipt")
    internals = panel.index("ADDITIONAL LIVE INTERNALS")
    assert pipeline < kaaval_receipt < internals
    assert telemetry < kaaval_receipt < internals
    assert "NO SAFE ANSWER" in panel
    assert "Caught before acceptance" in receipt
    assert "transport:${row.error_type" in receipt
    assert "row.verifier_failures" in receipt


def test_dormant_crt_overlay_is_removed():
    css = (SRC / "index.css").read_text(encoding="utf-8")
    assert ".bg-crt" not in css
    assert "Scan-line CRT effect" not in css


def test_layer3_is_described_as_display_only_everywhere():
    root = SRC.parents[2]
    architecture = (root / "docs" / "kaaval-assurance-architecture.html").read_text(
        encoding="utf-8"
    )
    runner = (
        root / "src" / "kaaval_assurance" / "audit" / "runner.py"
    ).read_text(encoding="utf-8")

    assert "informs routing only through" not in architecture
    assert "feed Layer-2 EWMA" not in runner
    assert "No challenger verdict gates a response or feeds routing" in architecture
