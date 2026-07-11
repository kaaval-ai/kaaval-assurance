"""Model comparison helper: one case, several local candidates, Layer 1 judges.

    python -m kaaval_assurance.compare --case-id sev-001

Runs one gold case against the mock baseline plus any configured Ollama
models (Gemma preferred; Qwen only as local comparison/fallback) and exports
artifacts/model-comparison.{json,md}. Providers are injectable so tests run
without a live Ollama. The AMD vLLM Gemma tier remains the Track 3 proof
target — this comparison is a development aid, not the AMD evidence.
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional

from pydantic import BaseModel, Field

from .contracts import get_contract
from .eval.dataset import load_dataset
from .providers import MockProvider, Provider
from .providers.ollama import OllamaProvider, ollama_config_from_env
from .verifier import verify

FRAMING_NOTE = (
    "Gemma is the preferred model family for the hackathon story; Qwen runs "
    "only as a local comparison/fallback. The AMD vLLM Gemma tier is the "
    "Track 3 proof target; this comparison is a development aid on the mock/"
    "Ollama tiers and claims no AMD runtime."
)


class ComparisonEntry(BaseModel):
    label: str
    provider: str
    model_id: str
    verifier_passed: Optional[bool] = None  # None when the call errored
    verifier_failures: list[str] = Field(default_factory=list)
    checks_run: int = 0
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    raw_text_excerpt: str = ""
    error: Optional[str] = None


class ComparisonReport(BaseModel):
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    case_id: str
    contract_id: str
    category: str
    task_input: str
    entries: list[ComparisonEntry] = Field(default_factory=list)
    note: str = FRAMING_NOTE


def run_model_comparison(
    task_input: str,
    contract_id: str,
    providers: dict[str, Provider],
    case_id: str = "compare",
) -> ComparisonReport:
    """Generate + Layer-1 verify the same input on each provider. One call
    per provider, no escalation — a like-for-like candidate comparison."""
    contract = get_contract(contract_id)
    report = ComparisonReport(
        case_id=case_id,
        contract_id=contract_id,
        category=contract.category,
        task_input=task_input,
    )
    for label, provider in providers.items():
        try:
            response = provider.generate(f"compare-{case_id}", task_input, contract)
        except Exception as e:  # a dead endpoint must not kill the comparison
            report.entries.append(
                ComparisonEntry(
                    label=label,
                    provider=getattr(provider, "provider_name", "unknown"),
                    model_id=getattr(provider, "model_id", "unknown"),
                    error=f"{type(e).__name__}: {e}",
                )
            )
            continue
        verification = verify(response, contract, task_input)
        report.entries.append(
            ComparisonEntry(
                label=label,
                provider=response.provider,
                model_id=response.model_id,
                verifier_passed=verification.passed,
                verifier_failures=verification.failures,
                checks_run=verification.checks_run,
                latency_ms=response.latency_ms,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                cost_usd=response.cost_usd,
                raw_text_excerpt=response.raw_text[:200],
            )
        )
    return report


def default_comparison_providers(
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, Provider]:
    """Mock baseline always; Ollama Gemma/Qwen only when configured."""
    env = os.environ if env is None else env
    providers: dict[str, Provider] = {
        "mock-baseline": MockProvider(tier="local")
    }
    try:
        gemma_config = ollama_config_from_env(env)
        providers[f"ollama-{gemma_config.model_family}"] = OllamaProvider(gemma_config)
    except ValueError:
        pass  # OLLAMA_MODEL not set; comparison stays mock-only
    qwen_model = (env.get("OLLAMA_QWEN_MODEL") or "").strip()
    if qwen_model:
        base = ollama_config_from_env(
            {**env, "OLLAMA_MODEL": qwen_model, "OLLAMA_MODEL_FAMILY": "qwen"}
        )
        providers["ollama-qwen"] = OllamaProvider(base)
    return providers


def _markdown(report: ComparisonReport) -> str:
    lines = [
        "# Model comparison",
        "",
        f"Case `{report.case_id}` — contract `{report.contract_id}` — "
        f"recorded {report.created_at.isoformat()}.",
        "",
        f"**Task input:** {report.task_input}",
        "",
        "| Candidate | Provider | Model | Layer 1 | Failed checks | Latency | Tokens |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in report.entries:
        if e.error is not None:
            outcome, failures = f"error: {e.error[:60]}", "—"
        else:
            outcome = "pass" if e.verifier_passed else "FAIL"
            failures = ", ".join(e.verifier_failures) or "none"
        lines.append(
            f"| {e.label} | {e.provider} | {e.model_id} | {outcome} | "
            f"{failures} | {e.latency_ms:.0f}ms | "
            f"{e.prompt_tokens}+{e.completion_tokens} |"
        )
    lines += ["", report.note]
    return "\n".join(lines)


def export_model_comparison(
    report: ComparisonReport, out_dir: Path
) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "model-comparison.json"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", "utf-8")
    md_path = out_dir / "model-comparison.md"
    md_path.write_text(_markdown(report) + "\n", "utf-8")
    return [json_path, md_path]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kaaval-compare",
        description="Compare configured local model candidates on one gold case.",
    )
    parser.add_argument("--dataset", default="data/eval/telecom_gold.jsonl")
    parser.add_argument("--case-id", default="sev-001")
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args(argv)

    cases = {c.case_id: c for c in load_dataset(args.dataset)}
    if args.case_id not in cases:
        print(f"error: unknown case_id {args.case_id!r}", file=sys.stderr)
        return 2
    case = cases[args.case_id]

    providers = default_comparison_providers()
    report = run_model_comparison(
        case.task_input, case.contract_id, providers, case_id=case.case_id
    )
    paths = export_model_comparison(report, args.out_dir)
    for entry in report.entries:
        status = (
            f"error ({entry.error})"
            if entry.error
            else ("pass" if entry.verifier_passed else "FAIL")
        )
        print(f"{entry.label}: {entry.model_id} -> Layer 1 {status}")
    print("written:", ", ".join(str(p) for p in paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
