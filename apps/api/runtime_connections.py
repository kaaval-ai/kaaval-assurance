"""Credential-safe, ephemeral runtime connections for interactive sessions."""

from __future__ import annotations

import os
import ipaddress
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Literal, Optional
from urllib.parse import urlparse

import requests

from kaaval_assurance.contracts import TaskContract
from kaaval_assurance.models import ModelResponse
from kaaval_assurance.providers import (
    FireworksConfig,
    FireworksProvider,
    OllamaProvider,
    Provider,
    VllmConfig,
    VllmProvider,
)
from kaaval_assurance.providers.fireworks import DEFAULT_BASE_URL as FIREWORKS_BASE_URL
from kaaval_assurance.providers.vllm import base_url_host

RuntimeProvider = Literal["fireworks", "ollama", "vllm", "openai_compatible"]
RuntimeRole = Literal["primary", "escalation"]

DEFAULT_LOCAL_URLS = {
    "ollama": "http://host.docker.internal:11434/v1",
    "vllm": "http://host.docker.internal:8000/v1",
}


class RuntimeConnectionError(RuntimeError):
    """A safe runtime onboarding error that never includes credentials."""


class UnconfiguredProvider(Provider):
    """Fail closed when a live session has no escalation runtime."""

    def __init__(self, tier: Literal["local", "remote"] = "remote"):
        self.provider_name = "not-configured"
        self.model_id = "no-runtime"
        self.tier = tier

    def generate(
        self, request_id: str, task_input: str, contract: TaskContract
    ) -> ModelResponse:
        raise RuntimeConnectionError(f"{self.tier} runtime is not configured")


def deployment_mode() -> str:
    value = os.environ.get("KAAVAL_DEPLOYMENT_MODE", "local").strip().lower()
    return value if value in {"local", "hosted"} else "local"


def byok_allowed() -> bool:
    return os.environ.get("KAAVAL_ALLOW_BYOK", "") == "1"


def custom_endpoints_allowed() -> bool:
    return os.environ.get("KAAVAL_ALLOW_CUSTOM_ENDPOINTS", "") == "1"


def _normalise_base_url(provider: RuntimeProvider, base_url: Optional[str]) -> str:
    if provider == "fireworks":
        return FIREWORKS_BASE_URL
    value = (base_url or DEFAULT_LOCAL_URLS.get(provider, "")).strip().rstrip("/")
    if not value:
        raise ValueError("base_url is required for this runtime")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("base_url must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("base_url must not contain credentials, query, or fragment")

    local_hosts = {"localhost", "127.0.0.1", "::1", "host.docker.internal"}
    configured_hosts = {
        host.strip().lower()
        for host in os.environ.get("KAAVAL_RUNTIME_HOST_ALLOWLIST", "").split(",")
        if host.strip()
    }
    host = parsed.hostname.lower()
    if provider in {"ollama", "vllm"}:
        if deployment_mode() == "hosted" and not custom_endpoints_allowed():
            raise ValueError(
                "local Ollama/vLLM endpoints are unavailable from hosted mode; "
                "use Fireworks BYOK or an operator-enabled HTTPS tunnel"
            )
        if host not in local_hosts | configured_hosts and not custom_endpoints_allowed():
            raise ValueError(
                "runtime host is not allowed; use host.docker.internal or configure "
                "KAAVAL_RUNTIME_HOST_ALLOWLIST"
            )
    elif provider == "openai_compatible":
        if not custom_endpoints_allowed():
            raise ValueError("custom endpoints are disabled by the server operator")
        if deployment_mode() == "hosted" and parsed.scheme != "https":
            raise ValueError("hosted custom endpoints must use HTTPS")
        if deployment_mode() == "hosted":
            try:
                addresses = {
                    item[4][0]
                    for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)
                }
            except socket.gaierror as exc:
                raise ValueError("custom endpoint hostname could not be resolved") from exc
            if not addresses or any(
                not ipaddress.ip_address(address).is_global for address in addresses
            ):
                raise ValueError("hosted custom endpoints must resolve to public addresses")
    return value


@dataclass
class RuntimeConnection:
    connection_id: str
    provider: RuntimeProvider
    role: RuntimeRole
    model_id: str
    base_url: str
    api_key: str
    model_family: str
    structured_outputs: bool
    hardware_target: str
    timeout_seconds: float
    max_tokens: int
    created_at: float
    last_accessed: float

    @property
    def tier(self) -> Literal["local", "remote"]:
        return "local" if self.role == "primary" else "remote"

    @property
    def spends_credits(self) -> bool:
        return self.provider == "fireworks"

    def public_metadata(self, ttl_seconds: int) -> dict:
        return {
            "connection_id": self.connection_id,
            "provider": self.provider,
            "role": self.role,
            "model_id": self.model_id,
            "model_family": self.model_family,
            "endpoint_host": base_url_host(self.base_url),
            "structured_outputs": self.structured_outputs,
            "hardware_target": self.hardware_target,
            "requires_spend_confirmation": self.spends_credits,
            "expires_in_seconds": ttl_seconds,
        }

    def build_provider(self) -> Provider:
        if self.provider == "fireworks":
            return FireworksProvider(
                FireworksConfig(
                    api_key=self.api_key,
                    model=self.model_id,
                    base_url=self.base_url,
                    timeout_seconds=self.timeout_seconds,
                    max_tokens=self.max_tokens,
                ),
                tier=self.tier,
            )

        cfg = VllmConfig(
            model=self.model_id,
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
            api_key=self.api_key,
            dtype="bfloat16" if self.provider == "vllm" else "",
            kv_cache_dtype="auto" if self.provider == "vllm" else "",
            enable_prefix_caching=self.provider == "vllm",
            gpu_memory_utilization=0.0,
            tensor_parallel_size=1,
            structured_outputs=self.structured_outputs,
            hardware_target=self.hardware_target,
            model_family=self.model_family,
        )
        if self.provider == "ollama":
            return OllamaProvider(cfg, tier=self.tier)
        return VllmProvider(
            cfg,
            tier=self.tier,
            provider_name=(
                "vllm-gemma" if self.provider == "vllm" else "openai-compatible"
            ),
        )


