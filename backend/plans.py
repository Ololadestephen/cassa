import json
import time
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from . import mcp_client
from .db import transaction
from .execution import claim_plan_execution, finish_execution, get_execution
from .obligations import (
    ACTIVE_STATUSES,
    get_asset_policies,
    get_obligation,
    reserved_usdc,
    update_obligation_status,
)
from .services.affordability import assess_affordability
from .store import get_config, is_mock, log_activity


def _decode(value):
    return json.loads(value) if value else None


def _plan(row, steps=None) -> dict:
    return {
        "id": row["id"],
        "version": row["version"],
        "state": row["state"],
        "request": _decode(row["request_json"]),
        "assessment": _decode(row["assessment_json"]),
        "expires_at": row["expires_at"],
        "approval": _decode(row["approval_json"]),
        "result": _decode(row["result_json"]),
        "steps": steps or [],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_plan(plan_id: str) -> dict | None:
    with transaction() as conn:
        row = conn.execute("SELECT * FROM funding_plans WHERE id=?", (plan_id,)).fetchone()
        if row is None:
            return None
        step_rows = conn.execute(
            "SELECT * FROM plan_steps WHERE plan_id=? ORDER BY ordinal", (plan_id,)
        ).fetchall()
    steps = [
        {
            "ordinal": step["ordinal"],
            "kind": step["kind"],
            "state": step["state"],
            "input": _decode(step["input_json"]),
            "result": _decode(step["result_json"]),
            "provider_id": step["provider_id"],
        }
        for step in step_rows
    ]
    return _plan(row, steps)


def list_plans(limit: int = 20) -> list[dict]:
    with transaction() as conn:
        rows = conn.execute(
            "SELECT id FROM funding_plans ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [get_plan(row["id"]) for row in rows]


def _prepare_obligation_request(request: dict) -> dict:
    prepared = dict(request)
    obligation_id = prepared.get("obligation_id")
    if obligation_id is None:
        return prepared
    obligation = get_obligation(obligation_id)
    if obligation is None:
        raise ValueError("Obligation not found")
    if obligation["status"] not in ACTIVE_STATUSES:
        raise ValueError(f"Obligation is already {obligation['status']}")
    if obligation["asset"] != "USDC":
        raise ValueError("Funding plans currently support USDC obligations only")
    if Decimal(str(prepared["amount"])) != Decimal(obligation["amount"]):
        raise ValueError("Plan amount must match the linked obligation")
    requested_recipient = prepared.get("recipient")
    saved_recipient = obligation.get("recipient")
    if requested_recipient and saved_recipient and requested_recipient != saved_recipient:
        raise ValueError("Plan recipient must match the linked obligation")
    if not requested_recipient and saved_recipient:
        prepared["recipient"] = saved_recipient
    return prepared


async def create_funding_plan(request: dict) -> dict:
    request = _prepare_obligation_request(request)
    assessment = await assess_affordability(
        request["amount"],
        request.get("payment_fee", 0),
        request.get("minimum_reserve"),
        request.get("obligation_id"),
        request.get("recipient"),
        request.get("allowed_assets"),
    )
    plan_id = str(uuid4())
    expires_at = int(time.time()) + int(request.get("validity_seconds", 600))
    state = (
        "awaiting_approval"
        if assessment["outcome"] in {"affordable_now", "affordable_after_conversions"}
        else "blocked"
    )
    max_fee = Decimal(str(request.get("max_conversion_fee_pct", 2.5)))
    for conversion in assessment.get("selected_conversions", []):
        gross = Decimal(str(conversion.get("gross_usdc", 0)))
        fee = Decimal(str(conversion.get("fee_usdc", 0)))
        if gross and fee / gross * 100 > max_fee:
            state = "blocked"
            assessment["outcome"] = "blocked_by_conversion_cost"
            assessment["cost_error"] = f"Estimated conversion fee exceeds {max_fee}%"
    steps = [
        {"kind": "dust_conversion", "input": conversion}
        for conversion in assessment.get("selected_conversions", [])
    ]
    with transaction() as conn:
        conn.execute(
            """INSERT INTO funding_plans(id, version, state, request_json, assessment_json, expires_at)
               VALUES (?, 1, ?, ?, ?, ?)""",
            (
                plan_id,
                state,
                json.dumps(request, sort_keys=True),
                json.dumps(assessment, sort_keys=True),
                expires_at,
            ),
        )
        for ordinal, step in enumerate(steps, 1):
            conn.execute(
                "INSERT INTO plan_steps(plan_id, ordinal, kind, state, input_json) VALUES (?, ?, ?, 'pending', ?)",
                (plan_id, ordinal, step["kind"], json.dumps(step["input"], sort_keys=True)),
            )
        if request.get("obligation_id") is not None:
            conn.execute(
                "INSERT INTO obligation_plan_links(obligation_id, plan_id) VALUES (?, ?)",
                (request["obligation_id"], plan_id),
            )
    return get_plan(plan_id)


def _release_asset_locks(plan_id: str, conn=None) -> None:
    if conn is not None:
        conn.execute("DELETE FROM plan_asset_locks WHERE plan_id=?", (plan_id,))
        return
    with transaction() as owned:
        owned.execute("DELETE FROM plan_asset_locks WHERE plan_id=?", (plan_id,))


def _expire_plan(plan_id: str, message: str) -> None:
    result = {"ok": False, "state": "expired", "error": message}
    with transaction() as conn:
        conn.execute(
            "UPDATE funding_plans SET state='expired', result_json=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (json.dumps(result, sort_keys=True), plan_id),
        )
        _release_asset_locks(plan_id, conn)


def approve_plan(plan_id: str, version: int, confirmed: bool) -> dict:
    plan = get_plan(plan_id)
    if plan is None:
        raise LookupError("Funding plan not found")
    if not confirmed:
        raise ValueError("Approval requires confirmed=true")
    if plan["version"] != version:
        raise ValueError("Plan version changed; review the current plan")
    if plan["state"] != "awaiting_approval":
        raise ValueError(f"Plan cannot be approved from state {plan['state']}")
    now = int(time.time())
    if now >= plan["expires_at"]:
        _expire_plan(plan_id, "Plan expired before approval")
        raise ValueError("Plan expired; create a fresh plan")
    assets = [step["input"]["asset"] for step in plan["steps"]]
    approval = {
        "confirmed": True,
        "version": version,
        "approved_at": now,
        "assets": assets,
        "max_conversion_fee_pct": plan["request"].get("max_conversion_fee_pct", 2.5),
        "max_slippage_pct": plan["request"].get("max_slippage_pct", 1),
    }
    with transaction() as conn:
        conn.execute("DELETE FROM plan_asset_locks WHERE expires_at<=?", (now,))
        for asset in assets:
            locked = conn.execute(
                "SELECT plan_id FROM plan_asset_locks WHERE asset=?", (asset,)
            ).fetchone()
            if locked and locked["plan_id"] != plan_id:
                raise ValueError(f"{asset} is already reserved by another approved funding plan")
        for asset in assets:
            conn.execute(
                "INSERT OR REPLACE INTO plan_asset_locks(asset, plan_id, expires_at) VALUES (?, ?, ?)",
                (asset, plan_id, plan["expires_at"]),
            )
        updated = conn.execute(
            """UPDATE funding_plans SET state='approved', approval_json=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND version=? AND state='awaiting_approval'""",
            (json.dumps(approval, sort_keys=True), plan_id, version),
        )
        if updated.rowcount != 1:
            raise ValueError("Plan changed while approval was being recorded")
    return get_plan(plan_id)


def _decimal(value, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Provider returned an invalid {label}") from exc


async def _preflight(plan: dict) -> dict:
    if not plan["steps"]:
        return {"source": "none", "details": []}
    current = await mcp_client.get_dust_convertible_assets("USDC")
    if not current.get("available"):
        raise ValueError("Current small-balance eligibility is unavailable")
    eligible = {str(item.get("asset", "")).upper(): item for item in current.get("details", [])}
    max_fee = Decimal(str(plan["request"].get("max_conversion_fee_pct", 2.5)))
    max_slippage = Decimal(str(plan["request"].get("max_slippage_pct", 1)))
    checked = []
    for step in plan["steps"]:
        approved = step["input"]
        asset = approved["asset"]
        item = eligible.get(asset)
        if item is None:
            raise ValueError(f"{asset} is no longer eligible for small-balance conversion")
        approved_quantity = _decimal(approved.get("quantity"), f"approved {asset} quantity")
        current_quantity = _decimal(item.get("amountFree"), f"current {asset} quantity")
        if current_quantity != approved_quantity:
            raise ValueError(f"{asset} balance changed; create and approve a fresh plan")
        gross = _decimal(item.get("gross_usdc"), f"{asset} gross proceeds")
        fee = _decimal(item.get("service_charge_usdc"), f"{asset} fee")
        net = _decimal(item.get("net_usdc"), f"{asset} net proceeds")
        if gross <= 0 or fee < 0 or net < 0:
            raise ValueError(f"Provider returned invalid conversion values for {asset}")
        if fee / gross * 100 > max_fee:
            raise ValueError(f"{asset} fee now exceeds the approved {max_fee}% limit")
        approved_net = _decimal(approved.get("net_usdc"), f"approved {asset} net proceeds")
        minimum_net = approved_net * (Decimal("1") - max_slippage / Decimal("100"))
        if net < minimum_net:
            raise ValueError(f"{asset} proceeds moved outside the approved {max_slippage}% bound")
        checked.append(
            {
                "asset": asset,
                "amount": str(current_quantity),
                "gross_usdc": str(gross),
                "service_charge_usdc": str(fee),
                "net_usdc": str(net),
            }
        )
    return {"source": current.get("source"), "details": checked}


def _persist_receipts(plan: dict, receipts: list[dict]) -> None:
    ordinals = {step["input"]["asset"]: step["ordinal"] for step in plan["steps"]}
    with transaction() as conn:
        for receipt in receipts:
            asset = str(receipt.get("from_asset", "")).upper()
            ordinal = ordinals.get(asset)
            if ordinal is None:
                continue
            conn.execute(
                """UPDATE plan_steps SET state='completed', result_json=?, provider_id=?, updated_at=CURRENT_TIMESTAMP
                   WHERE plan_id=? AND ordinal=?""",
                (
                    json.dumps(receipt, sort_keys=True),
                    receipt.get("provider_id"),
                    plan["id"],
                    ordinal,
                ),
            )


async def execute_plan(plan_id: str, version: int, operation_id: str | None = None) -> dict:
    plan = get_plan(plan_id)
    if plan is None:
        raise LookupError("Funding plan not found")
    if plan["version"] != version:
        raise ValueError("Plan version changed; review the current plan")
    if plan["state"] == "completed":
        return {**(plan.get("result") or {}), "duplicate": True}
    if plan["state"] != "approved":
        raise ValueError(f"Plan must be approved before execution; current state is {plan['state']}")
    if int(time.time()) >= plan["expires_at"]:
        _expire_plan(plan_id, "Plan expired before execution")
        raise ValueError("Plan expired; create and approve a fresh plan")
    if not is_mock() and plan["steps"]:
        raise ValueError("Live dust execution is not enabled until authenticated capability verification succeeds")

    selected = [step["input"]["asset"] for step in plan["steps"]]
    policies = get_asset_policies()
    blocked = [
        asset
        for asset in selected
        if policies.get(asset, {}).get("protected")
        or Decimal(policies.get(asset, {}).get("minimum_keep", "0")) > 0
    ]
    if blocked:
        _expire_plan(plan_id, f"Plan assets became protected: {', '.join(blocked)}")
        raise ValueError(f"Plan assets are now protected: {', '.join(blocked)}")

    try:
        preflight = await _preflight(plan)
    except ValueError as exc:
        _expire_plan(plan_id, str(exc))
        raise

    operation_id = operation_id or f"plan-{plan_id}"
    snapshot = {
        "plan_id": plan_id,
        "version": version,
        "selected_assets": selected,
        "approved_quantities": {
            step["input"]["asset"]: step["input"].get("quantity") for step in plan["steps"]
        },
    }
    existing = get_execution(operation_id)
    if existing:
        if existing.get("request") != snapshot:
            raise ValueError("operation_id was already used for a different plan")
        if existing.get("state") == "completed":
            return {**(existing.get("result") or {}), "duplicate": True}
        raise ValueError(f"Plan execution is {existing.get('state')}; reconcile before retrying")
    created, concurrent = claim_plan_execution(operation_id, plan_id, version, snapshot)
    if not created:
        if concurrent.get("request") != snapshot:
            raise ValueError("operation_id was already used for a different plan")
        if concurrent.get("state") == "completed":
            return {**(concurrent.get("result") or {}), "duplicate": True}
        raise ValueError(f"Plan execution is {concurrent.get('state')}; reconcile before retrying")

    try:
        conversion = await mcp_client.convert_dust_assets(selected, "USDC", dry_run=False)
    except Exception as exc:
        result = {
            "ok": False,
            "state": "needs_reconciliation",
            "error": str(exc),
            "preflight": preflight,
            "operation_id": operation_id,
        }
        finish_execution(operation_id, "needs_reconciliation", result)
        with transaction() as conn:
            conn.execute(
                "UPDATE funding_plans SET state='needs_reconciliation', result_json=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (json.dumps(result, sort_keys=True), plan_id),
            )
        return result
    if not conversion.get("ok"):
        result = {
            "ok": False,
            "state": "failed",
            "conversion": conversion,
            "preflight": preflight,
            "operation_id": operation_id,
        }
        finish_execution(operation_id, "failed", result)
        with transaction() as conn:
            conn.execute(
                "UPDATE funding_plans SET state='failed', result_json=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (json.dumps(result, sort_keys=True), plan_id),
            )
            _release_asset_locks(plan_id, conn)
        return result

    receipts = conversion.get("receipts", [])
    _persist_receipts(plan, receipts)
    max_fee = Decimal(str(plan["request"].get("max_conversion_fee_pct", 2.5)))
    for receipt in receipts:
        gross = _decimal(receipt.get("gross_usdc"), "actual gross proceeds")
        fee = _decimal(receipt.get("service_charge_usdc"), "actual conversion fee")
        if gross and fee / gross * 100 > max_fee:
            result = {
                "ok": False,
                "state": "partially_completed",
                "error": "Actual conversion fee exceeded the approved limit",
                "conversion": conversion,
                "preflight": preflight,
                "operation_id": operation_id,
            }
            finish_execution(operation_id, "partially_completed", result)
            with transaction() as conn:
                conn.execute(
                    "UPDATE funding_plans SET state='partially_completed', result_json=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (json.dumps(result, sort_keys=True), plan_id),
                )
                _release_asset_locks(plan_id, conn)
            return result

    free_usdc = Decimal(str(await mcp_client.get_spendable_balance("USDC")))
    obligation_id = plan["request"].get("obligation_id")
    other = reserved_usdc(exclude_id=obligation_id)
    reserve = Decimal(
        str(
            plan["request"].get("minimum_reserve")
            if plan["request"].get("minimum_reserve") is not None
            else get_config().get("minimum_reserve_usdc", 50)
        )
    )
    required = Decimal(str(plan["request"]["amount"])) + Decimal(
        str(plan["request"].get("payment_fee", 0))
    )
    ready = free_usdc - other - reserve >= required
    state = "completed" if ready else "partially_completed"
    result = {
        "ok": ready,
        "state": state,
        "funding_status": "funds_prepared" if ready else "still_underfunded",
        "settlement_status": "not_executed",
        "free_usdc": str(free_usdc),
        "required_usdc": str(required),
        "minimum_reserve_usdc": str(reserve),
        "other_obligations_usdc": str(other),
        "conversion": conversion,
        "preflight": preflight,
        "operation_id": operation_id,
        "obligation_id": obligation_id,
    }
    with transaction() as conn:
        conn.execute(
            "UPDATE funding_plans SET state=?, result_json=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (state, json.dumps(result, sort_keys=True), plan_id),
        )
        _release_asset_locks(plan_id, conn)
    if ready and obligation_id is not None:
        update_obligation_status(obligation_id, "ready")
    finish_execution(operation_id, state, result)
    log_activity(
        {
            "type": "funding_plan",
            "ok": ready,
            "plan_id": plan_id,
            "operation_id": operation_id,
            "obligation_id": obligation_id,
            "funding_status": result["funding_status"],
            "settlement_status": "not_executed",
            "net_received_usdc": conversion.get("net_received", "0"),
            "receipt_count": len(receipts),
            "mode": conversion.get("source"),
        }
    )
    return result
