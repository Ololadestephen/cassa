import re

from . import mcp_client
from .digest import build_digest
from .llm import ASSETS, parse_intent, parser_enabled
from .pay import execute_pay, preview_pay
from .sweep import run_sweep


async def _do_sweep(args: dict, dry_run: bool) -> dict:
    total = args.get("dca_total_usdc")
    split = args.get("dca_split")
    if total is not None:
        try:
            total = float(total)
        except (TypeError, ValueError):
            return {"reply": f"DCA total '{args.get('dca_total_usdc')}' is not a number.", "data": {}, "kind": "sweep"}
        if total <= 0:
            return {"reply": "DCA total must be greater than 0.", "data": {}, "kind": "sweep"}
    if split is not None:
        if not isinstance(split, dict) or not split:
            return {"reply": "DCA split must map assets to weights.", "data": {}, "kind": "sweep"}
        try:
            split = {str(k).upper(): float(v) for k, v in split.items()}
        except (TypeError, ValueError):
            return {"reply": "DCA split weights must be numbers.", "data": {}, "kind": "sweep"}
    result = await run_sweep(
        dca_total_usdc=total,
        dca_split=split,
        dry_run=True,
    )
    if not result.get("ok"):
        return {"reply": f"Sweep rejected: {result.get('error')}", "data": result, "kind": "sweep"}
    fills = "; ".join(f"{item['asset']} ${item['quote_usdc']:g} @ ${item['price']:,.2f}" for item in result["dca_fills"])
    earn = result.get("earn", {})
    if earn.get("ok", True) and earn.get("swept"):
        earn_note = f"swept ${earn['swept']:,.2f} to Flexible Earn ({earn.get('source')})"
    else:
        earn_note = earn.get("reason") or earn.get("error") or "earn checked"
    return {
        "reply": (
            f"Sweep preview [{result['mode']}]: {fills}. Earn: {earn_note}."
            + (" Open the investment review to approve live execution." if not dry_run else "")
        ),
        "data": result,
        "kind": "sweep",
    }


async def _do_pay(args: dict, dry_run: bool) -> dict:
    to = str(args.get("to", "")).strip()
    asset = str(args.get("asset", "USDC")).upper()
    memo = str(args.get("memo", ""))
    try:
        amount = float(args.get("amount", 0))
    except (TypeError, ValueError):
        return {"reply": f"Amount '{args.get('amount')}' is not a number.", "data": {}, "kind": "pay"}
    if not to:
        return {"reply": "Usage: pay @alice 250 USDC memo September VA", "data": {}, "kind": "pay"}
    if asset not in ASSETS:
        return {"reply": f"Unsupported asset '{asset}'. Use USDC, BTC, ETH, SOL, or BNB.", "data": {}, "kind": "pay"}
    preview = await preview_pay(to, amount, asset, memo)
    if not preview.get("ok"):
        return {"reply": f"Payment blocked: {preview.get('error')}", "data": preview, "kind": "pay"}
    if dry_run:
        return {
            "reply": f"Preview: pay {amount:g} {asset} to @{to}. Confirm needed: {preview['needs_confirm']}.",
            "data": preview,
            "kind": "pay",
        }
    return {
        "reply": f"Live execution requires explicit review. Prepared {amount:g} {asset} to @{to}; open the payment review to confirm it.",
        "data": preview,
        "kind": "confirm",
    }


