import os
from uuid import uuid4
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from .agent import handle_chat
from .digest import build_digest, split_holdings, value_holdings
from .gated import x402_unavailable
from .execution import begin_execution, finish_execution, get_execution, list_executions, resolve_failed_execution
from .llm import parser_enabled
from .models import (
    AddressbookEntry,
    AffordabilityRequest,
    AssetPolicyUpdate,
    ChatRequest,
    ConfigUpdate,
    EarnRequest,
    FundingPlanRequest,
    ObligationCreate,
    ObligationStatusUpdate,
    PlanApprovalRequest,
    PlanExecutionRequest,
    ReconciliationRequest,
    PayRequest,
    SweepRequest,
    X402PayRequest,
)
from .pay import execute_pay, preview_pay
from .policy import looks_like_external_address, normalize_recipient_id
from .obligations import create_obligation, get_asset_policies, list_obligations, set_asset_policy, update_obligation_status
from .services.affordability import assess_affordability
from .services.portfolio import build_portfolio
from .plans import approve_plan, create_funding_plan, execute_plan, get_plan, list_plans
from .receipts import list_receipts, receipts_csv
from . import mcp_client
from .providers.agent_os import client_metadata_document, connection as agent_os_connection
from .store import PAPER_DEFAULT, get_addressbook, get_config, is_agent_os_readonly, is_mock, load, log_activity, provider_mode, save

app = FastAPI(title="Cassa — Idle Cash That Pays Its Team", version="0.3.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/api/health")
def health() -> dict:
    mode = provider_mode()
    return {
        "ok": True,
        "service": "cassa",
        "version": "0.3.0",
        "mock_mode": is_mock(),
        "provider_mode": mode,
        "writes_enabled": mode in {"paper", "binance-rest"},
        "parser": "groq" if parser_enabled() else "rules",
        "exchange_keys": mcp_client.keys_configured(),
        "testnet": mcp_client.TESTNET,
        "mcp": mcp_client.MCP_URL,
        "rails": {
            "market_data": "live-public",
            "spot": "agent-os-readonly" if is_agent_os_readonly() else "paper-or-configured-unverified",
            "internal_transfer": "disabled" if is_agent_os_readonly() else "paper-or-configured-unverified",
            "earn": "disabled" if is_agent_os_readonly() else "paper-or-configured-unverified",
            "x402": "SKILL_UNAVAILABLE",
        },
    }


@app.get("/api/providers/binance-agent-os/client-metadata.json")
def binance_agent_os_client_metadata() -> dict:
    """Public OAuth client metadata; contains no token or account identifier."""
    return client_metadata_document()


@app.get("/api/providers/binance-agent-os/status")
async def binance_agent_os_status() -> dict:
    return await agent_os_connection.status()


@app.post("/api/providers/binance-agent-os/connect")
async def connect_binance_agent_os() -> dict:
    result = await agent_os_connection.begin_connect()
    if result.get("state") == "error" and not result.get("authorization_url"):
        raise HTTPException(status_code=502, detail=result.get("error") or "Binance authorization failed")
    return result


