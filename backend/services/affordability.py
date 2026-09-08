from decimal import Decimal, InvalidOperation

from ..obligations import reserved_usdc
from ..policy import check_pay_policy
from ..store import get_config
from .portfolio import build_portfolio


def _money(value, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a decimal number") from exc
    if result < 0:
        raise ValueError(f"{name} cannot be negative")
    return result


def _text(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


async def assess_affordability(
    amount,
    payment_fee=0,
    minimum_reserve=None,
    obligation_id: int | None = None,
    recipient: str | None = None,
    allowed_assets: list[str] | None = None,
    portfolio: dict | None = None,
) -> dict:
    payment = _money(amount, "amount")
    if payment <= 0:
        raise ValueError("amount must be greater than 0")
    fee = _money(payment_fee, "payment_fee")
    config = get_config()
    reserve = _money(
        config.get("minimum_reserve_usdc", 50) if minimum_reserve is None else minimum_reserve,
        "minimum_reserve",
    )
    portfolio = portfolio or await build_portfolio(include_dust=True)
    free_usdc = _money(portfolio.get("free_usdc", 0), "free_usdc")
    other_obligations = reserved_usdc(exclude_id=obligation_id)
    cash_headroom = free_usdc - other_obligations - reserve
    required = payment + fee
    shortfall = max(Decimal("0"), required - cash_headroom)

    allowed = {asset.upper() for asset in allowed_assets} if allowed_assets else None
    candidates = []
    for row in portfolio.get("holdings", []):
        asset = str(row.get("asset", "")).upper()
        if asset == "USDC" or not row.get("dust_eligible") or row.get("protected"):
            continue
        if allowed is not None and asset not in allowed:
            continue
        net = _money(row.get("recoverable_usdc") or 0, f"{asset} recoverable_usdc")
        if net > 0:
            candidates.append({"asset": asset, "net_usdc": net, "holding": row})
    candidates.sort(key=lambda item: (item["net_usdc"], item["asset"]))

    selected = []
    proceeds = Decimal("0")
    if shortfall > 0:
        for item in candidates:
            selected.append(item)
            proceeds += item["net_usdc"]
            if proceeds >= shortfall:
                break

    verdict = None
    if recipient:
        verdict = check_pay_policy(recipient, payment, "USDC", amount_usdc=required)
    policy_blocked = bool(verdict and not verdict.get("allowed"))
    projected = cash_headroom + proceeds - required

    if policy_blocked:
        outcome = "blocked_by_policy"
    elif cash_headroom >= required:
        outcome = "affordable_now"
    elif proceeds >= shortfall:
        outcome = "affordable_after_conversions"
    elif portfolio.get("unknown_assets") and not candidates:
        outcome = "unable_to_assess"
    else:
        outcome = "insufficient_eligible_funds"

    return {
        "outcome": outcome,
        "funding_status": "ready" if outcome == "affordable_now" else "requires_conversion" if outcome == "affordable_after_conversions" else "not_ready",
        "payment_status": "internal_transfer_only" if recipient and not policy_blocked else "cash_goal_only" if not recipient else "blocked",
        "amount_usdc": _text(payment),
        "payment_fee_usdc": _text(fee),
        "required_usdc": _text(required),
        "free_usdc": _text(free_usdc),
        "other_obligations_usdc": _text(other_obligations),
        "minimum_reserve_usdc": _text(reserve),
        "cash_headroom_usdc": _text(cash_headroom),
        "shortfall_usdc": _text(shortfall),
        "selected_net_conversion_usdc": _text(proceeds),
        "projected_headroom_usdc": _text(projected),
        "selected_conversions": [
            {
                "asset": item["asset"],
                "quantity": item["holding"].get("sellable_quantity"),
                "gross_usdc": _text(_money(item["holding"].get("value_usdc") or item["net_usdc"], "gross_usdc")),
                "fee_usdc": _text(
                    max(
                        Decimal("0"),
                        _money(item["holding"].get("value_usdc") or item["net_usdc"], "gross_usdc") - item["net_usdc"],
                    )
                ),
                "net_usdc": _text(item["net_usdc"]),
                "route": "dust_to_usdc",
                "whole_eligible_balance": True,
            }
            for item in selected
        ],
        "unknown_assets": portfolio.get("unknown_assets", []),
        "policy": verdict,
        "explanation": {
            "formula": "free USDC - other obligations - reserve + selected net conversions - payment - fee",
            "conversion_estimates_only": bool(selected),
            "recipient_settlement": "Internal sub-account transfer only; external teammate settlement is not verified.",
        },
    }
