from . import mcp_client
from .store import get_config

SYMBOL_MAP = {"BTC": "BTCUSDC", "ETH": "ETHUSDC", "SOL": "SOLUSDC", "BNB": "BNBUSDC"}


def _spot_of(balances: dict) -> dict:
    if balances.get("mode") in {"live-exchange", "agent-os-readonly"}:
        return dict(balances.get("exchange", {}).get("balances", {}))
    return dict(balances.get("paper", {}).get("spot", {}))


async def run_sweep(
    dca_total_usdc: float | None = None,
    dca_split: dict | None = None,
    sweep_idle_over_usdc: float | None = None,
    dust_under_usdc: float | None = None,
    dry_run: bool = True,
) -> dict:
    cfg = get_config()
    total = cfg["dca_total_usdc"] if dca_total_usdc is None else dca_total_usdc
    split = cfg["dca_split"] if dca_split is None else dca_split
    idle_over = cfg["sweep_idle_over_usdc"] if sweep_idle_over_usdc is None else sweep_idle_over_usdc
    dust_under = cfg["dust_under_usdc"] if dust_under_usdc is None else dust_under_usdc
    if total <= 0:
        return {"ok": False, "error": "dca_total_usdc must be greater than 0"}
    weight_sum = sum(float(v) for v in split.values())
    if weight_sum <= 0 or any(float(v) < 0 for v in split.values()):
        return {"ok": False, "error": "dca_split weights must sum above 0"}
    split = {k: float(v) / weight_sum for k, v in split.items()}

    balances = await mcp_client.get_balances()
    prices = balances.get("prices") or await mcp_client.get_prices()
    spot = _spot_of(balances)

    fills = []
    for asset, weight in split.items():
        quote = round(total * weight, 2)
        symbol = SYMBOL_MAP.get(asset, f"{asset}USDC")
        result = await mcp_client.place_spot_order(symbol, "BUY", quote, dry_run)
        node = prices.get(symbol, {})
        price = float(node.get("price", 0)) if isinstance(node, dict) else 0.0
        fills.append(
            {
                "asset": asset,
                "symbol": symbol,
                "quote_usdc": quote,
                "price": price or None,
                "est_qty": round(quote / price, 6) if price else None,
                "result": result,
            }
        )

    dca_ok = all(item["result"].get("ok") for item in fills)
    if dry_run:
        spent = sum(item["quote_usdc"] for item in fills if item["result"].get("ok"))
        post_dca_idle = round(float(spot.get("USDC", 0)) - spent, 2)
    else:
        refreshed = await mcp_client.get_balances()
        post_dca_idle = round(float(_spot_of(refreshed).get("USDC", 0)), 2)
    reserve = float(cfg.get("minimum_reserve_usdc", 50))
    if dca_ok and post_dca_idle > float(idle_over):
        swept_amount = round(max(0.0, post_dca_idle - reserve), 2)
        earn_result = await mcp_client.earn_subscribe("USDC", swept_amount, dry_run)
        earn = {**earn_result, "swept": swept_amount if earn_result.get("ok") else 0.0}
    elif not dca_ok:
        earn = {"ok": False, "swept": 0.0, "reason": "skipped_after_dca_failure"}
    else:
        earn = {"ok": True, "swept": 0.0, "reason": f"idle ${post_dca_idle:.2f} at or below threshold ${float(idle_over):.2f}"}
    required_steps_ok = dca_ok and earn.get("ok", False)

    dust = []
    for asset, qty in spot.items():
        if asset == "USDC":
            continue
        try:
            amount = float(qty)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        symbol = SYMBOL_MAP.get(asset)
        node = prices.get(symbol, {}) if symbol else {}
        price = float(node.get("price", 0)) if isinstance(node, dict) else 0.0
        value = amount * price
        if price and value < float(dust_under):
            dust.append(
                {"asset": asset, "qty": amount, "est_usdc": round(value, 2), "action": "report-only"}
            )

    return {
        "ok": required_steps_ok,
        "status": "completed" if required_steps_ok else "partially_completed" if any(item["result"].get("ok") for item in fills) else "failed",
        "dry_run": dry_run,
        "mode": balances.get("mode"),
        "source": balances.get("source"),
        "idle_usdc_before": round(float(spot.get("USDC", 0)), 2),
        "idle_usdc_after_dca": post_dca_idle,
        "minimum_reserve_usdc": reserve,
        "dca_fills": fills,
        "earn": earn,
        "dust": dust,
        "prices_used": {
            symbol: (prices.get(symbol, {}).get("price") if isinstance(prices.get(symbol), dict) else None)
            for symbol in SYMBOL_MAP.values()
        },
    }
