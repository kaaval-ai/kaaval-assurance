"""Flight Deck API: captured-evidence artifacts plus gated live assurance runs.

GET  /api/health         service liveness + live-run availability
GET  /api/dashboard      one typed payload assembled from all artifacts
GET  /api/telemetry      raw telemetry artifact with provenance
GET  /api/trajectory     raw trajectory artifact with provenance
GET  /api/runtime-probe  raw runtime-probe artifact with provenance
GET  /api/capabilities   deployment/runtime onboarding capabilities
GET  /api/ops/snapshot   redacted live-session operations snapshot
POST /api/runtime-connections  test and hold one ephemeral runtime credential
POST /api/runs           execute one real assurance pipeline run (gated)

Live runs reuse the existing provider factory and AssurancePipeline — this
API never reimplements routing or verification, never returns credentials,
and refuses Fireworks execution without explicit spend confirmation. Live
execution as a whole is disabled unless KAAVAL_LIVE_RUNS_ENABLED=1. Runtime
credentials supplied interactively stay in process memory and expire.

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
from pydantic import BaseModel, Field, SecretStr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from apps.api.artifacts import ArtifactStore  # noqa: E402
from apps.api.runtime_connections import (  # noqa: E402
    DEFAULT_LOCAL_URLS,
    RuntimeConnectionError,
    RuntimeProvider,
    RuntimeRole,
    UnconfiguredProvider,
    byok_allowed,
    custom_endpoints_allowed,
    deployment_mode,
    runtime_connection_manager,
)
from kaaval_assurance.agent import (  # noqa: E402
    NOC_INCIDENT_WORKFLOW,
    rows_for_agent_run,
    run_agent_workflow,
)
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
from kaaval_assurance.pipeline import AssurancePipeline  # noqa: E402
from kaaval_assurance import __version__ as assurance_version  # noqa: E402
from kaaval_assurance.ops import (  # noqa: E402
    OpsRoutingState,
    OpsSessionInput,
    OpsSnapshot,
    build_ops_snapshot,
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

# K Top's quick MVP is a polling client. Bound each active session's copied
# history so one read-only poll cannot scan an ever-growing in-memory store.
OPS_DECISIONS_PER_SESSION_LIMIT = 100


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
    primary_connection_id: Optional[str] = None
    escalation_connection_id: Optional[str] = None


class RuntimeConnectionRequest(BaseModel):
    provider: RuntimeProvider
    role: RuntimeRole = "primary"
    model_id: str = Field(min_length=1, max_length=300)
    api_key: SecretStr = SecretStr("")
    base_url: Optional[str] = Field(default=None, max_length=500)
    model_family: str = Field(default="", max_length=80)
    structured_outputs: Optional[bool] = None
    hardware_target: str = Field(default="", max_length=120)
    timeout_seconds: float = Field(default=30.0, ge=1, le=120)
    max_tokens: int = Field(default=1024, ge=32, le=4096)


class AgentRunRequest(BaseModel):
    task_input: str = Field(min_length=1, max_length=4000)
    local_provider: Literal["mock", "ollama", "vllm"] = "mock"
    remote_provider: Literal["mock", "fireworks"] = "mock"
    confirm_spend: bool = False
    session_id: Optional[str] = None


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

    def _cleanup(self, reserve_new_session: bool = False):
        now = time.time()
        # 15 minutes TTL
        expired = [s for s in list(self.sessions.values()) if now - s.last_accessed > 900]
        for s in expired:
            with s.lock:
                s.store.close()
            if s.session_id in self.sessions:
                del self.sessions[s.session_id]
        # Reserve capacity only when a caller is about to create a new session.
        # Read-only snapshots and checkouts of existing sessions must not evict.
        if reserve_new_session and len(self.sessions) >= 64:
            oldest = min(self.sessions.values(), key=lambda s: s.last_accessed)
            with oldest.lock:
                oldest.store.close()
            if oldest.session_id in self.sessions:
                del self.sessions[oldest.session_id]

    @contextmanager
    def checkout(self, session_id: str | None, local: str, remote: str):
        with self.lock:
            self._cleanup(reserve_new_session=session_id is None)
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

    def ops_inputs(self) -> list[OpsSessionInput]:
        """Copy content-bearing session rows into a short-lived server view.

        Only ``build_ops_snapshot`` sees these rows. The public record produced
        from them omits task input, model output, exception bodies, credentials,
        connection identifiers, and local paths.
        """

        snapshots: list[OpsSessionInput] = []
        with self.lock:
            self._cleanup()
            for sess in self.sessions.values():
                with sess.lock:
                    rows, window_truncated = sess.store.recent_request_window(
                        OPS_DECISIONS_PER_SESSION_LIMIT
                    )
                    routing = []
                    for category in sorted({row.category for row in rows}):
                        policy = sess.router.current_policy_for(category)
                        routing.append(
                            OpsRoutingState(
                                session_id=sess.session_id,
                                category=category,
                                verifier_failure_ewma=(
                                    sess.router.online_drift_for(category)
                                ),
                                action=policy.action,
                                reason=policy.reason,
                            )
                        )
                    snapshots.append(
                        OpsSessionInput(
                            session_id=sess.session_id,
                            rows=tuple(rows),
                            routing=tuple(routing),
                            window_truncated=window_truncated,
                        )
                    )
        return snapshots


session_manager = SessionManager()


def live_runs_enabled() -> bool:
    return os.environ.get("KAAVAL_LIVE_RUNS_ENABLED", "") == "1"


def paid_remote_allowed() -> bool:
    """Server-side gate for spending the server's Fireworks credential.

    The client's confirm_spend flag is a UX acknowledgment, never
    authorization: any unauthenticated caller can send confirm_spend=true.
    Paid remote execution additionally requires the operator to have set
    KAAVAL_ALLOW_PAID_REMOTE=1 on the server. Default closed.
    """
    return os.environ.get("KAAVAL_ALLOW_PAID_REMOTE", "") == "1"


def artifact_export_allowed() -> bool:
    """Server-side gate for writing live-run artifacts to disk.

    Any writable artifact can poison what the evidence dashboard loads, so
    exports are disabled unless the operator sets
    KAAVAL_ALLOW_ARTIFACT_EXPORT=1. The submission evidence bundle is
    curated offline, never through this API. Default closed.
    """
    return os.environ.get("KAAVAL_ALLOW_ARTIFACT_EXPORT", "") == "1"


def diagnostic_raw_allowed() -> bool:
    """Operator gate for exposing rejected model output over HTTP."""
    return os.environ.get("KAAVAL_ALLOW_DIAGNOSTIC_RAW", "") == "1"


def _trajectory_for_response(rows, include_raw: bool) -> list[dict]:
    """Serialize receipts while redacting rejected output by default."""
    payload: list[dict] = []
    for row in rows:
        item = json.loads(row.model_dump_json())
        withheld = not row.verifier_passed and not include_raw
        if withheld:
            item["raw_text"] = ""
        item["raw_text_withheld"] = withheld
        payload.append(item)
    return payload


def _static_dir_from_env() -> Path:
    configured = os.environ.get("KAAVAL_STATIC_DIR")
    if configured:
        return Path(configured)
    return ROOT / "apps" / "flight-deck" / "dist"


def create_app(
    store: Optional[ArtifactStore] = None,
    static_dir: Optional[Path] = None,
    export_root: Optional[Path] = None,
) -> FastAPI:
    store = store or ArtifactStore()
    # Live API exports are deliberately outside the curated bundle root. Each
    # run gets its own directory, so even an operator-authorized export can
    # never overwrite the top-level evidence consumed by ArtifactStore.
    live_export_root = export_root or (ROOT / "artifacts" / "live-exports")
    app = FastAPI(title="Kaaval Assurance Flight Deck API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
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
            "paid_remote_allowed": paid_remote_allowed(),
            "artifact_export_allowed": artifact_export_allowed(),
            "diagnostic_raw_allowed": diagnostic_raw_allowed(),
            "deployment_mode": deployment_mode(),
            "byok_allowed": byok_allowed(),
            "custom_endpoints_allowed": custom_endpoints_allowed(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/capabilities")
    def capabilities():
        providers = ["fireworks"]
        if deployment_mode() == "local":
            providers.extend(["ollama", "vllm"])
        if custom_endpoints_allowed():
            providers.append("openai_compatible")
        return {
            "deployment_mode": deployment_mode(),
            "live_runs_enabled": live_runs_enabled(),
            "byok_allowed": byok_allowed(),
            "custom_endpoints_allowed": custom_endpoints_allowed(),
            "providers": providers,
            "default_endpoints": DEFAULT_LOCAL_URLS,
            "connection_ttl_seconds": runtime_connection_manager.ttl_seconds,
        }

    @app.post("/api/runtime-connections")
    def create_runtime_connection(req: RuntimeConnectionRequest):
        if not live_runs_enabled():
            raise HTTPException(status_code=403, detail="live runs are disabled")
        try:
            connection = runtime_connection_manager.create(
                provider=req.provider,
                role=req.role,
                model_id=req.model_id,
                api_key=req.api_key.get_secret_value(),
                base_url=req.base_url,
                model_family=req.model_family,
                structured_outputs=req.structured_outputs,
                hardware_target=req.hardware_target,
                timeout_seconds=req.timeout_seconds,
                max_tokens=req.max_tokens,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeConnectionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return connection.public_metadata(runtime_connection_manager.ttl_seconds)

    @app.delete("/api/runtime-connections/{connection_id}")
    def delete_runtime_connection(connection_id: str):
        removed = runtime_connection_manager.delete(connection_id)
        return {"status": "disconnected" if removed else "already_expired"}

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

    @app.get("/api/ops/snapshot", response_model=OpsSnapshot)
    def ops_snapshot():
        """Return a bounded, content-free view of real live-session state."""

        if deployment_mode() != "local":
            raise HTTPException(
                status_code=403,
                detail=(
                    "the K Top preview is local-only; hosted operations access "
                    "requires the future authenticated, tenant-scoped API"
                ),
            )
        return build_ops_snapshot(
            session_manager.ops_inputs(),
            runtime_version=assurance_version,
            deployment_mode=deployment_mode(),
            live_runs_enabled=live_runs_enabled(),
        )

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
        uses_runtime_connection = req.primary_connection_id is not None
        if req.escalation_connection_id and not uses_runtime_connection:
            raise HTTPException(
                status_code=422,
                detail="escalation_connection_id requires primary_connection_id",
            )
        if uses_runtime_connection and (
            req.failure_mode is not None or req.remote_failure_mode is not None
        ):
            raise HTTPException(
                status_code=422,
                detail="failure injection is unavailable for connected runtimes",
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
        if (
            not uses_runtime_connection
            and req.remote_provider == "fireworks"
            and not paid_remote_allowed()
        ):
            raise HTTPException(
                status_code=403,
                detail="paid remote execution is disabled on this server; the "
                "operator must set KAAVAL_ALLOW_PAID_REMOTE=1 (client "
                "confirm_spend is an acknowledgment, not authorization)",
            )
        if req.export_artifacts and not artifact_export_allowed():
            raise HTTPException(
                status_code=403,
                detail="artifact export is disabled on this server; the operator "
                "must set KAAVAL_ALLOW_ARTIFACT_EXPORT=1. The captured-evidence "
                "bundle is curated offline, never through this API",
            )
        if req.include_unverified_raw and not diagnostic_raw_allowed():
            raise HTTPException(
                status_code=403,
                detail="diagnostic raw output is disabled on this server; the "
                "operator must set KAAVAL_ALLOW_DIAGNOSTIC_RAW=1",
            )
        try:
            if uses_runtime_connection:
                primary_connection = runtime_connection_manager.get(
                    req.primary_connection_id or "", role="primary"
                )
                escalation_connection = (
                    runtime_connection_manager.get(
                        req.escalation_connection_id, role="escalation"
                    )
                    if req.escalation_connection_id
                    else None
                )
                uses_fireworks = primary_connection.spends_credits or bool(
                    escalation_connection and escalation_connection.spends_credits
                )
                if uses_fireworks and not req.confirm_spend:
                    raise SpendConfirmationRequired(
                        "this live session uses Fireworks credits; confirm spend for the run"
                    )
                local = primary_connection.build_provider()
                remote = (
                    escalation_connection.build_provider()
                    if escalation_connection
                    else UnconfiguredProvider("remote")
                )
                local_identity = f"runtime:{primary_connection.connection_id}"
                remote_identity = (
                    f"runtime:{escalation_connection.connection_id}"
                    if escalation_connection
                    else "runtime:not-configured"
                )
                request_local_provider = primary_connection.provider
                request_remote_provider = (
                    escalation_connection.provider
                    if escalation_connection
                    else "not-configured"
                )
            else:
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
                local_identity = req.local_provider
                remote_identity = req.remote_provider
                request_local_provider = req.local_provider
                request_remote_provider = req.remote_provider
        except SpendConfirmationRequired as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

        try:
            with session_manager.checkout(
                req.session_id, local_identity, remote_identity
            ) as sess:
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

                local_for_profile = local or create_local_provider("mock")
                profile = local_for_profile.runtime_profile()
                telemetry_summary = telemetry_for(demo, runtime_profile=profile)

                artifacts_written: list[str] = []
                if req.export_artifacts:
                    run_export_dir = live_export_root / demo.result.request_id
                    paths = export_live_demo_artifacts(demo, run_export_dir)
                    artifacts_written = [
                        f"{demo.result.request_id}/{path.name}" for path in paths
                    ]

                category = demo.category
                online_ewma_drift = sess.router.online_drift_for(category)
                current_policy_action = sess.router.current_policy_for(category).action
                current_policy_reason = sess.router.current_policy_for(category).reason
                session_id = sess.session_id
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        accepted = demo.result.accepted_response
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
                "local_provider": request_local_provider,
                "remote_provider": request_remote_provider,
                "primary_connection_id": req.primary_connection_id,
                "escalation_connection_id": req.escalation_connection_id,
                "failure_mode": req.failure_mode,
                "remote_failure_mode": req.remote_failure_mode,
            },
            "result": {
                "status": demo.result.status,
                "contract_conformant": demo.result.verification.passed,
                # Backward-compatible alias; contract_conformant is the
                # authoritative public meaning of this legacy field.
                "verified": demo.result.verification.passed,
                "checks_run": demo.result.verification.checks_run,
                "failures": demo.result.verification.failures,
                "escalated": demo.result.escalated,
                "attempts": demo.result.attempts,
                "tier": demo.result.response.tier,
                "routing_reason": demo.result.routing.reason,
                "answer": accepted.parsed if accepted is not None else None,
                "raw_text": accepted.raw_text if accepted is not None else "",
                "diagnostic_raw_text": (
                    demo.result.response.raw_text
                    if req.include_unverified_raw and accepted is None
                    else None
                ),
                "unverified_output_withheld": (
                    accepted is None and not req.include_unverified_raw
                ),
            },
            "trajectory": _trajectory_for_response(
                demo.rows, include_raw=req.include_unverified_raw
            ),
            "telemetry": json.loads(telemetry_summary.model_dump_json()),
            "runtime_profile": (
                json.loads(profile.model_dump_json()) if profile is not None else None
            ),
            "artifacts_written": artifacts_written,
        }

    @app.post("/api/agent-runs")
    def create_agent_run(req: AgentRunRequest):
        if not live_runs_enabled():
            raise HTTPException(status_code=403, detail="live runs are disabled")
        if req.remote_provider == "fireworks" and not paid_remote_allowed():
            raise HTTPException(
                status_code=403,
                detail="paid remote execution is disabled on this server",
            )
        try:
            local = create_local_provider(req.local_provider)
            remote = create_remote_provider(
                req.remote_provider, confirm_spend=req.confirm_spend
            )
        except SpendConfirmationRequired as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        try:
            with session_manager.checkout(
                req.session_id, req.local_provider, req.remote_provider
            ) as sess:
                pipeline = AssurancePipeline(sess.router, local, remote, sess.store)
                result = run_agent_workflow(
                    pipeline, req.task_input, NOC_INCIDENT_WORKFLOW
                )
                rows = rows_for_agent_run(sess.store, result)
                session_id = sess.session_id
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return {
            "run_id": result.run_id,
            "mode": "live",
            "workflow": "noc_incident",
            "status": "completed" if result.completed else "blocked",
            "blocked_at": result.blocked_at,
            "session_id": session_id,
            "steps": [
                {
                    "request_id": step.request_id,
                    "status": step.status,
                    "contract_conformant": step.verification.passed,
                    "failures": step.verification.failures,
                    "attempts": step.attempts,
                    "escalated": step.escalated,
                    "routing_reason": step.routing.reason,
                    "accepted_answer": (
                        step.accepted_response.parsed
                        if step.accepted_response is not None
                        else None
                    ),
                }
                for step in result.steps
            ],
            "trajectory": _trajectory_for_response(rows, include_raw=False),
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
