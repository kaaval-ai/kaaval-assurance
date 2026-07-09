"""Runtime probe: measure what the local vLLM endpoint actually serves.

    python -m kaaval_assurance.runtime_probe [--json] [--output PATH]

Probing is how runtime facts become "measured" in the telemetry truth layer:
before a successful probe, model and hardware statements stay planned or
configured. The local tier is Gemma-first; if a non-Gemma model is served as
an operational fallback, the probe records that truthfully — model id and
family are telemetry fields, not marketing claims.

Never prints secrets: environment output is redacted.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional

import requests
from pydantic import BaseModel, Field

DEFAULT_BASE_URL = "http://localhost:8000/v1"

_SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")
_ENV_PREFIXES = ("VLLM_", "FIREWORKS_", "KAAVAL_")


class RuntimeProbeResult(BaseModel):
    probed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    base_url: str
    reachable: bool
    latency_ms: Optional[float] = None
    served_models: list[str] = Field(default_factory=list)
    configured_model: Optional[str] = None
    configured_model_served: Optional[bool] = None
    model_family: str = "gemma"
    # None when no model configured; False flags a family/model mismatch that
    # must be corrected in env (e.g. a Qwen fallback still labeled gemma).
    family_consistent: Optional[bool] = None
    hardware_target: str = "amd-hackathon-gpu"
    vllm_version: Optional[str] = None
    error: Optional[str] = None
    source: str = "measured"  # a probe result is a measurement by definition


def redact_env(env: Optional[Mapping[str, str]] = None) -> dict[str, str]:
    """Project-relevant env vars with secret values redacted."""
    env = os.environ if env is None else env
    out: dict[str, str] = {}
    for key in sorted(env):
        if not key.startswith(_ENV_PREFIXES):
            continue
        value = env[key]
        if value and any(marker in key.upper() for marker in _SECRET_MARKERS):
            out[key] = "***redacted***"
        else:
            out[key] = value
    return out


def _version_url(base_url: str) -> str:
    # vLLM serves GET /version at the server root, outside the /v1 prefix.
    if base_url.endswith("/v1"):
        return base_url[: -len("/v1")] + "/version"
    return base_url + "/version"


def probe_runtime(
    env: Optional[Mapping[str, str]] = None,
    session: Optional[requests.Session] = None,
    timeout: float = 10.0,
) -> RuntimeProbeResult:
    env = os.environ if env is None else env
    session = session or requests.Session()

    base_url = env.get("VLLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    configured_model = env.get("VLLM_MODEL", "").strip() or None
    model_family = env.get("VLLM_MODEL_FAMILY", "gemma")
    hardware_target = env.get("VLLM_HARDWARE_TARGET", "amd-hackathon-gpu")
    family_consistent = (
        model_family.lower() in configured_model.lower()
        if configured_model
        else None
    )
    common = dict(
        base_url=base_url,
        configured_model=configured_model,
        model_family=model_family,
        family_consistent=family_consistent,
        hardware_target=hardware_target,
    )

    headers = {}
    api_key = env.get("VLLM_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    started = time.perf_counter()
    try:
        resp = session.get(f"{base_url}/models", headers=headers, timeout=timeout)
    except requests.RequestException as e:
        return RuntimeProbeResult(
            reachable=False, error=f"{type(e).__name__}: {e}", **common
        )
    latency_ms = (time.perf_counter() - started) * 1000.0

    if resp.status_code != 200:
        return RuntimeProbeResult(
            reachable=False,
            latency_ms=latency_ms,
            error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            **common,
        )
    try:
        data = resp.json()
        served = [
            m.get("id", "")
            for m in data.get("data", [])
            if isinstance(m, dict) and m.get("id")
        ]
    except ValueError as e:
        return RuntimeProbeResult(
            reachable=False,
            latency_ms=latency_ms,
            error=f"unexpected /models response: {e}",
            **common,
        )

    vllm_version = None
    try:
        vresp = session.get(_version_url(base_url), timeout=timeout)
        if vresp.status_code == 200:
            vllm_version = (vresp.json() or {}).get("version")
    except (requests.RequestException, ValueError):
        pass  # version endpoint is optional; absence is not an error

    return RuntimeProbeResult(
        reachable=True,
        latency_ms=latency_ms,
        served_models=served,
        configured_model_served=(
            configured_model in served if configured_model else None
        ),
        vllm_version=vllm_version,
        **common,
    )


def _print_text(result: RuntimeProbeResult, env: Mapping[str, str]) -> None:
    print(f"runtime probe — {result.base_url}")
    if result.reachable:
        version = f" | vLLM version {result.vllm_version}" if result.vllm_version else ""
        print(f"reachable: yes (latency {result.latency_ms:.1f}ms){version}")
        print(f"served models: {', '.join(result.served_models) or 'none reported'}")
    else:
        print(f"reachable: no — {result.error}")
    if result.configured_model:
        served = (
            "yes"
            if result.configured_model_served
            else "no" if result.configured_model_served is not None else "unknown"
        )
        print(f"configured VLLM_MODEL: {result.configured_model} (served: {served})")
    else:
        print("configured VLLM_MODEL: not set — pick from served models above")
    print(
        f"model family: {result.model_family} | hardware target: "
        f"{result.hardware_target}"
    )
    if result.family_consistent is False:
        print(
            "note: configured model does not match VLLM_MODEL_FAMILY. If this "
            "is an operational fallback (Gemma did not fit or serve reliably), "
            "set VLLM_MODEL_FAMILY accordingly so telemetry records it "
            "truthfully."
        )
    print(
        "policy: Gemma-first local tier via vLLM on the AMD hackathon GPU; "
        "fallback local model recorded truthfully if Gemma does not fit."
    )
    print("env (redacted):")
    for key, value in redact_env(env).items():
        print(f"  {key}={value}")


def main(
    argv: Optional[list[str]] = None,
    env: Optional[Mapping[str, str]] = None,
    session: Optional[requests.Session] = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="kaaval-runtime-probe",
        description="Probe the configured vLLM endpoint and report measured "
        "runtime facts with secrets redacted.",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument(
        "--output", type=Path, default=None, help="also write the JSON result here"
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="probe timeout seconds"
    )
    args = parser.parse_args(argv)
    env = os.environ if env is None else env

    result = probe_runtime(env=env, session=session, timeout=args.timeout)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2) + "\n", "utf-8")
    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        _print_text(result, env)
        if args.output is not None:
            print(f"probe JSON written to {args.output}")
    return 0 if result.reachable else 1


if __name__ == "__main__":
    raise SystemExit(main())