async def _do_rules(text: str, dry_run: bool) -> dict:
    lowered = text.lower()
    if re.search(r"\b(balance|portfolio|holdings|worth)\b", lowered):
        digest = await build_digest()
        top = ", ".join(
            f"{row['asset']} {row['qty']} (~${row['usdc_value']:,.2f})" for row in digest["valuation"]["rows"][:5]
        )
        return {"reply": f"{digest['headline']}. {top}.", "data": digest, "kind": "balance"}
    if re.search(r"\b(sweep|dca|invest)\b", lowered):
        return await _do_sweep({}, dry_run)
    if lowered.startswith("/pay") or lowered.startswith("pay ") or "pay @" in lowered or lowered.startswith("send "):
        match = re.search(r"@?([A-Za-z0-9_.-]+)\s+([\d.]+)\s*([A-Za-z]+)?(?:.*memo\s*['\"]?([^'\"]+))?", text, re.I)
        if not match:
            return {"reply": "Usage: pay @alice 250 USDC memo September VA", "data": {}, "kind": "pay"}
        to, amount_raw, asset_raw, memo = match.groups()
        asset = (asset_raw or "USDC").upper()
        if asset.startswith("MEMO"):
            asset, memo = "USDC", asset
        return await _do_pay({"to": to, "amount": amount_raw, "asset": asset, "memo": memo or ""}, dry_run)
    if "price" in lowered or "btc" in lowered or "eth" in lowered or "sol" in lowered or "bnb" in lowered:
        prices = await mcp_client.get_prices()
        parts = []
        for symbol in ("BTCUSDC", "ETHUSDC", "SOLUSDC", "BNBUSDC"):
            node = prices.get(symbol, {})
            if isinstance(node, dict) and "price" in node:
                parts.append(f"{symbol.replace('USDC', '')} ${node['price']:,.2f} ({node.get('change_24h_pct', 0):+.2f}% 24h)")
        return {"reply": "Live: " + (" · ".join(parts) if parts else "price feed unreachable"), "data": prices, "kind": "prices"}
    if lowered.startswith("/digest") or "digest" in lowered or "report" in lowered:
        digest = await build_digest()
        return {
            "reply": f"{digest['headline']}. {len(digest['recent_activity'])} recent records. Earn Flexible holds ${digest['earn'].get('principal', 0):,.2f} at {digest['earn'].get('apr_pct', 0):g}% APR.",
            "data": digest,
            "kind": "digest",
        }
    return {
        "reply": "I handle: balance, sweep, pay @name amount ASSET, prices, digest. Example: pay @alice 250 USDC memo September VA",
        "data": {},
        "kind": "help",
    }


async def _dispatch_intent(intent: dict, dry_run: bool) -> dict:
    action = intent.get("action")
    if action == "balance":
        digest = await build_digest()
        top = ", ".join(
            f"{row['asset']} {row['qty']} (~${row['usdc_value']:,.2f})" for row in digest["valuation"]["rows"][:5]
        )
        return {"reply": f"{digest['headline']}. {top}.", "data": digest, "kind": "balance"}
    if action == "sweep":
        return await _do_sweep(intent, dry_run)
    if action == "pay":
        return await _do_pay(intent, dry_run)
    if action == "prices":
        prices = await mcp_client.get_prices()
        parts = []
        for symbol in ("BTCUSDC", "ETHUSDC", "SOLUSDC", "BNBUSDC"):
            node = prices.get(symbol, {})
            if isinstance(node, dict) and "price" in node:
                parts.append(f"{symbol.replace('USDC', '')} ${node['price']:,.2f} ({node.get('change_24h_pct', 0):+.2f}% 24h)")
        return {"reply": "Live: " + (" · ".join(parts) if parts else "price feed unreachable"), "data": prices, "kind": "prices"}
    if action == "digest":
        digest = await build_digest()
        return {
            "reply": f"{digest['headline']}. {len(digest['recent_activity'])} recent records. Earn Flexible holds ${digest['earn'].get('principal', 0):,.2f} at {digest['earn'].get('apr_pct', 0):g}% APR.",
            "data": digest,
            "kind": "digest",
        }
    return {
        "reply": "I handle: balance, sweep, pay @name amount ASSET, prices, digest. Example: pay @alice 250 USDC memo September VA",
        "data": {},
        "kind": "help",
    }


async def handle_chat(message: str, dry_run: bool = True) -> dict:
    text = (message or "").strip()
    if not text:
        return {
            "reply": "Send one of: balance, sweep, pay @alice 250 USDC, prices, digest.",
            "data": {},
            "kind": "help",
            "parsed_by": "rules",
        }
    if parser_enabled():
        try:
            out = await _dispatch_intent(await parse_intent(text), dry_run)
            out["parsed_by"] = "llm"
            return out
        except Exception:
            pass
    out = await _do_rules(text, dry_run)
    out["parsed_by"] = "rules"
    return out
