"""Binance access layer for Cassa — confirmed tools only.

Confirmed in code (account access still depends on credentials and permissions):
- market data: get_prices, get_orderbook (public REST, no keys)
- balances: get_exchange_balances (signed REST, needs keys in live mode)
- positions: get_futures_positions (signed REST, needs keys in live mode)
- spot: place_spot_order (signed REST in live mode; paper ledger in mock mode)
- internal transfer: internal_transfer (signed REST in live mode; paper ledger in mock mode)

Simple Earn and signed dust discovery are implemented as provider adapters;
live account capability remains unverified. x402 stays gated elsewhere.
"""
import hashlib
import hmac
import os
import time
import urllib.parse

import httpx

from .store import get_earn_ledger, get_paper, is_mock, save

PUBLIC_BASES = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
]
API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
PRIVATE_BASE = "https://testnet.binance.vision" if TESTNET else "https://api.binance.com"
MCP_URL = "https://agent.binance.com/mcp/agentic"

ASSET_OF = {"BTCUSDC": "BTC", "ETHUSDC": "ETH", "SOLUSDC": "SOL", "BNBUSDC": "BNB"}


def keys_configured() -> bool:
    return bool(os.getenv("BINANCE_API_KEY", "") and os.getenv("BINANCE_API_SECRET", ""))


def _sign(params: dict) -> dict:
    secret = os.getenv("BINANCE_API_SECRET", "")
    signed = dict(params)
    signed["timestamp"] = int(time.time() * 1000)
    query = urllib.parse.urlencode(signed)
    signed["signature"] = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    return signed


async def _public_get(path: str, params: dict | None = None) -> tuple:
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=15) as client:
        for base in PUBLIC_BASES:
            try:
                response = await client.get(base + path, params=params or {})
                response.raise_for_status()
                return response.json(), base
            except Exception as exc:
                last_error = exc
                continue
    raise RuntimeError(f"Binance public hosts unreachable: {last_error}")


async def _signed_get(path: str, params: dict | None = None) -> dict:
    if not keys_configured():
        raise RuntimeError("BINANCE_API_KEY and BINANCE_API_SECRET are required for live exchange reads")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            PRIVATE_BASE + path,
            params=_sign(params or {}),
            headers={"X-MBX-APIKEY": os.getenv("BINANCE_API_KEY", "")},
        )
        response.raise_for_status()
        return response.json()


async def _signed_post(path: str, params: dict | None = None) -> dict:
    if not keys_configured():
        raise RuntimeError("BINANCE_API_KEY and BINANCE_API_SECRET are required for live exchange writes")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            PRIVATE_BASE + path,
            params=_sign(params or {}),
            headers={"X-MBX-APIKEY": os.getenv("BINANCE_API_KEY", "")},
        )
        response.raise_for_status()
        return response.json()


async def get_prices(symbols: tuple = ("BTCUSDC", "ETHUSDC", "SOLUSDC", "BNBUSDC")) -> dict:
    out: dict = {"source": "live-public"}
    quoted = ",".join(f'"{symbol}"' for symbol in symbols)
    try:
        tickers, base = await _public_get("/api/v3/ticker/24hr", {"symbols": f"[{quoted}]"})
        out["base"] = base
        for ticker in tickers:
            out[ticker["symbol"]] = {
                "price": float(ticker["lastPrice"]),
                "change_24h_pct": float(ticker["priceChangePercent"]),
                "high_24h": float(ticker["highPrice"]),
                "low_24h": float(ticker["lowPrice"]),
                "volume_24h": float(ticker["volume"]),
                "quote_volume_24h": float(ticker["quoteVolume"]),
            }
    except Exception:
        for symbol in symbols:
            try:
                tick, base = await _public_get("/api/v3/ticker/price", {"symbol": symbol})
                out[symbol] = {"price": float(tick["price"])}
                out["base"] = base
            except Exception as exc:
                out[symbol] = {"error": str(exc)}
    out["fetched_at"] = int(time.time())
    return out


