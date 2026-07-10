"""Flight Deck API: captured-evidence artifacts plus gated live assurance runs.

GET  /api/health         service liveness + live-run availability
GET  /api/dashboard      one typed payload assembled from all artifacts
GET  /api/telemetry      raw telemetry artifact with provenance
GET  /api/trajectory     raw trajectory artifact with provenance
GET  /api/runtime-probe  raw runtime-probe artifact with provenance
POST /api/runs           execute one real assurance pipeline run (gated)

Live runs reuse the existing provider factory and AssurancePipeline — this
API never reimplements routing or verification, never returns credentials,
and refuses Fireworks execution without explicit spend confirmation. Live
execution as a whole is disabled unless KAAVAL_LIVE_RUNS_ENABLED=1, so a
hosted deployment stays a pure captured-evidence surface.

Run from the repo root:
    uv run uvicorn apps.api.server:app --port 8000
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from apps.api.artifacts import ArtifactStore  # noqa: E402
from kaaval_assurance.demo import (  # noqa: E402
    LIVE_FAILURE_MODES,
    export_live_demo_artifacts,
    run_live_demo,
    telemetry_for,
)
from kaaval_assurance.providers import (  # noqa: E402
    FireworksError,
    SpendConfirmationRequired,
    VllmError,
    create_local_provider,
    create_remote_provider,
)

# Local Vite dev origins only. No credentials, so no wildcard+credentials trap.
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


class RunRequest(BaseModel):
    task_input: str = Field(min_length=1, max_length=4000)
    contract_id: str
    local_provider: Literal["mock", "ollama", "vllm"] = "mock"
    remote_provider: Literal["mock", "fireworks"] = "mock"
    confirm_spend: bool = False
    failure_mode: Optional[str] = None
    export_artifacts: bool = False


def live_runs_enabled() -> bool:
    return os.environ.get("KAAVAL_LIVE_RUNS_ENABLED", "") == "1"


def create_app(store: Optional[ArtifactStore] = None) -> FastAPI:
    store = store or ArtifactStore()
    app = FastAPI(title="Kaaval Assurance Flight Deck API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    def _artifact_response(kind: str):
        data, provenance = store.resolve(kind)
        if data is None:
            # honest unavailability, not a plausible default
            return {"available": False, "provenance": provenance, "data": None}
        return {"available": True, "provenance": provenance, "data": data}

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "service": "kaaval-flight-deck-api",
            "live_runs_enabled": live_runs_enabled(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/dashboard")
    def dashboard():
        return store.dashboard()

    @app.get("/api/telemetry")
    def telemetry():
        return _artifact_response("telemetry")

    @app.get("/api/trajectory")
    def trajectory():
        return _artifact_response("trajectory")

    @app.get("/api/runtime-probe")
    def runtime_probe():
        return _artifact_response("runtime_probe")

    @app.post("/api/runs")
    def create_run(req: RunRequest):
        if not live_runs_enabled():
            raise HTTPException(
                status_code=403,
                detail="live runs are disabled; set KAAVAL_LIVE_RUNS_ENABLED=1 "
                "on the server to enable (hosted deployments stay in "
                "captured-evidence mode)",
            )
        if req.failure_mode is not None and req.failure_mode not in LIVE_FAILURE_MODES:
            raise HTTPException(
                status_code=422,
                detail=f"failure_mode must be one of {list(LIVE_FAILURE_MODES)}",
            )
        if req.failure_mode is not None and req.local_provider != "mock":
            raise HTTPException(
                status_code=422,
                detail="failure injection is supported by the mock local provider only",
            )
        try:
            local = (
                None
                if req.local_provider == "mock"
                else create_local_provider(req.local_provider)
            )
            remote = (
                None
                if req.remote_provider == "mock"
                else create_remote_provider(
                    req.remote_provider, confirm_spend=req.confirm_spend
                )
            )
        except SpendConfirmationRequired as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

        try:
            demo = run_live_demo(
                task_input=req.task_input,
                contract_id=req.contract_id,
                failure_mode=req.failure_mode,
                case_id="api",
                local_provider=local,
                remote_provider=remote,
            )
        except KeyError as e:
            raise HTTPException(status_code=422, detail=f"unknown contract: {e}") from e
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except (FireworksError, VllmError) as e:
            # provider error strings never contain credentials
            raise HTTPException(status_code=502, detail=str(e)) from e

        telemetry_summary = telemetry_for(demo)
        local_for_profile = local or create_local_provider("mock")
        profile = local_for_profile.runtime_profile()

        artifacts_written: list[str] = []
        if req.export_artifacts:
            paths = export_live_demo_artifacts(demo, ROOT / "artifacts")
            artifacts_written = [p.name for p in paths]

        return {
            "run_id": demo.result.request_id,
            "mode": "live",
            "label": "LIVE RUN",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "request": {
                "contract_id": req.contract_id,
                "category": demo.category,
                "local_provider": req.local_provider,
                "remote_provider": req.remote_provider,
                "failure_mode": req.failure_mode,
            },
            "result": {
                "verified": demo.result.verification.passed,
                "checks_run": demo.result.verification.checks_run,
                "failures": demo.result.verification.failures,
                "escalated": demo.result.escalated,
                "attempts": demo.result.attempts,
                "tier": demo.result.response.tier,
                "routing_reason": demo.result.routing.reason,
                "answer": demo.result.response.parsed,
                "raw_text": demo.result.response.raw_text,
            },
            "trajectory": [json.loads(r.model_dump_json()) for r in demo.rows],
            "telemetry": json.loads(telemetry_summary.model_dump_json()),
            "runtime_profile": (
                json.loads(profile.model_dump_json()) if profile is not None else None
            ),
            "artifacts_written": artifacts_written,
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.api.server:app", host="127.0.0.1", port=8000, reload=True)
