"""Runtime probe: record what this host and the vLLM endpoint actually provide.

    python -m kaaval_assurance.runtime_probe            # JSON by default
    python -m kaaval_assurance.runtime_probe --text     # human summary
    python -m kaaval_assurance.runtime_probe --output artifacts/runtime-probe.json

Probing is how runtime facts become "measured" in the telemetry truth layer:
before a successful probe, model and hardware statements stay planned or
configured. The local tier is Gemma-first; if a non-Gemma model is served as
an operational fallback, the probe records that truthfully — model id and
family are telemetry fields, not marketing claims.

Design rules:
- Never fails because a host tool is missing: absent rocm-smi, vllm CLI, or
  Python packages are reported as not_available, not raised.
- Never prints secrets: environment output is redacted.
- Every section carries a source tag: measured | configured | not_available.
"""

import argparse
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Optional

import requests
from pydantic import BaseModel, Field

DEFAULT_BASE_URL = "http://localhost:8000/v1"

# Segment match, not substring: VLLM_API_KEY is a secret, but token-count
# knobs like FIREWORKS_AUDIT_MAX_TOKENS are configuration, not credentials.
_SECRET_SEGMENTS = {"KEY", "APIKEY", "SECRET", "PASSWORD"}
_ENV_PREFIXES = ("VLLM_", "FIREWORKS_", "KAAVAL_")


def _is_secret_key(key: str) -> bool:
    return bool(_SECRET_SEGMENTS & set(key.upper().split("_")))

PACKAGES_TO_CHECK = ("vllm", "torch", "requests", "pydantic")

HOST_COMMANDS: dict[str, list[str]] = {
    "rocm_smi_product": ["rocm-smi", "--showproductname"],
    "rocm_smi_vram": ["rocm-smi", "--showmeminfo", "vram"],
    "vllm_version": ["vllm", "--version"],
}

CommandRunner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


class SystemFacts(BaseModel):
    cwd: str
    under_workspace: bool  # AMD pod persistence lives under /workspace
    python_version: str
    source: str = "measured"


class PackageCheck(BaseModel):
    name: str
    importable: bool
    version: Optional[str] = None
    source: str = "measured"


class CommandProbe(BaseModel):
    command: list[str]
    available: bool
    output: Optional[str] = None
    error: Optional[str] = None
    source: str  # "measured" when it ran, "not_available" otherwise


class RuntimeProbeResult(BaseModel):
    """HTTP probe of the configured vLLM endpoint."""

    probed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    source: str = "measured"


class RuntimeProbeReport(BaseModel):
    probed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    system: SystemFacts
    packages: list[PackageCheck]
    commands: dict[str, CommandProbe]
    env_vllm: dict[str, str] = Field(default_factory=dict)  # redacted
    env_fireworks: dict[str, str] = Field(default_factory=dict)  # redacted
    env_source: str = "configured"
    endpoint: Optional[RuntimeProbeResult] = None
    policy: str = (
        "Gemma-first local tier via vLLM on the AMD hackathon GPU; fallback "
        "local model recorded truthfully if Gemma does not fit."
    )


def redact_env(env: Optional[Mapping[str, str]] = None) -> dict[str, str]:
    """Project-relevant env vars with secret values redacted."""
    env = os.environ if env is None else env
    out: dict[str, str] = {}
    for key in sorted(env):
        if not key.startswith(_ENV_PREFIXES):
            continue
        value = env[key]
        if value and _is_secret_key(key):
            out[key] = "***redacted***"
        else:
            out[key] = value
    return out


def check_packages(names: tuple[str, ...] = PACKAGES_TO_CHECK) -> list[PackageCheck]:
    checks: list[PackageCheck] = []
    for name in names:
        try:
            importable = importlib.util.find_spec(name) is not None
        except Exception:  # a broken package must not break the probe
            importable = False
        version = None
        if importable:
            try:
                version = importlib.metadata.version(name)
            except Exception:
                version = None
        checks.append(PackageCheck(name=name, importable=importable, version=version))
    return checks


