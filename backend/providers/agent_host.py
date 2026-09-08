"""Validated observations imported from a supported Binance Agent OS host.

Binance owns authentication in the supported host (Codex). Cassa receives only
the minimum account facts needed for its deterministic, read-only planning
services. No OAuth token, API key, authorization URL, or account identifier is
accepted or stored here.
"""
from __future__ import annotations

import re
import time
from decimal import Decimal, InvalidOperation
from typing import Any

from ..store import load, save


SNAPSHOT_KEY = "agent_os_host_snapshot"
ASSET_RE = re.compile(r"^[A-Z0-9]{1,20}$")


def _amount(value: Any, field: str) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a decimal string") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{field} must be a finite, non-negative decimal")
    return format(amount, "f")


def _asset(value: Any, field: str = "asset") -> str:
    asset = str(value or "").strip().upper()
    if not ASSET_RE.fullmatch(asset):
        raise ValueError(f"{field} must contain 1-20 uppercase letters or digits")
    return asset


def record_agentic_snapshot(
    balances: list[dict[str, Any]],
    convert_routes: list[dict[str, Any]] | None = None,
    account_type: str = "SPOT",
    can_trade: bool | None = None,
) -> dict[str, Any]:
    """Validate and persist a supported-host observation without credentials."""
    free: dict[str, str] = {}
    locked: dict[str, str] = {}
    totals: dict[str, str] = {}
    for index, row in enumerate(balances):
        asset = _asset(row.get("asset"), f"balances[{index}].asset")
        if asset in totals:
            raise ValueError(f"duplicate balance asset: {asset}")
        free_amount = _amount(row.get("free", "0"), f"balances[{index}].free")
        locked_amount = _amount(row.get("locked", "0"), f"balances[{index}].locked")
        total = Decimal(free_amount) + Decimal(locked_amount)
        if total == 0:
            continue
        free[asset] = free_amount
        locked[asset] = locked_amount
        totals[asset] = format(total, "f")

    routes: list[dict[str, Any]] = []
    seen_routes: set[tuple[str, str]] = set()
    for index, row in enumerate(convert_routes or []):
        from_asset = _asset(row.get("from_asset"), f"convert_routes[{index}].from_asset")
        to_asset = _asset(row.get("to_asset", "USDC"), f"convert_routes[{index}].to_asset")
        key = (from_asset, to_asset)
        if key in seen_routes:
            raise ValueError(f"duplicate convert route: {from_asset}/{to_asset}")
        seen_routes.add(key)
        supported = bool(row.get("supported"))
        minimum = row.get("minimum_from_amount")
        routes.append(
            {
                "from_asset": from_asset,
                "to_asset": to_asset,
                "supported": supported,
                "minimum_from_amount": _amount(minimum, f"convert_routes[{index}].minimum_from_amount")
                if minimum is not None
                else None,
            }
        )

    now = int(time.time())
    snapshot = {
        "source": "binance-agent-os-mcp-via-codex",
        "evidence_level": "supported-host-observation",
        "account_scope": "agentic-sub-account",
        "account_type": str(account_type or "SPOT").upper(),
        "can_trade": can_trade,
        "balances": totals,
        "free": free,
        "locked": locked,
        "convert_routes": routes,
        "captured_at": now,
        "writes_enabled": False,
    }
    save(SNAPSHOT_KEY, snapshot)
    return snapshot


def get_agentic_snapshot() -> dict[str, Any] | None:
    snapshot = load(SNAPSHOT_KEY, None)
    return snapshot if isinstance(snapshot, dict) and snapshot.get("captured_at") else None


def agent_host_status() -> dict[str, Any]:
    snapshot = get_agentic_snapshot()
    captured_at = int(snapshot.get("captured_at", 0)) if snapshot else None
    age_seconds = max(0, int(time.time()) - captured_at) if captured_at else None
    return {
        "state": "synced" if snapshot else "awaiting_agent_sync",
        "connected": bool(snapshot),
        "snapshot_available": bool(snapshot),
        "supported_host": "Codex",
        "authorization_owner": "supported-agent-host",
        "app_has_credentials": False,
        "account_scope": "agentic-sub-account",
        "access": "read-only-snapshot",
        "last_success_at": captured_at,
        "age_seconds": age_seconds,
        "stale": age_seconds is None or age_seconds > 300,
        "writes_enabled": False,
        "sync_prompt": "Sync my Agentic account balances to Cassa. Do not trade, convert, or transfer anything.",
    }
