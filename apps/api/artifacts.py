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

    def _resolve_bundle(self) -> dict:
        """Find the best coherent run bundle.
        
        Prefer real over sample. Prefer manifest over loose. Prefer newer.
        """
        def load_bundle(base_dir: Path, origin: str) -> list[dict]:
            bundles = []
            if not base_dir.exists():
                return bundles

            # 1. Manifest bundles
            manifest_path = base_dir / "demo-live-manifest.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    run_id = manifest["run_id"]
                    artifacts = manifest["artifacts"]
                    tel_name = artifacts["telemetry"]
                    traj_name = artifacts["trajectory"]
                    probe_name = artifacts.get("runtime_probe")

                    tel_path = base_dir / tel_name
                    traj_path = base_dir / traj_name
                    probe_path = base_dir / probe_name if probe_name else None

                    telemetry = json.loads(tel_path.read_text(encoding="utf-8"))
                    trajectory = json.loads(traj_path.read_text(encoding="utf-8"))
                    probe = json.loads(probe_path.read_text(encoding="utf-8")) if probe_path and probe_path.exists() else None

                    # Strict consistency check
                    consistent = True
                    reason = "coherent manifest bundle"
                    if telemetry.get("run_id") != run_id:
                        consistent = False
                        reason = "telemetry run_id mismatch"
                    elif not isinstance(trajectory, list):
                        consistent = False
                        reason = "trajectory is not a list"
                    elif any(r.get("request_id") != run_id for r in trajectory):
                        consistent = False
                        reason = "trajectory rows contain mismatched request_id"

                    if consistent:
                        mod_times = [manifest_path.stat().st_mtime, tel_path.stat().st_mtime, traj_path.stat().st_mtime]
                        if probe_path and probe_path.exists():
                            mod_times.append(probe_path.stat().st_mtime)
                        max_mod = max(mod_times)
                        
                        bundles.append({
                            "bundle_id": run_id,
                            "bundle_consistent": True,
                            "consistency_reason": reason,
                            "telemetry": telemetry,
                            "trajectory": trajectory,
                            "runtime_probe": probe,
                            "provenance": {
                                "telemetry": {"available": True, "artifact": tel_name, "origin": origin, "modified_at": datetime.fromtimestamp(tel_path.stat().st_mtime, tz=timezone.utc).isoformat()},
                                "trajectory": {"available": True, "artifact": traj_name, "origin": origin, "modified_at": datetime.fromtimestamp(traj_path.stat().st_mtime, tz=timezone.utc).isoformat()},
                                "runtime_probe": {"available": True, "artifact": probe_name, "origin": origin, "modified_at": datetime.fromtimestamp(probe_path.stat().st_mtime, tz=timezone.utc).isoformat()} if probe else {"available": False, "artifact": None, "origin": "not_available", "modified_at": None},
                            },
                            "max_mod_time": max_mod,
                            "origin": origin,
                        })
                except Exception:
                    pass

            # 2. Legacy loose files
            try:
                tel_name = "telemetry-truth.json"
                traj_name = "trajectory-sample.json"
                probe_name = "runtime-probe.json"
                
                tel_path = base_dir / tel_name
                traj_path = base_dir / traj_name
                probe_path = base_dir / probe_name

                # Try aliases if standard names don't exist
                if not tel_path.exists(): tel_name = "demo-live-telemetry.json"; tel_path = base_dir / tel_name
                if not traj_path.exists(): traj_name = "demo-live-trajectory.json"; traj_path = base_dir / traj_name

                if tel_path.exists():
                    telemetry = json.loads(tel_path.read_text(encoding="utf-8"))
                    
                    trajectory = None
                    if traj_path.exists():
                        try: trajectory = json.loads(traj_path.read_text(encoding="utf-8"))
                        except Exception: pass

                    probe = None
                    if probe_path.exists():
                        try: probe = json.loads(probe_path.read_text(encoding="utf-8"))
                        except Exception: pass
                        
                    run_id = telemetry.get("run_id")
                    
                    # Loosely check if trajectory matches
                    consistent = False
                    reason = "legacy loose artifacts"
                    if trajectory and isinstance(trajectory, list) and all(r.get("request_id") == run_id for r in trajectory):
                        consistent = True
                        reason = "legacy loose artifacts matching run_id"

                    mod_times = [tel_path.stat().st_mtime]
                    if trajectory: mod_times.append(traj_path.stat().st_mtime)
                    if probe: mod_times.append(probe_path.stat().st_mtime)
                    max_mod = max(mod_times)
                    
                    bundles.append({
                        "bundle_id": run_id,
                        "bundle_consistent": consistent,
                        "consistency_reason": reason,
                        "telemetry": telemetry,
                        "trajectory": trajectory,
                        "runtime_probe": probe,
                        "provenance": {
                            "telemetry": {"available": True, "artifact": tel_name, "origin": origin, "modified_at": datetime.fromtimestamp(tel_path.stat().st_mtime, tz=timezone.utc).isoformat()},
                            "trajectory": {"available": True, "artifact": traj_name, "origin": origin, "modified_at": datetime.fromtimestamp(traj_path.stat().st_mtime, tz=timezone.utc).isoformat()} if trajectory else {"available": False, "artifact": None, "origin": "not_available", "modified_at": None},
                            "runtime_probe": {"available": True, "artifact": probe_name, "origin": origin, "modified_at": datetime.fromtimestamp(probe_path.stat().st_mtime, tz=timezone.utc).isoformat()} if probe else {"available": False, "artifact": None, "origin": "not_available", "modified_at": None},
                        },
                        "max_mod_time": max_mod,
                        "origin": origin,
                    })
            except Exception:
                pass
                
            return bundles

        real_bundles = load_bundle(self.artifacts_dir, "artifacts")
        if real_bundles:
            real_bundles.sort(key=lambda b: b["max_mod_time"], reverse=True)
            return real_bundles[0]

        sample_bundles = load_bundle(self.sample_dir, "sample")
        if sample_bundles:
            sample_bundles.sort(key=lambda b: b["max_mod_time"], reverse=True)
            return sample_bundles[0]

        return {
            "bundle_id": None,
            "bundle_consistent": False,
            "consistency_reason": "no artifacts available",
            "telemetry": None,
            "trajectory": None,
            "runtime_probe": None,
            "provenance": {
                "telemetry": {"available": False, "artifact": None, "origin": "not_available", "modified_at": None},
                "trajectory": {"available": False, "artifact": None, "origin": "not_available", "modified_at": None},
                "runtime_probe": {"available": False, "artifact": None, "origin": "not_available", "modified_at": None},
            },
            "origin": "not_available"
        }

    def resolve(self, kind: str) -> tuple[Optional[object], dict]:
        bundle = self._resolve_bundle()
        data = bundle.get(kind)
        prov = bundle["provenance"].get(kind, {"available": False, "artifact": None, "origin": "not_available", "modified_at": None})
        return data, prov

    def resolve_comparison(self) -> tuple[Optional[object], dict]:
        """Resolve the newest Fireworks local-first vs always-remote comparison.

        This artifact is intentionally optional: the Flight Deck can prove a
        captured run without it, but when present it lets the UI show the cost
        avoidance receipt from recorded trajectory DBs.
        """
        if not self.artifacts_dir.exists():
            return None, {
                "available": False,
                "artifact": None,
                "origin": "not_available",
                "modified_at": None,
            }

        candidates = sorted(
            self.artifacts_dir.glob("fireworks-cost-comparison-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for path in candidates:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            return data, {
                "available": True,
                "artifact": path.name,
                "origin": "artifacts",
                "modified_at": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            }

        return None, {
            "available": False,
            "artifact": None,
            "origin": "not_available",
            "modified_at": None,
        }

    @staticmethod
    def _amd_status(bundle: dict) -> dict:
        """AMD runtime evidence status."""
        probe = bundle.get("runtime_probe")
        telemetry = bundle.get("telemetry")
        probe_prov = bundle["provenance"]["runtime_probe"]
        telemetry_prov = bundle["provenance"]["telemetry"]
        
        # Must be a coherent bundle, not legacy/mixed
        is_coherent = bundle.get("bundle_consistent", False) and bundle.get("consistency_reason") == "coherent manifest bundle"

        if probe and probe_prov.get("origin") == "artifacts" and telemetry and telemetry_prov.get("origin") == "artifacts":
            commands = probe.get("commands") or {}
            rocm = commands.get("rocm_smi_product") or {}
            
            # Check all conditions for MEASURED
            has_rocm = rocm.get("available") and rocm.get("source") == "measured"
            
            attempts = telemetry.get("attempts_detail") or []
            has_vllm_attempt = any(a.get("provider") == "vllm-gemma" and a.get("tier") == "local" for a in attempts)
            
            runtime = telemetry.get("runtime") or {}
            profile = runtime.get("profile") or {}
            endpoint_type = profile.get("endpoint_type")
            is_vllm_endpoint = endpoint_type == "openai_compatible" and profile.get("provider") == "vllm-gemma"
            
            tel_model = profile.get("model_id") or profile.get("model_family")
            endpoint_info = probe.get("endpoint") or {}
            probe_model = endpoint_info.get("configured_model") or endpoint_info.get("model_family")
            
            model_matches = (tel_model == probe_model) if (tel_model and probe_model) else False
            configured_served = endpoint_info.get("configured_model_served") is True
            
            # Check that no sample artifact participates in the bundle
            no_sample = all(p.get("origin") != "sample" for p in bundle["provenance"].values() if p.get("available"))

            if is_coherent and has_rocm and has_vllm_attempt and is_vllm_endpoint and model_matches and configured_served and no_sample:
                return {
                    "status": "measured",
                    "reason": "coherent bundle confirms local vLLM execution on measured AMD host",
                }
            
            # Build failure reasons
            reasons = []
            if not is_coherent: reasons.append("bundle not coherent manifest")
            if not has_rocm: reasons.append("no measured rocm-smi output")
            if not has_vllm_attempt: reasons.append("no local vllm-gemma attempt")
            if not is_vllm_endpoint: reasons.append("endpoint_type not openai_compatible or provider not vllm-gemma")
            if not model_matches: reasons.append("model mismatch between telemetry and probe")
            if not configured_served: reasons.append("configured model not confirmed served")
            if not no_sample: reasons.append("sample data in bundle")
            
            return {
                "status": "pending",
                "reason": f"missing evidence: {', '.join(reasons)}"
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
        bundle_consistent: bool = False,
    ) -> str:
        if telemetry is None:
            return "UNAVAILABLE"
        if telemetry_prov.get("origin") == "sample":
            return "SAMPLE"
        if not bundle_consistent:
            return "UNVERIFIED (INCONSISTENT BUNDLE)"
        if amd["status"] == "measured":
            return "MEASURED AMD RUN"
        attempts = telemetry.get("attempts_detail") or []
        if any(a.get("provider") == "fireworks" for a in attempts):
            return "CAPTURED FIREWORKS RUN"
        return "CAPTURED LOCAL RUN"

    def dashboard(self) -> dict:
        bundle = self._resolve_bundle()
        telemetry = bundle.get("telemetry")
        trajectory = bundle.get("trajectory")
        probe = bundle.get("runtime_probe")
        prov = bundle["provenance"]
        comparison, comparison_prov = self.resolve_comparison()

        amd = self._amd_status(bundle)
        used_sample = any(
            p.get("origin") == "sample"
            for p in prov.values() if p.get("available")
        )
        return {
            "generated_at": _utcnow_iso(),
            "mode": "captured",
            "label": self._label(telemetry, prov["telemetry"], amd, bundle.get("bundle_consistent", False)),
            "used_sample": used_sample,
            "amd": amd,
            "bundle_consistent": bundle.get("bundle_consistent", False),
            "bundle_id": bundle.get("bundle_id"),
            "consistency_reason": bundle.get("consistency_reason", "unavailable"),
            "provenance": prov,
            "comparison_provenance": comparison_prov,
            "telemetry": telemetry,
            "trajectory": trajectory,
            "runtime_probe": probe,
            "comparison": comparison,
        }
