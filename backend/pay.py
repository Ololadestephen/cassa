from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from . import mcp_client
from .obligations import ACTIVE_STATUSES, get_obligation, reserved_usdc, update_obligation_status
from .execution import begin_execution, finish_execution, get_execution
from .policy import check_pay_policy, normalize_recipient_id
from .store import get_config, log_activity


async def preview_pay(to: str, amount: float, asset: str, memo: str, obligation_id: int | None = None) -> dict:
    asset = (asset or "USDC").upper()
    if asset not in ("USDC", "BTC", "ETH", "SOL", "BNB"):
        return {"ok": False, "error": f"Unsupported asset '{asset}'. Use USDC, BTC, ETH, SOL, or BNB."}
    obligation = None
    if obligation_id is not None:
        obligation = get_obligation(obligation_id)
        if obligation is None:
            return {"ok": False, "error": "Linked obligation was not found"}
        if obligation["status"] not in ACTIVE_STATUSES:
            return {"ok": False, "error": f"Linked obligation is already {obligation['status']}"}
        if obligation["asset"] != asset or Decimal(obligation["amount"]) != Decimal(str(amount)):
            return {"ok": False, "error": "Payment amount and asset must match the linked obligation"}
        if obligation.get("recipient") and normalize_recipient_id(to) != normalize_recipient_id(obligation["recipient"]):
            return {"ok": False, "error": "Payment recipient must match the linked obligation"}
    quote = None
    if asset != "USDC":
        quote = await mcp_client.quote_convert_from_market(asset, "USDC", amount)
        if not isinstance(quote, dict) or quote.get("est_receive") is None:
            return {"ok": False, "error": f"A current USDC valuation is required for {asset}"}
        amount_usdc = quote["est_receive"]
    else:
        amount_usdc = amount
    verdict = check_pay_policy(to, amount, asset, amount_usdc=amount_usdc)
    if not verdict["allowed"]:
        return {"ok": False, "error": verdict["error"]}
    funding = None
    if asset == "USDC":
        available = Decimal(str(await mcp_client.get_spendable_balance("USDC")))
        reserved = reserved_usdc(exclude_id=obligation_id)
        reserve = Decimal(str(get_config().get("minimum_reserve_usdc", 50)))
        spendable = max(Decimal("0"), available - reserved - reserve)
        funding = {
            "available_usdc": float(available),
            "other_obligations_usdc": float(reserved),
            "minimum_reserve_usdc": float(reserve),
            "spendable_usdc": float(spendable),
        }
        if Decimal(str(amount)) > spendable:
            return {
                "ok": False,
                "error": f"Only {float(spendable):g} USDC is spendable after obligations and the minimum reserve. Prepare funding first.",
                "funding": funding,
            }
    return {
        "ok": True,
        "rail": "internal-transfer",
        "to": verdict["recipient"],
        "amount": amount,
        "asset": asset,
        "memo": memo or "",
        "quote_usdc": quote,
        "amount_usdc": verdict["amount_usdc"],
        "needs_confirm": verdict["needs_confirm"],
        "caps": verdict["caps"],
        "funding": funding,
        "obligation_id": obligation_id,
    }


async def execute_pay(
    to: str,
    amount: float,
    asset: str,
    memo: str,
    dry_run: bool,
    confirmed: bool,
    obligation_id: int | None = None,
    operation_id: str | None = None,
) -> dict:
    asset = (asset or "USDC").upper()
    operation_id = operation_id or str(uuid4())
    request_snapshot = {
        "to": normalize_recipient_id(to),
        "amount": str(amount),
        "asset": asset,
        "memo": memo or "",
        "obligation_id": obligation_id,
    }
    if not dry_run:
        existing = get_execution(operation_id)
        if existing:
            if existing.get("request") != request_snapshot:
                return {"ok": False, "error": "operation_id was already used for a different payment", "operation_id": operation_id}
            if existing.get("state") == "completed":
                return {**(existing.get("result") or {}), "duplicate": True}
            return {
                "ok": False,
                "error": f"Payment operation is {existing.get('state')}; reconcile it before retrying.",
                "operation_id": operation_id,
                "state": existing.get("state"),
            }
    preview = await preview_pay(to, amount, asset, memo, obligation_id)
    if not preview.get("ok"):
        return preview
    if not confirmed and not dry_run:
        return {
            "ok": False,
            "needs_confirm": True,
            "preview": preview,
            "message": "Confirm this exact payment before execution.",
        }
    if not dry_run:
        created, existing = begin_execution(operation_id, "pay", request_snapshot)
        if not created:
            if existing.get("request") != request_snapshot:
                return {"ok": False, "error": "operation_id was already used for a different payment", "operation_id": operation_id}
            if existing.get("state") == "completed":
                return {**(existing.get("result") or {}), "duplicate": True}
            return {
                "ok": False,
                "error": f"Payment operation is {existing.get('state')}; reconcile it before retrying.",
                "operation_id": operation_id,
                "state": existing.get("state"),
            }
    destination = str(preview["to"].get("email_or_uid", ""))
    try:
        result = await mcp_client.internal_transfer(asset, amount, destination, dry_run)
    except Exception as exc:
        response = {
            "ok": False,
            "error": "Provider response was ambiguous. Reconcile before retrying.",
            "detail": str(exc),
            "operation_id": operation_id,
            "state": "needs_reconciliation",
        }
        if not dry_run:
            finish_execution(operation_id, "needs_reconciliation", response)
        return response
    if not result.get("ok"):
        response = {"ok": False, "error": result.get("error", "Transfer failed"), "preview": preview, "operation_id": operation_id}
        if not dry_run:
            finish_execution(operation_id, "failed", response)
        return response
    record = None
    if not dry_run:
        record = log_activity(
            {
                "type": "pay",
                "day": datetime.now(UTC).strftime("%Y-%m-%d"),
                "ok": True,
                "to": normalize_recipient_id(to),
                "amount": amount,
                "amount_usdc": preview.get("amount_usdc"),
                "asset": asset,
                "memo": memo or "",
                "rail": "internal-transfer",
                "mode": result.get("source"),
                "operation_id": operation_id,
            }
        )
        if obligation_id is not None:
            update_obligation_status(obligation_id, "paid")
    response = {
        "ok": True,
        "dry_run": dry_run,
        "rail": "internal-transfer",
        "payment": result,
        "preview": preview,
        "ledger_entry_id": (record or {}).get("ledger_entry_id"),
        "operation_id": operation_id,
    }
    if not dry_run:
        finish_execution(operation_id, "completed", response)
    return response