async def get_orderbook(symbol: str, limit: int = 10) -> dict:
    book, base = await _public_get("/api/v3/depth", {"symbol": symbol, "limit": limit})
    bids = [(float(price), float(qty)) for price, qty in book["bids"]]
    asks = [(float(price), float(qty)) for price, qty in book["asks"]]
    mid = (bids[0][0] + asks[0][0]) / 2 if bids and asks else 0.0
    spread_bps = round((asks[0][0] - bids[0][0]) / mid * 10000, 2) if mid else 0.0
    return {
        "symbol": symbol,
        "base": base,
        "source": "live-public",
        "mid": mid,
        "spread_bps": spread_bps,
        "best_bid": bids[0] if bids else None,
        "best_ask": asks[0] if asks else None,
        "bids": bids[:limit],
        "asks": asks[:limit],
    }


async def get_dust_convertible_assets(
    target_asset: str = "USDC", account_type: str = "SPOT", prices: dict | None = None
) -> dict:
    """Discover provider-eligible small balances without converting them."""
    from decimal import Decimal, InvalidOperation

    from .store import get_config

    target_asset = target_asset.upper()
    if is_mock():
        paper = get_paper()
        spot = paper.get("spot", {})
        symbols = tuple(f"{asset.upper()}{target_asset}" for asset in spot if asset.upper() != target_asset)
        prices = prices or await get_prices(symbols)
        threshold = Decimal(str(get_config().get("dust_under_usdc", 5)))
        fee_rate = Decimal("0.02")
        details = []
        for asset, quantity_raw in spot.items():
            asset = asset.upper()
            if asset == target_asset:
                continue
            try:
                quantity = Decimal(str(quantity_raw))
                node = prices.get(f"{asset}{target_asset}", {})
                price = Decimal(str(node["price"]))
            except (InvalidOperation, KeyError, TypeError, ValueError):
                continue
            gross = quantity * price
            if quantity <= 0 or gross > threshold:
                continue
            charge = gross * fee_rate
            details.append(
                {
                    "asset": asset,
                    "amountFree": str(quantity),
                    "gross_usdc": str(gross),
                    "service_charge_usdc": str(charge),
                    "net_usdc": str(gross - charge),
                }
            )
        return {
            "available": True,
            "source": "paper-fixture",
            "target_asset": target_asset,
            "fee_rate": str(fee_rate),
            "details": details,
        }
    raw = await _signed_post(
        "/sapi/v1/asset/dust-convert/query-convertible-assets",
        {"targetAsset": target_asset, "accountType": account_type},
    )
    details = []
    for item in raw.get("details", []):
        details.append(
            {
                **item,
                "asset": str(item.get("asset", "")).upper(),
                "net_usdc": item.get("toTargetAssetOffExchange") if target_asset == "USDC" else None,
            }
        )
    return {
        "available": True,
        "source": "live-wallet-api",
        "target_asset": target_asset,
        "fee_rate": raw.get("dribbletPercentage"),
        "details": details,
        "raw_totals": {
            "quota": raw.get("totalTransferQuotaAssetAmount"),
            "target": raw.get("totalTransferTargetAssetAmount"),
        },
    }


async def convert_dust_assets(assets: list[str], target_asset: str = "USDC", dry_run: bool = True) -> dict:
    """Execute an exact selected set in paper mode; live execution remains gated."""
    from decimal import Decimal
    from uuid import uuid4

    selected = sorted({str(asset).upper() for asset in assets if str(asset).strip()})
    if not selected:
        return {"ok": True, "source": "paper-fixture" if is_mock() else "live-wallet-api", "receipts": [], "net_received": "0"}
    if not is_mock():
        return {
            "ok": False,
            "reason": "LIVE_DUST_EXECUTION_NOT_ENABLED",
            "error": "Authenticated dust execution has not been verified for this account.",
        }
    eligibility = await get_dust_convertible_assets(target_asset)
    eligible = {item["asset"]: item for item in eligibility.get("details", [])}
    missing = [asset for asset in selected if asset not in eligible]
    if missing:
        return {"ok": False, "reason": "ASSET_NO_LONGER_ELIGIBLE", "assets": missing}
    receipts = []
    total_net = Decimal("0")
    for asset in selected:
        item = eligible[asset]
        receipts.append(
            {
                "provider_id": f"paper-dust-{uuid4()}",
                "from_asset": asset,
                "amount": item["amountFree"],
                "gross_usdc": item["gross_usdc"],
                "service_charge_usdc": item["service_charge_usdc"],
                "net_usdc": item["net_usdc"],
            }
        )
        total_net += Decimal(item["net_usdc"])
    if dry_run:
        return {"ok": True, "dry_run": True, "source": "paper-fixture", "receipts": receipts, "net_received": str(total_net)}
    paper = get_paper()
    spot = paper.setdefault("spot", {})
    for receipt in receipts:
        asset = receipt["from_asset"]
        expected = Decimal(receipt["amount"])
        current = Decimal(str(spot.get(asset, 0)))
        if current != expected:
            return {"ok": False, "reason": "BALANCE_CHANGED", "asset": asset}
    for receipt in receipts:
        spot[receipt["from_asset"]] = "0"
    spot[target_asset] = str(Decimal(str(spot.get(target_asset, 0))) + total_net)
    save("paper", paper)
    return {"ok": True, "dry_run": False, "source": "paper", "receipts": receipts, "net_received": str(total_net)}


