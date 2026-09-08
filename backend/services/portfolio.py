from decimal import Decimal, InvalidOperation

from .. import mcp_client
from ..digest import split_holdings
from ..obligations import get_asset_policies, reserved_usdc
from ..store import get_config


STABLE_ASSETS = {"USDC": Decimal("1")}


def _decimal(value, default: Decimal | None = None) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.quantize(Decimal("0.00000001")).normalize(), "f")


async def build_portfolio(include_dust: bool = True, balances: dict | None = None) -> dict:
    balances = balances or await mcp_client.get_balances()
    spot, earn_usdc, earn = await split_holdings(balances)
    prices = dict(balances.get("prices") or {})
    assets = [str(asset).upper() for asset, qty in spot.items() if _decimal(qty, Decimal("0")) > 0]
    missing_symbols = tuple(
        f"{asset}USDC" for asset in assets if asset not in STABLE_ASSETS and f"{asset}USDC" not in prices
    )
    if missing_symbols:
        extra = await mcp_client.get_prices(missing_symbols)
        prices.update(extra)

    dust = {"available": False, "reason": "not_requested", "details": []}
    if include_dust:
        try:
            dust = await mcp_client.get_dust_convertible_assets("USDC", prices=prices)
        except Exception as exc:
            dust = {"available": False, "reason": "provider_unavailable", "error": str(exc), "details": []}
    eligible = {str(item.get("asset", "")).upper(): item for item in dust.get("details", [])}
    route_observations = {
        str(item.get("from_asset", "")).upper(): item
        for item in balances.get("convert_routes", [])
        if str(item.get("to_asset", "")).upper() == "USDC"
    }
    policies = get_asset_policies()
    threshold = Decimal(str(get_config().get("dust_under_usdc", 5)))
    rows = []
    unknown_assets = []
    total = Decimal("0")

    for asset in assets:
        quantity = _decimal(spot.get(asset), Decimal("0")) or Decimal("0")
        policy = policies.get(asset, {"protected": False, "minimum_keep": "0"})
        minimum_keep = _decimal(policy.get("minimum_keep"), Decimal("0")) or Decimal("0")
        sellable_quantity = max(Decimal("0"), quantity - minimum_keep)
        if asset in STABLE_ASSETS:
            price = STABLE_ASSETS[asset]
        else:
            node = prices.get(f"{asset}USDC", {})
            price = _decimal(node.get("price")) if isinstance(node, dict) else None
        value = quantity * price if price is not None else None
        if value is None:
            unknown_assets.append(asset)
        else:
            total += value

        provider = eligible.get(asset)
        route = route_observations.get(asset)
        route_minimum = _decimal((route or {}).get("minimum_from_amount"))
        if route and route.get("supported") and route_minimum is not None:
            convert_route_status = "above_minimum" if sellable_quantity >= route_minimum else "below_minimum"
        elif route and not route.get("supported"):
            convert_route_status = "unsupported"
        else:
            convert_route_status = "not_checked"
        provider_net = _decimal((provider or {}).get("net_usdc") or (provider or {}).get("toTargetAssetOffExchange"))
        dust_eligible = (
            bool(provider)
            and not bool(policy.get("protected"))
            and minimum_keep == 0
            and sellable_quantity > 0
        )
        rows.append(
            {
                "asset": asset,
                "quantity": _text(quantity),
                "price_usdc": _text(price),
                "value_usdc": _text(value),
                "protected": bool(policy.get("protected")),
                "minimum_keep": _text(minimum_keep),
                "sellable_quantity": _text(sellable_quantity),
                "small_balance": bool(value is not None and value <= threshold),
                "dust_eligible": dust_eligible,
                "recoverable_usdc": _text(provider_net) if dust_eligible else None,
                "eligibility_source": dust.get("source") if provider else None,
                "ordinary_convert_route_status": convert_route_status,
                "ordinary_convert_minimum": _text(route_minimum),
                "ordinary_convert_evidence_only": bool(route),
                "unavailable_reason": (
                    "protected" if policy.get("protected") else
                    "minimum_keep" if minimum_keep > 0 else
                    "unpriced" if value is None else
                    None if provider else "not_provider_eligible"
                ),
            }
        )

    rows.sort(key=lambda row: Decimal(row["value_usdc"] or "-1"), reverse=True)
    reserved = reserved_usdc()
    free_usdc = _decimal(spot.get("USDC"), Decimal("0")) or Decimal("0")
    return {
        "mode": balances.get("mode"),
        "source": balances.get("source"),
        "fetched_at": prices.get("fetched_at"),
        "free_usdc": _text(free_usdc),
        "reserved_usdc": _text(reserved),
        "spendable_after_reservations_usdc": _text(max(Decimal("0"), free_usdc - reserved)),
        "total_priced_usdc": _text(total + Decimal(str(earn_usdc))),
        "unknown_assets": unknown_assets,
        "holdings": rows,
        "earn": earn,
        "dust": {
            "available": dust.get("available", False),
            "source": dust.get("source"),
            "target_asset": "USDC",
            "reason": dust.get("reason"),
            "error": dust.get("error"),
        },
    }
