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
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
from kaaval_assurance.router import Router
from kaaval_assurance.trajectory import TrajectoryStore

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
    remote_failure_mode: Optional[str] = None
    export_artifacts: bool = False
    session_id: Optional[str] = None
    # Fail-closed boundary: when the final answer did not pass Layer 1, the
    # response omits it (answer=None, raw_text="") unless the caller
    # explicitly opts in. The Flight Deck opts in — it is an inspection
    # surface whose receipts show every attempt verbatim by design.
    include_unverified_raw: bool = False


class LiveSession:
    def __init__(self, session_id: str, local_provider: str, remote_provider: str):
        self.session_id = session_id
        self.local_provider = local_provider
        self.remote_provider = remote_provider
        self.created_at = time.time()
        self.last_accessed = self.created_at
        self.router = Router()
        self.store = TrajectoryStore(":memory:", check_same_thread=False)
        self.lock = threading.Lock()


class SessionManager:
    def __init__(self):
        self.sessions: dict[str, LiveSession] = {}
        self.lock = threading.Lock()

    def _cleanup(self):
        now = time.time()
        # 15 minutes TTL
        expired = [s for s in list(self.sessions.values()) if now - s.last_accessed > 900]
        for s in expired:
            with s.lock:
                s.store.close()
            if s.session_id in self.sessions:
                del self.sessions[s.session_id]
        # Max 64 sessions
        if len(self.sessions) >= 64:
            oldest = min(self.sessions.values(), key=lambda s: s.last_accessed)
            with oldest.lock:
                oldest.store.close()
            if oldest.session_id in self.sessions:
                del self.sessions[oldest.session_id]

    @contextmanager
    def checkout(self, session_id: str | None, local: str, remote: str):
        with self.lock:
            self._cleanup()
            if session_id:
                if session_id in self.sessions:
                    sess = self.sessions[session_id]
                    if sess.local_provider != local or sess.remote_provider != remote:
                        raise ValueError("Provider mismatch for existing session")
                    sess.last_accessed = time.time()
                else:
                    raise ValueError(f"Unknown session_id: {session_id}")
            else:
                new_id = uuid.uuid4().hex
                sess = LiveSession(new_id, local, remote)
                self.sessions[new_id] = sess
            sess.lock.acquire()
        try:
            yield sess
        finally:
            sess.lock.release()

    def reset(self, session_id: str) -> LiveSession:
        with self.lock:
            if session_id in self.sessions:
                old_sess = self.sessions[session_id]
                with old_sess.lock:
                    old_sess.store.close()
                new_sess = LiveSession(session_id, old_sess.local_provider, old_sess.remote_provider)
                self.sessions[session_id] = new_sess
                return new_sess
            raise KeyError("Session not found")


session_manager = SessionManager()


def live_runs_enabled() -> bool:
    return os.environ.get("KAAVAL_LIVE_RUNS_ENABLED", "") == "1"


def _static_dir_from_env() -> Path:
    configured = os.environ.get("KAAVAL_STATIC_DIR")
    if configured:
        return Path(configured)
    return ROOT / "apps" / "flight-deck" / "dist"


def create_app(
    store: Optional[ArtifactStore] = None,
    static_dir: Optional[Path] = None,
) -> FastAPI:
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

    @app.post("/api/live-sessions/{session_id}/reset")
    def reset_session(session_id: str):
        if not live_runs_enabled():
            raise HTTPException(status_code=403, detail="live runs are disabled")
        try:
            sess = session_manager.reset(session_id)
            return {"status": "ok", "session_id": sess.session_id}
        except KeyError:
            raise HTTPException(status_code=404, detail="Session not found")

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
        if req.remote_failure_mode is not None and (
            req.remote_failure_mode not in LIVE_FAILURE_MODES
            or req.remote_provider != "mock"
        ):
            raise HTTPException(
                status_code=422,
                detail="remote failure injection requires the mock remote provider "
                f"and one of {list(LIVE_FAILURE_MODES)}",
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
            with session_manager.checkout(req.session_id, req.local_provider, req.remote_provider) as sess:
                try:
                    demo = run_live_demo(
                        task_input=req.task_input,
                        contract_id=req.contract_id,
                        failure_mode=req.failure_mode,
                        remote_failure_mode=req.remote_failure_mode,
                        case_id="api",
                        local_provider=local,
                        remote_provider=remote,
                        router=sess.router,
                        store=sess.store,
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

                category = demo.category
                online_ewma_drift = sess.router.online_drift_for(category)
                current_policy_action = sess.router.current_policy_for(category).action
                current_policy_reason = sess.router.current_policy_for(category).reason
                session_id = sess.session_id
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        expose_output = (
            demo.result.verification.passed or req.include_unverified_raw
        )
        return {
            "run_id": demo.result.request_id,
            "mode": "live",
            "label": "LIVE RUN",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "session": {
                "session_id": session_id,
                "category": category,
                "online_ewma_drift": online_ewma_drift,
                "current_policy_action": current_policy_action,
                "current_policy_reason": current_policy_reason,
            },
            "request": {
                "contract_id": req.contract_id,
                "category": demo.category,
                "local_provider": req.local_provider,
                "remote_provider": req.remote_provider,
                "failure_mode": req.failure_mode,
                "remote_failure_mode": req.remote_failure_mode,
            },
            "result": {
                "verified": demo.result.verification.passed,
                "checks_run": demo.result.verification.checks_run,
                "failures": demo.result.verification.failures,
                "escalated": demo.result.escalated,
                "attempts": demo.result.attempts,
                "tier": demo.result.response.tier,
                "routing_reason": demo.result.routing.reason,
                # Fail closed: an answer that did not pass Layer 1 is a typed
                # failure, not a usable value with a warning flag attached.
                "answer": (
                    demo.result.response.parsed if expose_output else None
                ),
                "raw_text": (
                    demo.result.response.raw_text if expose_output else ""
                ),
                "unverified_output_withheld": (
                    not demo.result.verification.passed
                    and not req.include_unverified_raw
                ),
            },
            "trajectory": [json.loads(r.model_dump_json()) for r in demo.rows],
            "telemetry": json.loads(telemetry_summary.model_dump_json()),
            "runtime_profile": (
                json.loads(profile.model_dump_json()) if profile is not None else None
            ),
            "artifacts_written": artifacts_written,
        }

    resolved_static_dir = static_dir if static_dir is not None else _static_dir_from_env()
    if resolved_static_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=resolved_static_dir, html=True),
            name="flight-deck",
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.api.server:app", host="127.0.0.1", port=8000, reload=True)