async def get_exchange_balances() -> dict:
    account = await _signed_get("/api/v3/account")
    balances = {
        row["asset"]: float(row["free"]) + float(row["locked"])
        for row in account.get("balances", [])
        if float(row["free"]) + float(row["locked"]) > 0
    }
    return {
        "source": "live-exchange",
        "testnet": TESTNET,
        "balances": balances,
        "can_trade": account.get("canTrade"),
        "account_type": account.get("accountType"),
    }


async def get_futures_positions() -> dict:
    risks = await _signed_get("/fapi/v2/positionRisk")
    open_positions = [row for row in risks if float(row.get("positionAmt", 0)) != 0]
    return {"source": "live-exchange", "testnet": TESTNET, "open": open_positions, "count": len(open_positions)}


async def get_balances() -> dict:
    prices = await get_prices()
    if is_mock():
        return {"mode": "paper", "source": "paper", "paper": get_paper(), "prices": prices}
    balances = await get_exchange_balances()
    positions = await get_futures_positions()
    return {
        "mode": "live-exchange",
        "source": "live-exchange",
        "testnet": TESTNET,
        "exchange": balances,
        "positions": positions,
        "prices": prices,
    }


async def get_spendable_balance(asset: str) -> float:
    asset = asset.upper()
    if is_mock():
        return float(get_paper().get("spot", {}).get(asset, 0))
    balances = await get_exchange_balances()
    return float(balances.get("balances", {}).get(asset, 0))


async def quote_convert_from_market(from_asset: str, to_asset: str, amount: float) -> dict:
    """Quote-only conversion estimate from live public prices. Does not execute."""
    symbols = tuple({f"{from_asset}USDC", f"{to_asset}USDC"} - {"USDCUSDC"})
    if not symbols:
        return {"source": "live-public", "from": from_asset, "to": to_asset, "amount": amount, "est_receive": amount}
    prices = await get_prices(symbols or ("BTCUSDC",))
    if from_asset == "USDC":
        rate = prices[to_asset + "USDC"]["price"]
        return {
            "source": "live-public",
            "from": from_asset,
            "to": to_asset,
            "amount": amount,
            "est_receive": round(amount / rate, 6),
            "ref_price": rate,
            "execution": "not-executed",
        }
    if to_asset == "USDC":
        rate = prices[from_asset + "USDC"]["price"]
        return {
            "source": "live-public",
            "from": from_asset,
            "to": to_asset,
            "amount": amount,
            "est_receive": round(amount * rate, 2),
            "ref_price": rate,
            "execution": "not-executed",
        }
    from_rate = prices[from_asset + "USDC"]["price"]
    to_rate = prices[to_asset + "USDC"]["price"]
    return {
        "source": "live-public",
        "from": from_asset,
        "to": to_asset,
        "amount": amount,
        "est_receive": round(amount * from_rate / to_rate, 6),
        "execution": "not-executed",
    }