class RuntimeConnectionManager:
    def __init__(self, ttl_seconds: int = 900, max_connections: int = 64):
        self.ttl_seconds = ttl_seconds
        self.max_connections = max_connections
        self._connections: dict[str, RuntimeConnection] = {}
        self._lock = threading.Lock()

    def _cleanup_locked(self) -> None:
        now = time.time()
        expired = [
            connection_id
            for connection_id, connection in self._connections.items()
            if now - connection.last_accessed > self.ttl_seconds
        ]
        for connection_id in expired:
            del self._connections[connection_id]
        while len(self._connections) >= self.max_connections:
            oldest = min(self._connections.values(), key=lambda item: item.last_accessed)
            del self._connections[oldest.connection_id]

    def create(
        self,
        *,
        provider: RuntimeProvider,
        role: RuntimeRole,
        model_id: str,
        api_key: str = "",
        base_url: Optional[str] = None,
        model_family: str = "",
        structured_outputs: Optional[bool] = None,
        hardware_target: str = "",
        timeout_seconds: float = 30.0,
        max_tokens: int = 1024,
        probe: bool = True,
    ) -> RuntimeConnection:
        if not byok_allowed():
            raise ValueError("runtime onboarding is disabled by the server operator")
        model_id = model_id.strip()
        if not model_id:
            raise ValueError("model_id is required")
        if provider == "fireworks" and not api_key.strip():
            raise ValueError("Fireworks API key is required")
        if not 1 <= timeout_seconds <= 120:
            raise ValueError("timeout_seconds must be between 1 and 120")
        if not 32 <= max_tokens <= 4096:
            raise ValueError("max_tokens must be between 32 and 4096")

        resolved_url = _normalise_base_url(provider, base_url)
        family = model_family.strip() or (
            "gemma" if provider in {"ollama", "vllm"} else "unknown"
        )
        structured = (
            provider in {"vllm", "openai_compatible"}
            if structured_outputs is None
            else structured_outputs
        )
        target = hardware_target.strip() or {
            "fireworks": "fireworks-hosted",
            "ollama": "local-ollama",
            "vllm": "local-vllm",
            "openai_compatible": "user-endpoint",
        }[provider]
        now = time.time()
        connection = RuntimeConnection(
            connection_id=f"rtc-{uuid.uuid4().hex}",
            provider=provider,
            role=role,
            model_id=model_id,
            base_url=resolved_url,
            api_key=api_key.strip(),
            model_family=family,
            structured_outputs=structured,
            hardware_target=target,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            created_at=now,
            last_accessed=now,
        )
        if probe:
            self.probe(connection)
        with self._lock:
            self._cleanup_locked()
            self._connections[connection.connection_id] = connection
        return connection

    def probe(self, connection: RuntimeConnection) -> None:
        headers = {}
        if connection.api_key:
            headers["Authorization"] = f"Bearer {connection.api_key}"
        try:
            response = requests.get(
                f"{connection.base_url.rstrip('/')}/models",
                headers=headers,
                timeout=min(connection.timeout_seconds, 15.0),
            )
        except requests.RequestException as exc:
            raise RuntimeConnectionError(
                f"runtime connection failed: {type(exc).__name__}"
            ) from exc
        if response.status_code != 200:
            raise RuntimeConnectionError(
                f"runtime connection returned HTTP {response.status_code}"
            )
        if connection.provider in {"ollama", "vllm"}:
            try:
                payload = response.json()
                served_models = {
                    str(item["id"])
                    for item in payload["data"]
                    if isinstance(item, dict) and item.get("id")
                }
            except (ValueError, KeyError, TypeError) as exc:
                raise RuntimeConnectionError(
                    "runtime model inventory response was invalid"
                ) from exc
            if connection.model_id not in served_models:
                available = ", ".join(sorted(served_models)) or "none"
                raise RuntimeConnectionError(
                    f"model '{connection.model_id}' is not served by this runtime; "
                    f"available models: {available}"
                )

    def get(
        self, connection_id: str, role: Optional[RuntimeRole] = None
    ) -> RuntimeConnection:
        with self._lock:
            self._cleanup_locked()
            connection = self._connections.get(connection_id)
            if connection is None:
                raise KeyError("runtime connection not found or expired")
            if role is not None and connection.role != role:
                raise ValueError(f"runtime connection role must be {role}")
            connection.last_accessed = time.time()
            return connection

    def delete(self, connection_id: str) -> bool:
        with self._lock:
            return self._connections.pop(connection_id, None) is not None


runtime_connection_manager = RuntimeConnectionManager()
