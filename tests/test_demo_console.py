"""Demo console + sample artifact tests. Streamlit itself is not required:
the app is compile-checked, and the shipped sample data is validated for
structure and honesty (no measured-runtime claims before an AMD run)."""

import json
import py_compile

SAMPLE_DIR = "demo_artifacts/sample"


def load(name):
    with open(f"{SAMPLE_DIR}/{name}", encoding="utf-8") as f:
        return json.load(f)


def test_app_compiles():
    py_compile.compile("apps/demo_console/app.py", doraise=True)


def test_sample_telemetry_structure():
    telemetry = load("telemetry-truth.json")
    assert telemetry["claims"], "claims table must not be empty"
    for claim in telemetry["claims"]:
        assert claim["source"] in {"measured", "configured", "not_available", "planned"}
    assert telemetry["verification"]["final_verified_rate"] == 1.0
    assert telemetry["audit"]["enabled"] is True
    assert telemetry["audit"]["calibration_status"] == "passed"


def test_sample_runtime_never_claims_measured():
    telemetry = load("telemetry-truth.json")
    # Sample data is mock-mode: runtime must stay planned/configured until a
    # real AMD pod probe or run produces measured artifacts.
    assert telemetry["runtime"]["status"] in ("planned", "configured")
    runtime_claim = next(
        c for c in telemetry["claims"] if c["claim"] == "Runtime"
    )
    assert runtime_claim["source"] != "measured"


def test_sample_trajectory_shows_verification_detail():
    rows = load("trajectory-sample.json")
    assert len(rows) == 2  # failed local attempt + escalated remote attempt
    local, remote = rows
    assert local["tier"] == "local" and local["verifier_passed"] is False
    assert local["verifier_failures"]  # contract check ids present
    assert remote["tier"] == "remote" and remote["verifier_passed"] is True
    assert remote["escalated"] is True
    assert local["task_input"] and local["raw_text"]  # replayable


def test_sample_contains_no_secret_material():
    for name in ("telemetry-truth.json", "trajectory-sample.json"):
        content = open(f"{SAMPLE_DIR}/{name}", encoding="utf-8").read()
        for marker in ("api_key", "API_KEY", "Bearer ", "sk-", "fw-"):
            assert marker not in content, f"{marker!r} found in {name}"