async def place_spot_order(symbol: str, side: str, quote_usdc: float, dry_run: bool) -> dict:
    if side not in ("BUY", "SELL"):
        return {"source": "rejected", "ok": False, "error": "side must be BUY or SELL"}
    if quote_usdc <= 0:
        return {"source": "rejected", "ok": False, "error": "quote_usdc must be > 0"}
    prices = await get_prices((symbol,))
    node = prices.get(symbol, {})
    if not isinstance(node, dict) or "price" not in node:
        return {"source": prices.get("source", "live-public"), "ok": False, "error": f"No live price for {symbol}"}
    price = float(node["price"])
    qty = quote_usdc / price
    if dry_run:
        return {
            "source": "dry-run",
            "ok": True,
            "symbol": symbol,
            "side": side,
            "quote_usdc": quote_usdc,
            "est_price": price,
            "est_qty": round(qty, 6),
            "would_execute_on": "paper" if is_mock() else "live-exchange",
        }
    if is_mock():
        paper = get_paper()
        spot = paper["spot"]
        asset = ASSET_OF.get(symbol, symbol.replace("USDC", ""))
        if side == "BUY":
            if float(spot.get("USDC", 0)) < quote_usdc:
                return {"source": "paper", "ok": False, "error": "Insufficient paper USDC balance"}
            spot["USDC"] = round(float(spot["USDC"]) - quote_usdc, 2)
            spot[asset] = round(float(spot.get(asset, 0)) + qty, 6)
        else:
            if float(spot.get(asset, 0)) < qty:
                return {"source": "paper", "ok": False, "error": f"Insufficient paper {asset} balance"}
            spot[asset] = round(float(spot[asset]) - qty, 6)
            spot["USDC"] = round(float(spot.get("USDC", 0)) + quote_usdc, 2)
        save("paper", paper)
        return {
            "source": "paper",
            "ok": True,
            "symbol": symbol,
            "side": side,
            "fill_price": price,
            "fill_qty": round(qty, 6),
            "quote_usdc": quote_usdc,
        }
    fill = await _signed_post(
        "/api/v3/order", {"symbol": symbol, "side": side, "type": "MARKET", "quoteOrderQty": quote_usdc}
    )
    fill["source"] = "live-exchange"
    fill["ok"] = True
    return fill


async def internal_transfer(asset: str, amount: float, destination: str, dry_run: bool) -> dict:
    if amount <= 0:
        return {"source": "rejected", "ok": False, "error": "amount must be > 0"}
    if dry_run:
        return {
            "source": "dry-run",
            "ok": True,
            "rail": "internal-transfer",
            "asset": asset,
            "amount": amount,
            "destination": destination,
            "would_execute_on": "paper" if is_mock() else "live-exchange",
        }
    if is_mock():
        paper = get_paper()
        spot = paper["spot"]
        if float(spot.get(asset, 0)) < amount:
            return {"source": "paper", "ok": False, "error": f"Insufficient paper {asset} balance"}
        spot[asset] = round(float(spot[asset]) - amount, 2)
        save("paper", paper)
        return {
            "source": "paper",
            "ok": True,
            "rail": "internal-transfer",
            "asset": asset,
            "amount": amount,
            "destination": destination,
        }
    moved = await _signed_post(
        "/sapi/v1/sub-account/universalTransfer",
        {
            "fromAccountType": "SPOT",
            "toAccountType": "SPOT",
            "toAccount": destination,
            "asset": asset,
            "amount": amount,
        },
    )
    moved["source"] = "live-exchange"
    moved["ok"] = True
    moved["rail"] = "internal-transfer"
    return moved


def _accrue_paper_earn(paper: dict, now: int) -> dict:
    import time as _time

    now = now or int(_time.time())
    earn = get_earn_ledger(paper)
    for asset, row in earn.items():
        try:
            principal = float(row.get("principal", 0))
            apr = float(row.get("apr_pct", 0))
            updated = int(row.get("updated_at", now))
        except (TypeError, ValueError):
            continue
        days = max(0.0, (now - updated) / 86400)
        if principal > 0 and apr > 0 and days > 0:
            interest = principal * apr / 100 * days / 365
            row["principal"] = round(principal + interest, 6)
            row["accrued_total"] = round(float(row.get("accrued_total", 0)) + interest, 6)
        row["updated_at"] = now
    return earn


async def _resolve_flexible_product_id(asset: str) -> tuple:
    products = await _signed_get("/sapi/v1/lending/daily/product/list", {"asset": asset, "status": "PURCHASING"})
    rows = products if isinstance(products, list) else products.get("rows", [])
    for row in rows:
        if str(row.get("asset", "")).upper() == asset.upper():
            return str(row["productId"]), row
    raise RuntimeError(f"No purchasable Simple Earn Flexible product for {asset}")


