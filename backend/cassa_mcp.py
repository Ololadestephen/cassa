"""Local MCP tools used alongside Binance Agent OS in a supported host."""
from typing import Any

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from .providers.agent_host import agent_host_status, record_agentic_snapshot
from .services.affordability import assess_affordability


class AgentBalance(BaseModel):
    asset: str = Field(min_length=1, max_length=20)
    free: str
    locked: str = "0"


class ConvertRouteObservation(BaseModel):
    from_asset: str = Field(min_length=1, max_length=20)
    to_asset: str = Field(default="USDC", min_length=1, max_length=20)
    supported: bool
    minimum_from_amount: str | None = None


server = MCPServer(
    "cassa",
    instructions=(
        "Cassa is a deterministic cash-readiness layer. Use Binance Agent OS for provider reads. "
        "Call sync_agentic_spot_snapshot only with exact results from a fresh Binance MCP account read. "
        "Never invent balances, pass credentials, or treat a route/minimum observation as an executed quote."
    ),
)


@server.tool(
    description=(
        "Persist a read-only Agentic Spot observation after a fresh Binance Agent OS account read. "
        "Pass exact decimal strings. This tool cannot trade, convert, or transfer."
    )
)
def sync_agentic_spot_snapshot(
    balances: list[AgentBalance],
    convert_routes: list[ConvertRouteObservation] | None = None,
    account_type: str = "SPOT",
    can_trade: bool | None = None,
) -> dict[str, Any]:
    snapshot = record_agentic_snapshot(
        balances=[row.model_dump() for row in balances],
        convert_routes=[row.model_dump() for row in (convert_routes or [])],
        account_type=account_type,
        can_trade=can_trade,
    )
    return {
        "ok": True,
        "source": snapshot["source"],
        "captured_at": snapshot["captured_at"],
        "asset_count": len(snapshot["balances"]),
        "route_count": len(snapshot["convert_routes"]),
        "writes_enabled": False,
    }


@server.tool(description="Return Cassa's current supported-host sync status. This is read-only.")
def get_agent_sync_status() -> dict[str, Any]:
    return agent_host_status()


@server.tool(
    description=(
        "Run Cassa's deterministic Can I afford this? calculation against the latest synced snapshot. "
        "This previews only and cannot grant approval or execute a financial action."
    )
)
async def can_i_afford(
    amount_usdc: str,
    minimum_reserve_usdc: str = "0",
    payment_fee_usdc: str = "0",
    recipient: str | None = None,
    allowed_assets: list[str] | None = None,
) -> dict[str, Any]:
    return await assess_affordability(
        amount=amount_usdc,
        minimum_reserve=minimum_reserve_usdc,
        payment_fee=payment_fee_usdc,
        recipient=recipient,
        allowed_assets=allowed_assets,
    )


if __name__ == "__main__":
    server.run()
