"""Gated features: x402.

x402 has no confirmed client in this repo, so it fails closed with a
structured SKILL_UNAVAILABLE payload and an activity record. Callers must
surface `reason` in the UI and must not claim execution.

(Earn used to live here. It now has a paper adapter and a configured live REST
adapter whose account capability still requires verification.)
"""
from .store import get_config, log_activity


def x402_unavailable(amount: float, asset: str, memo: str, record: bool = True) -> dict:
    limit = float(get_config().get("max_x402_per_day_usdc", 20.0))
    payload = {
        "ok": False,
        "reason": "SKILL_UNAVAILABLE",
        "feature": "x402",
        "amount": amount,
        "asset": asset,
        "memo": memo,
        "limit_usdc_per_day": limit,
        "policy": f"x402 rail limited to ${limit:.0f}/day when available; larger amounts stay preview-only",
        "action_required": "Connect an x402 client, then retry within the daily limit. No funds moved.",
    }
    if record:
        log_activity(
            {
                "type": "x402",
                "ok": False,
                "reason": "SKILL_UNAVAILABLE",
                "amount": amount,
                "asset": asset,
                "memo": memo,
            }
        )
    return payload