async def earn_positions(asset: str = "USDC") -> dict:
    import time as _time

    asset = asset.upper()
    if is_mock():
        paper = get_paper()
        earn = _accrue_paper_earn(paper, int(_time.time()))
        save("paper", paper)
        row = earn.get(asset, {"principal": 0.0, "accrued_total": 0.0, "apr_pct": 4.2})
        return {
            "source": "paper",
            "asset": asset,
            "principal": round(float(row.get("principal", 0)), 6),
            "accrued_total": round(float(row.get("accrued_total", 0)), 6),
            "apr_pct": float(row.get("apr_pct", 4.2)),
            "apr_note": "paper snapshot rate, compounds on every read",
        }
    product_id, product = await _resolve_flexible_product_id(asset)
    raw = await _signed_get("/sapi/v1/lending/daily/token/position", {"asset": asset})
    rows = raw if isinstance(raw, list) else raw.get("rows", [])
    total = sum(float(row.get("totalAmount", 0)) for row in rows)
    return {
        "source": "live-exchange",
        "asset": asset,
        "product_id": product_id,
        "principal": round(total, 6),
        "apr_pct": float(product.get("latestAnnualPercentageRate", 0)),
        "positions": rows,
    }


async def earn_subscribe(asset: str, amount: float, dry_run: bool) -> dict:
    import time as _time

    asset = asset.upper()
    if amount <= 0:
        return {"source": "rejected", "ok": False, "error": "amount must be > 0"}
    if dry_run:
        return {
            "source": "dry-run",
            "ok": True,
            "asset": asset,
            "amount": amount,
            "product": "Simple Earn Flexible",
            "would_execute_on": "paper" if is_mock() else "live-exchange",
        }
    if is_mock():
        paper = get_paper()
        earn = _accrue_paper_earn(paper, int(_time.time()))
        spot = paper["spot"]
        if float(spot.get(asset, 0)) < amount:
            return {"source": "paper", "ok": False, "error": f"Insufficient paper {asset} balance"}
        spot[asset] = round(float(spot[asset]) - amount, 2)
        row = earn.get(asset)
        if row is None:
            row = {"principal": 0.0, "accrued_total": 0.0, "apr_pct": 4.2, "updated_at": int(_time.time())}
            earn[asset] = row
        row["principal"] = round(float(row["principal"]) + amount, 6)
        save("paper", paper)
        return {"source": "paper", "ok": True, "asset": asset, "amount": amount, "principal": row["principal"]}
    product_id, _ = await _resolve_flexible_product_id(asset)
    bought = await _signed_post("/sapi/v1/lending/daily/purchase", {"productId": product_id, "amount": amount})
    bought["source"] = "live-exchange"
    bought["ok"] = True
    return bought


async def earn_redeem(asset: str, amount: float, dry_run: bool) -> dict:
    import time as _time

    asset = asset.upper()
    if amount <= 0:
        return {"source": "rejected", "ok": False, "error": "amount must be > 0"}
    if dry_run:
        positions = await earn_positions(asset)
        return {
            "source": "dry-run",
            "ok": True,
            "asset": asset,
            "amount": amount,
            "principal_available": positions.get("principal", 0),
            "would_execute_on": "paper" if is_mock() else "live-exchange",
        }
    if is_mock():
        paper = get_paper()
        earn = _accrue_paper_earn(paper, int(_time.time()))
        row = earn.get(asset, {})
        principal = float(row.get("principal", 0))
        if principal < amount:
            return {"source": "paper", "ok": False, "error": f"Only {principal:g} {asset} in paper Earn"}
        row["principal"] = round(principal - amount, 6)
        paper["spot"][asset] = round(float(paper["spot"].get(asset, 0)) + amount, 2)
        save("paper", paper)
        return {"source": "paper", "ok": True, "asset": asset, "amount": amount, "principal_left": row["principal"]}
    product_id, _ = await _resolve_flexible_product_id(asset)
    freed = await _signed_post("/sapi/v1/lending/daily/redeem", {"productId": product_id, "amount": amount})
    freed["source"] = "live-exchange"
    freed["ok"] = True
    return freed
