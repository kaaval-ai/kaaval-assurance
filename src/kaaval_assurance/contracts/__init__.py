"""Contract registry: lookup by contract_id, optionally pinned to a version."""

from .base import FieldSpec, GroundingRule, TaskContract
from .support import ALL_CONTRACTS as SUPPORT_CONTRACTS
from .telecom import ALL_CONTRACTS as TELECOM_CONTRACTS

ALL_CONTRACTS = [*TELECOM_CONTRACTS, *SUPPORT_CONTRACTS]

_REGISTRY: dict[tuple[str, str], TaskContract] = {c.key: c for c in ALL_CONTRACTS}


def get_contract(contract_id: str, version: str | None = None) -> TaskContract:
    """Return the contract, latest version if none pinned. KeyError if absent."""
    if version is not None:
        return _REGISTRY[(contract_id, version)]
    candidates = [c for c in _REGISTRY.values() if c.contract_id == contract_id]
    if not candidates:
        raise KeyError(f"unknown contract_id: {contract_id!r}")
    return max(candidates, key=lambda c: c.version)


def list_contracts() -> list[TaskContract]:
    return list(_REGISTRY.values())


__all__ = [
    "FieldSpec",
    "GroundingRule",
    "TaskContract",
    "get_contract",
    "list_contracts",
]