def _default_runner(cmd: list[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(cmd, capture_output=True, text=True, timeout=15)


def probe_command(cmd: list[str], runner: CommandRunner = _default_runner) -> CommandProbe:
    """Run a host command; absence or failure is data, never an exception."""
    try:
        proc = runner(cmd)
    except FileNotFoundError:
        return CommandProbe(
            command=cmd, available=False, error="command not found",
            source="not_available",
        )
    except Exception as e:
        return CommandProbe(
            command=cmd, available=False, error=f"{type(e).__name__}: {e}",
            source="not_available",
        )
    output = ((proc.stdout or "").strip() or (proc.stderr or "").strip())[:500]
    if proc.returncode != 0:
        return CommandProbe(
            command=cmd, available=False, output=output,
            error=f"exit {proc.returncode}", source="not_available",
        )
    return CommandProbe(command=cmd, available=True, output=output, source="measured")


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
    """HTTP probe of the configured vLLM endpoint (served models, version)."""
    env = os.environ if env is None else env
    session = session or requests.Session()

    base_url = env.get("VLLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    configured_model = env.get("VLLM_MODEL", "").strip() or None
    model_family = env.get("VLLM_MODEL_FAMILY", "gemma")
    hardware_target = env.get("VLLM_HARDWARE_TARGET", "amd-hackathon-gpu")
    family_consistent = (
        model_family.lower() in configured_model.lower() if configured_model else None
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


def build_probe_report(
    env: Optional[Mapping[str, str]] = None,
    session: Optional[requests.Session] = None,
    runner: CommandRunner = _default_runner,
    include_endpoint: bool = True,
    timeout: float = 10.0,
    cwd: Optional[str] = None,
) -> RuntimeProbeReport:
    env = os.environ if env is None else env
    cwd = cwd if cwd is not None else os.getcwd()
    redacted = redact_env(env)
    return RuntimeProbeReport(
        system=SystemFacts(
            cwd=cwd,
            under_workspace=cwd == "/workspace" or cwd.startswith("/workspace/"),
            python_version=platform.python_version(),
        ),
        packages=check_packages(),
        commands={
            name: probe_command(cmd, runner=runner)
            for name, cmd in HOST_COMMANDS.items()
        },
        env_vllm={k: v for k, v in redacted.items() if k.startswith("VLLM_")},
        env_fireworks={
            k: v for k, v in redacted.items() if k.startswith("FIREWORKS_")
        },
        endpoint=(
            probe_runtime(env=env, session=session, timeout=timeout)
            if include_endpoint
            else None
        ),
    )


def _print_text(report: RuntimeProbeReport) -> None:
    s = report.system
    workspace = "yes" if s.under_workspace else "no (AMD pod persistence is /workspace)"
    print(f"runtime probe — cwd {s.cwd} | under /workspace: {workspace}")
    print(f"python {s.python_version} [{s.source}]")
    pkgs = ", ".join(
        f"{p.name}={'missing' if not p.importable else (p.version or 'present')}"
        for p in report.packages
    )
    print(f"packages: {pkgs} [measured]")
    for name, probe in report.commands.items():
        if probe.available:
            first_line = (probe.output or "").splitlines()[0] if probe.output else ""
            print(f"{name}: {first_line} [measured]")
        else:
            print(f"{name}: {probe.error} [not_available]")
    result = report.endpoint
    if result is None:
        print("endpoint: skipped")
    elif result.reachable:
        version = f" | vLLM version {result.vllm_version}" if result.vllm_version else ""
        print(
            f"endpoint {result.base_url}: reachable "
            f"(latency {result.latency_ms:.1f}ms){version} [measured]"
        )
        print(f"served models: {', '.join(result.served_models) or 'none reported'}")
        if result.configured_model:
            served = (
                "yes" if result.configured_model_served
                else "no" if result.configured_model_served is not None else "unknown"
            )
            print(
                f"configured VLLM_MODEL: {result.configured_model} (served: {served})"
            )
        else:
            print("configured VLLM_MODEL: not set — pick from served models above")
        if result.family_consistent is False:
            print(
                "note: configured model does not match VLLM_MODEL_FAMILY. If "
                "this is an operational fallback, set VLLM_MODEL_FAMILY "
                "accordingly so telemetry records it truthfully."
            )
    else:
        print(f"endpoint {result.base_url}: unreachable — {result.error}")
    print(f"policy: {report.policy}")
    print("env (redacted) [configured]:")
    for key, value in {**report.env_vllm, **report.env_fireworks}.items():
        print(f"  {key}={value}")


def main(
    argv: Optional[list[str]] = None,
    env: Optional[Mapping[str, str]] = None,
    session: Optional[requests.Session] = None,
    runner: CommandRunner = _default_runner,
) -> int:
    parser = argparse.ArgumentParser(
        prog="kaaval-runtime-probe",
        description="Record measured host/endpoint runtime facts with secrets "
        "redacted. JSON by default; never fails when host tools are absent.",
    )
    parser.add_argument("--text", action="store_true", help="human summary instead of JSON")
    parser.add_argument(
        "--output", type=Path, default=None, help="also write the JSON report here"
    )
    parser.add_argument(
        "--skip-endpoint", action="store_true", help="skip the vLLM HTTP probe"
    )
    parser.add_argument(
        "--require-endpoint",
        action="store_true",
        help="exit 1 unless the vLLM endpoint is reachable (for smoke scripts)",
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="endpoint probe timeout seconds"
    )
    args = parser.parse_args(argv)
    env = os.environ if env is None else env

    report = build_probe_report(
        env=env,
        session=session,
        runner=runner,
        include_endpoint=not args.skip_endpoint,
        timeout=args.timeout,
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report.model_dump_json(indent=2) + "\n", "utf-8")
    if args.text:
        _print_text(report)
        if args.output is not None:
            print(f"probe JSON written to {args.output}")
    else:
        print(report.model_dump_json(indent=2))

    if args.require_endpoint:
        if report.endpoint is None or not report.endpoint.reachable:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
