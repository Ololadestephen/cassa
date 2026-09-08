from . import mcp_client
from .store import load

PRICE_SYMBOL = {"BTC": "BTCUSDC", "ETH": "ETHUSDC", "SOL": "SOLUSDC", "BNB": "BNBUSDC"}


def value_holdings(spot: dict, earn_usdc: float, prices: dict) -> dict:
    rows = []
    total = 0.0
    for asset, qty_raw in (spot or {}).items():
        try:
            qty = float(qty_raw)
        except (TypeError, ValueError):
            continue
        if asset == "USDC":
            value = qty
        else:
            node = prices.get(PRICE_SYMBOL.get(asset, f"{asset}USDC"), {})
            price = float(node.get("price", 0)) if isinstance(node, dict) else 0.0
            value = qty * price
        total += value
        rows.append({"asset": asset, "qty": qty, "usdc_value": round(value, 2)})
    if earn_usdc > 0:
        total += earn_usdc
        rows.append({"asset": "EARN-USDC", "qty": round(earn_usdc, 2), "usdc_value": round(earn_usdc, 2)})
    rows.sort(key=lambda row: row["usdc_value"], reverse=True)
    return {"total_usdc": round(total, 2), "rows": rows}


async def split_holdings(balances: dict) -> tuple:
    """Return (spot dict, earn_usdc float, earn detail dict) from a get_balances() payload."""
    if balances.get("mode") in {"live-exchange", "agent-os-readonly"}:
        spot = dict(balances.get("exchange", {}).get("balances", {}))
        earn = await mcp_client.earn_positions("USDC")
        return spot, float(earn.get("principal", 0)), earn
    paper = balances.get("paper", {})
    spot = dict(paper.get("spot", {}))
    earn = await mcp_client.earn_positions("USDC")
    return spot, float(earn.get("principal", 0)), earn


async def build_digest() -> dict:
    balances = await mcp_client.get_balances()
    prices = balances.get("prices", {})
    spot, earn_usdc, earn = await split_holdings(balances)
    missing = tuple(
        f"{asset}USDC"
        for asset in spot
        if asset != "USDC" and f"{asset}USDC" not in prices
    )
    if missing:
        prices.update(await mcp_client.get_prices(missing))
    valuation = value_holdings(spot, earn_usdc, prices)
    compact_prices = {
        key: value.get("price")
        for key, value in prices.items()
        if key.endswith("USDC") and isinstance(value, dict) and "price" in value
    }
    return {
        "mode": balances.get("mode"),
        "source": balances.get("source"),
        "headline": f"Cassa manages ${valuation['total_usdc']:,.2f} ({balances.get('mode')})",
        "valuation": valuation,
        "earn": earn,
        "prices": compact_prices,
        "recent_activity": load("activity", [])[:10],
    }
