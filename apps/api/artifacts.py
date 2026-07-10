"""Artifact adapter for the Flight Deck API.

Resolves captured artifacts (telemetry, trajectory, runtime probe) with an
explicit precedence — real files under artifacts/ first, shipped sample data
under demo_artifacts/sample/ second, honest unavailability third — and
assembles the single dashboard payload the UI consumes.

Truth rules enforced here:
- provenance on every artifact: origin (artifacts | sample), artifact name,
  file modification time; never absolute filesystem paths, never env values.
- malformed JSON is skipped, never partially served.
- labels derive from data: MEASURED AMD RUN only when a probe artifact from
  artifacts/ actually reports AMD host facts; SAMPLE whenever shipped sample
  data is used; UNAVAILABLE when nothing exists.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

# Canonical names first, aliases after (produced by different scripts).
ARTIFACT_ALIASES: dict[str, list[str]] = {
    "telemetry": ["telemetry-truth.json", "demo-live-telemetry.json"],
    "trajectory": ["trajectory-sample.json", "demo-live-trajectory.json"],
    "runtime_probe": ["runtime-probe.json"],
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactStore:
    def __init__(
        self,
        artifacts_dir: Optional[Path] = None,
        sample_dir: Optional[Path] = None,
    ):
        self.artifacts_dir = artifacts_dir or (REPO_ROOT / "artifacts")
        self.sample_dir = sample_dir or (REPO_ROOT / "demo_artifacts" / "sample")

    def resolve(self, kind: str) -> tuple[Optional[object], dict]:
        """Return (data, provenance) for an artifact kind.

        Provenance never contains filesystem paths — only the artifact name,
        its origin class, and the file's modification timestamp.
        """
        names = ARTIFACT_ALIASES.get(kind)
        if names is None:
            raise KeyError(f"unknown artifact kind: {kind!r}")
        for base, origin in ((self.artifacts_dir, "artifacts"), (self.sample_dir, "sample")):
            for name in names:
                path = base / name
                if not path.exists():
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue  # malformed or unreadable: never partially served
                modified_at = datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat()
                return data, {
                    "available": True,
                    "artifact": name,
                    "origin": origin,
                    "modified_at": modified_at,
                }
        return None, {
            "available": False,
            "artifact": None,
            "origin": "not_available",
            "modified_at": None,
        }

    # -- label / status derivation (deterministic over artifact content) --

    @staticmethod
    def _amd_status(probe: Optional[dict], probe_prov: dict, telemetry: Optional[dict]) -> dict:
        """AMD runtime evidence status. Measured requires a real probe artifact
        whose host commands actually returned AMD facts — sample data or a
        probe without rocm-smi output can never claim measured."""
        if probe is not None and probe_prov.get("origin") == "artifacts":
            commands = probe.get("commands") or {}
            rocm = commands.get("rocm_smi_product") or {}
            if rocm.get("available") and rocm.get("source") == "measured":
                return {
                    "status": "measured",
                    "reason": "runtime probe artifact reports AMD host facts",
                }
            return {
                "status": "pending",
                "reason": "probe artifact exists but reports no AMD GPU facts",
            }
        runtime = (telemetry or {}).get("runtime") or {}
        if runtime.get("status") == "configured":
            return {
                "status": "configured",
                "reason": "serving settings configured; AMD GPU measured run pending",
            }
        return {
            "status": "pending",
            "reason": "AMD GPU measured run pending; no probe artifact captured yet",
        }

    @staticmethod
    def _label(
        telemetry: Optional[dict],
        telemetry_prov: dict,
        amd: dict,
    ) -> str:
        if telemetry is None:
            return "UNAVAILABLE"
        if telemetry_prov.get("origin") == "sample":
            return "SAMPLE"
        if amd["status"] == "measured":
            return "MEASURED AMD RUN"
        attempts = telemetry.get("attempts_detail") or []
        if any(a.get("provider") == "fireworks" for a in attempts):
            return "CAPTURED FIREWORKS RUN"
        return "CAPTURED LOCAL RUN"

    def dashboard(self) -> dict:
        telemetry, telemetry_prov = self.resolve("telemetry")
        trajectory, trajectory_prov = self.resolve("trajectory")
        probe, probe_prov = self.resolve("runtime_probe")

        amd = self._amd_status(probe, probe_prov, telemetry)
        used_sample = any(
            p.get("origin") == "sample"
            for p in (telemetry_prov, trajectory_prov, probe_prov)
        )
        return {
            "generated_at": _utcnow_iso(),
            "mode": "captured",
            "label": self._label(telemetry, telemetry_prov, amd),
            "used_sample": used_sample,
            "amd": amd,
            "provenance": {
                "telemetry": telemetry_prov,
                "trajectory": trajectory_prov,
                "runtime_probe": probe_prov,
            },
            "telemetry": telemetry,
            "trajectory": trajectory,
            "runtime_probe": probe,
        }
