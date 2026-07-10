"""Static claims-integrity guard for the Flight Deck frontend.

Fails if fabricated-claim vocabulary or generic mock providers reappear in
apps/flight-deck/src, and if judge-facing metrics regain simulated variation.
"""

from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "apps" / "flight-deck" / "src"

BANNED_STRINGS = [
    "SEV-SNP",
    "cryptographic attestation",
    "launch digest",
    "launchDigest",
    "hardware tamper",
    "GPT-4o",
    "Claude 3.5",
    "Gemini Pro",
    "AWS Nitro",
    "PII Redaction",
    "hallucinationRate",
    "Sigstore",
    "Presidio",
]


def _source_files():
    files = [
        p
        for p in SRC.rglob("*")
        if p.suffix in (".ts", ".tsx", ".css", ".html") and p.is_file()
    ]
    assert files, "flight deck source not found"
    return files


def test_no_fabricated_claim_strings():
    offenders = []
    for path in _source_files():
        content = path.read_text(encoding="utf-8")
        for banned in BANNED_STRINGS:
            if banned in content:
                offenders.append(f"{path.name}: {banned}")
    assert not offenders, f"fabricated-claim strings found: {offenders}"


def test_no_simulated_variation_in_metrics():
    offenders = [
        p.name for p in _source_files() if "Math.random(" in p.read_text("utf-8")
    ]
    assert not offenders, f"Math.random in judge-facing UI: {offenders}"