@app.get("/api/providers/binance-agent-os/callback", response_class=HTMLResponse)
async def binance_agent_os_callback(
    code: str | None = None,
    state: str | None = None,
    iss: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    if error:
        raise HTTPException(status_code=400, detail="Binance authorization was declined")
    if not code:
        raise HTTPException(status_code=400, detail="Binance did not return an authorization code")
    try:
        await agent_os_connection.complete_callback(code, state, iss)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return HTMLResponse(
        """<!doctype html><html><head><title>Cassa connected</title></head>
        <body style="background:#0b0b09;color:#f1eddd;font-family:system-ui;padding:3rem">
        <h1>Binance authorization received.</h1><p>Cassa is verifying the read-only account connection.</p>
        <script>if(window.opener){window.opener.postMessage('cassa-binance-connected','*');window.close()}</script>
        </body></html>"""
    )


@app.get("/api/market")
async def market() -> dict:
    prices = await mcp_client.get_prices()
    markets = []
    for symbol in ("BTCUSDC", "ETHUSDC", "SOLUSDC", "BNBUSDC"):
        node = prices.get(symbol, {})
        if isinstance(node, dict) and "price" in node:
            markets.append({"symbol": symbol, "asset": symbol.replace("USDC", ""), **node})
    if not markets:
        raise HTTPException(status_code=502, detail="Live market feed unreachable")
    return {
        "markets": markets,
        "base": prices.get("base"),
        "fetched_at": prices.get("fetched_at"),
        "source": "live-public",
    }


@app.get("/api/orderbook")
async def orderbook(symbol: str = "BTCUSDC", limit: int = 10) -> dict:
    allowed = {"BTCUSDC", "ETHUSDC", "SOLUSDC", "BNBUSDC"}
    if symbol not in allowed:
        raise HTTPException(status_code=400, detail=f"symbol must be one of {sorted(allowed)}")
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return await mcp_client.get_orderbook(symbol, limit)


@app.get("/api/balance")
async def balance() -> dict:
    balances = await mcp_client.get_balances()
    _, _, earn = await split_holdings(balances)
    balances["earn"] = earn
    return balances


@app.get("/api/portfolio")
async def portfolio(include_dust: bool = True) -> dict:
    return await build_portfolio(include_dust=include_dust)


@app.get("/api/capabilities")
async def capabilities() -> dict:
    mode = provider_mode()
    live = mode != "paper"
    keys = mcp_client.keys_configured()
    agent_status = await agent_os_connection.status() if is_agent_os_readonly() else None
    if is_agent_os_readonly():
        balance_status = "available" if agent_status and agent_status.get("authorized") else "authorization_required"
        dust_status = "tool_unverified"
        earn_status = "not_enabled"
    else:
        balance_status = "available" if not live or keys else "credentials_required"
        dust_status = "paper_fixture" if not live else "configured_unverified" if keys else "credentials_required"
        earn_status = "paper_fixture" if not live else "configured_unverified" if keys else "credentials_required"
    return {
        "mode": mode,
        "account_scope": "agentic-sub-account" if is_agent_os_readonly() else "paper" if not live else "exchange-account",
        "capabilities": {
            "market_data": {"status": "available", "source": "binance-public"},
            "balances": {"status": balance_status, "source": "binance-agent-os-mcp" if is_agent_os_readonly() else None},
            "dust_discovery": {"status": dust_status, "target": "USDC"},
            "dust_execution": {
                "status": "paper_only" if not live else "not_enabled",
                "reason": "approved plans execute against the paper ledger; authenticated live execution remains gated",
            },
            "recipient_payment": {
                "status": "not_enabled" if is_agent_os_readonly() else "internal_transfer_only",
                "external_settlement": False,
            },
            "earn": {"status": earn_status},
        },
    }


@app.post("/api/affordability")
async def affordability(request: AffordabilityRequest) -> dict:
    try:
        return await assess_affordability(
            request.amount,
            request.payment_fee,
            request.minimum_reserve,
            request.obligation_id,
            request.recipient,
            request.allowed_assets,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/obligations")
def obligations(active_only: bool = False) -> list:
    return list_obligations(active_only=active_only)


@app.post("/api/obligations")
def add_obligation(request: ObligationCreate) -> dict:
    try:
        return create_obligation(request.amount, request.asset, request.due_date, request.recipient, request.memo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/obligations/{obligation_id}")
def set_obligation_status(obligation_id: int, request: ObligationStatusUpdate) -> dict:
    try:
        result = update_obligation_status(obligation_id, request.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return result


@app.get("/api/asset-policies")
def asset_policies() -> dict:
    return get_asset_policies()


@app.put("/api/asset-policies/{asset}")
def update_asset_policy(asset: str, request: AssetPolicyUpdate) -> dict:
    try:
        return set_asset_policy(asset, request.protected, request.minimum_keep)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/plans")
def funding_plans(limit: int = 20) -> list:
    return list_plans(max(1, min(limit, 100)))


@app.post("/api/plans")
async def add_funding_plan(request: FundingPlanRequest) -> dict:
    try:
        return await create_funding_plan(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/plans/{plan_id}")
def funding_plan(plan_id: str) -> dict:
    result = get_plan(plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Funding plan not found")
    return result


@app.post("/api/plans/{plan_id}/approve")
def confirm_funding_plan(plan_id: str, request: PlanApprovalRequest) -> dict:
    try:
        return approve_plan(plan_id, request.version, request.confirmed)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/plans/{plan_id}/execute")
async def run_funding_plan(plan_id: str, request: PlanExecutionRequest) -> dict:
    try:
        return await execute_plan(plan_id, request.version, request.operation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/sweep")
async def sweep(request: SweepRequest) -> dict:
    from .sweep import run_sweep

    if not request.dry_run and not request.confirmed:
        raise HTTPException(status_code=409, detail="Confirm this exact sweep before execution")
    operation_id = request.operation_id or str(uuid4())
    snapshot = request.model_dump(exclude={"confirmed", "operation_id"})
    if not request.dry_run:
        existing = get_execution(operation_id)
        if existing:
            if existing.get("request") != snapshot:
                raise HTTPException(status_code=409, detail="operation_id was already used for a different sweep")
            if existing.get("state") == "completed":
                return {**(existing.get("result") or {}), "duplicate": True}
            raise HTTPException(status_code=409, detail=f"Sweep operation is {existing.get('state')}; reconcile it before retrying")
        created, existing = begin_execution(operation_id, "sweep", snapshot)
        if not created:
            raise HTTPException(status_code=409, detail=f"Sweep operation is {existing.get('state')}; reconcile it before retrying")
    try:
        result = await run_sweep(
            request.dca_total_usdc,
            request.dca_split,
            request.sweep_idle_over_usdc,
            request.dust_under_usdc,
            request.dry_run,
        )
    except Exception as exc:
        if not request.dry_run:
            finish_execution(operation_id, "needs_reconciliation", {"ok": False, "error": str(exc), "operation_id": operation_id})
        raise
    result["operation_id"] = operation_id
    if not request.dry_run:
        finish_execution(operation_id, result.get("status", "failed"), result)
    if not result.get("ok") and result.get("status") in (None, "failed"):
        raise HTTPException(status_code=400, detail=result.get("error", "Sweep rejected"))
    if not request.dry_run and result.get("status") == "completed":
        log_activity(
            {
                "type": "sweep",
                "day": datetime.now(UTC).strftime("%Y-%m-%d"),
                "ok": True,
                "summary": f"DCA ${request.dca_total_usdc:g} split {request.dca_split}",
                "mode": result["mode"],
            }
        )
    return result


@app.post("/api/pay/preview")
async def pay_preview(request: PayRequest) -> dict:
    return await preview_pay(request.to, request.amount, request.asset, request.memo, request.obligation_id)


@app.post("/api/pay")
async def pay(request: PayRequest) -> dict:
    return await execute_pay(
        request.to, request.amount, request.asset, request.memo, request.dry_run, request.confirmed,
        request.obligation_id, request.operation_id
    )


@app.post("/api/earn/subscribe")
async def earn_subscribe(request: EarnRequest) -> dict:
    if not request.dry_run and not request.confirmed:
        raise HTTPException(status_code=409, detail="Confirm this exact Earn subscription before execution")
    return await mcp_client.earn_subscribe(request.asset.upper(), request.amount, request.dry_run)


@app.get("/api/earn/positions")
async def earn_positions(asset: str = "USDC") -> dict:
    if asset.upper() != "USDC":
        raise HTTPException(status_code=400, detail="Only USDC Earn is tracked in this release")
    return await mcp_client.earn_positions("USDC")


@app.post("/api/earn/redeem")
async def earn_redeem(request: EarnRequest) -> dict:
    if not request.dry_run and not request.confirmed:
        raise HTTPException(status_code=409, detail="Confirm this exact Earn redemption before execution")
    return await mcp_client.earn_redeem(request.asset.upper(), request.amount, request.dry_run)


@app.post("/api/x402/preview")
async def x402_preview(request: X402PayRequest) -> dict:
    return x402_unavailable(request.amount, request.asset.upper(), request.memo, record=False)


@app.post("/api/x402/pay")
async def x402_pay(request: X402PayRequest) -> dict:
    return x402_unavailable(request.amount, request.asset.upper(), request.memo)


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    return await handle_chat(request.message, request.dry_run)


@app.get("/api/digest")
async def digest() -> dict:
    return await build_digest()


@app.get("/api/activity")
def activity() -> list:
    return load("activity", [])


@app.get("/api/executions/{operation_id}")
def execution(operation_id: str) -> dict:
    result = get_execution(operation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return result


@app.get("/api/reconciliations")
def reconciliations(limit: int = 100) -> list:
    return list_executions("needs_reconciliation", max(1, min(limit, 500)))


@app.post("/api/reconciliations/{operation_id}/resolve-failed")
def resolve_reconciliation(operation_id: str, request: ReconciliationRequest) -> dict:
    try:
        return resolve_failed_execution(operation_id, request.evidence, request.confirmed)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/receipts")
def receipts(limit: int = 100) -> list:
    return list_receipts(max(1, min(limit, 1000)))


@app.get("/api/receipts/export.csv")
def export_receipts() -> Response:
    return Response(
        receipts_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="cassa-receipts.csv"'},
    )


@app.get("/api/config")
def get_cfg() -> dict:
    return {
        "config": get_config(),
        "addressbook": get_addressbook(),
        "mock_mode": is_mock(),
        "exchange_keys": mcp_client.keys_configured(),
    }


@app.post("/api/config")
def update_cfg(request: ConfigUpdate) -> dict:
    cfg = get_config()
    update = request.model_dump(exclude_none=True)
    if "max_x402_per_day_usdc" in update:
        raise HTTPException(status_code=400, detail="max_x402_per_day_usdc is fixed at $20 and cannot change")
    if "dca_split" in update:
        split = update["dca_split"] or {}
        if not split or sum(float(v) for v in split.values()) <= 0:
            raise HTTPException(status_code=400, detail="dca_split weights must sum above 0")
        cfg["dca_split"] = {key: float(value) for key, value in split.items()}
        del update["dca_split"]
    for key, value in update.items():
        if key in cfg:
            cfg[key] = value
    save("config", cfg)
    return {"ok": True, "config": get_config()}


@app.post("/api/addressbook")
def add_recipient(entry: AddressbookEntry) -> dict:
    recipient_id = normalize_recipient_id(entry.id)
    if not recipient_id:
        raise HTTPException(status_code=400, detail="id is required")
    if looks_like_external_address(entry.email_or_uid) or looks_like_external_address(recipient_id):
        raise HTTPException(status_code=400, detail="External addresses are disabled. Internal sub-account references only.")
    book = get_addressbook()
    book[recipient_id] = {
        "label": entry.label,
        "asset": entry.asset.upper(),
        "email_or_uid": entry.email_or_uid,
        "rail": "internal-transfer",
    }
    save("addressbook", book)
    return {"ok": True, "addressbook": book}


@app.post("/api/paper/reset")
def paper_reset() -> dict:
    if not is_mock():
        raise HTTPException(status_code=403, detail="Paper reset is available only when MOCK_MODE=true")
    import time as _time

    save("paper", {
        "spot": dict(PAPER_DEFAULT["spot"]),
        "earn": {
            asset: {**position, "updated_at": int(_time.time())}
            for asset, position in PAPER_DEFAULT["earn"].items()
        },
    })
    save("activity", [])
    save("_seq", {"n": 0})
    return {"ok": True, "mode": "paper"}
