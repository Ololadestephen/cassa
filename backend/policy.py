"""Policy enforcement for Cassa. Every execute path calls through here first.

- Allowlist: recipient id must exist in the addressbook.
- No external withdraw: destination must be an internal sub-account reference.
  Anything resembling an on-chain address is rejected before any execute call.
- Caps: per-pay max $500 (hard veto above), daily max, confirm-at-or-above threshold.
- x402: $20/day ceiling documented in config; x402 rail itself is gated unavailable.
"""
from decimal import Decimal, InvalidOperation

from .store import get_addressbook, get_config, load


def normalize_recipient_id(raw: str) -> str:
    return (raw or "").strip().lstrip("@").lower()


def looks_like_external_address(value: str) -> bool:
    text = (value or "").strip()
    lowered = text.lower()
    if lowered.startswith("0x") and len(text) >= 26:
        return True
    if lowered.startswith(("bc1", "tb1", "bnb1", "tbnb1")):
        return True
    if lowered.endswith(".eth") or ".eth:" in lowered:
        return True
    if len(text) >= 64 and all(ch in "0123456789abcdefABCDEF" for ch in text[:64]):
        return True
    return False


def resolve_recipient(raw: str) -> dict | None:
    book = get_addressbook()
    return book.get(normalize_recipient_id(raw))


def spent_today_usdc() -> Decimal:
    from datetime import UTC, datetime

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    total = Decimal("0")
    for row in load("activity", []):
        if row.get("type") == "pay" and row.get("day") == today and row.get("ok", True):
            value = row.get("amount_usdc")
            if value is None and str(row.get("asset", "USDC")).upper() == "USDC":
                value = row.get("amount", 0)
            try:
                total += Decimal(str(value)) if value is not None else Decimal("0")
            except (InvalidOperation, TypeError, ValueError):
                continue
    return total.quantize(Decimal("0.01"))


def check_pay_policy(to: str, amount, asset: str, amount_usdc=None) -> dict:
    cfg = get_config()
    per_pay = Decimal(str(cfg["max_per_pay_usdc"]))
    daily = Decimal(str(cfg["max_daily_usdc"]))
    confirm_at = Decimal(str(cfg["require_confirm_over_usdc"]))
    try:
        requested = Decimal(str(amount))
        usdc_value = Decimal(str(amount_usdc if amount_usdc is not None else amount))
    except (InvalidOperation, TypeError, ValueError):
        return {"allowed": False, "error": "Amount and USDC valuation must be valid decimal numbers"}
    code = normalize_recipient_id(to)
    if not code:
        return {"allowed": False, "error": "Recipient is required"}
    if requested <= 0:
        return {"allowed": False, "error": "Amount must be greater than 0"}
    if str(asset).upper() != "USDC" and amount_usdc is None:
        return {"allowed": False, "error": f"A current USDC valuation is required to apply payment caps to {str(asset).upper()}"}
    recipient = resolve_recipient(to)
    if recipient is None:
        known = ", ".join(sorted(get_addressbook())) or "(empty)"
        return {"allowed": False, "error": f"Recipient '@{code}' is not on the allowlist. Known: {known}"}
    destination = str(recipient.get("email_or_uid", ""))
    if not destination or looks_like_external_address(destination) or looks_like_external_address(code):
        return {"allowed": False, "error": "External withdraws are disabled. Internal sub-account destinations only."}
    if usdc_value > per_pay:
        return {
            "allowed": False,
            "error": f"USDC value ${float(usdc_value):g} exceeds the per-pay cap of ${float(per_pay):g}.",
        }
    spent = spent_today_usdc()
    if spent + usdc_value > daily:
        return {
            "allowed": False,
            "error": f"Would exceed the daily cap of ${float(daily):g} (already spent ${float(spent):g} today).",
        }
    return {
        "allowed": True,
        "recipient": {**recipient, "id": code},
        "amount_usdc": float(usdc_value),
        "needs_confirm": bool(usdc_value >= confirm_at) or str(asset).upper() != "USDC",
        "caps": {"per_pay": float(per_pay), "daily": float(daily), "spent_today": float(spent), "confirm_at": float(confirm_at)},
    }
