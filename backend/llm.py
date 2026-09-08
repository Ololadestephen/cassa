"""Optional Groq intent parser for Cassa chat.

Role: translate free text into one whitelisted intent. Nothing else.
Execution, caps, allowlist, and confirmation stay in backend/policy.py and
backend/pay.py — the parser can never confirm, move funds, or invent actions.

Fail-closed: disabled unless LLM_PARSER=true AND GROQ_API_KEY is set.
Any error (no key, timeout, bad JSON, unknown action) raises and the caller
falls back to the deterministic rules router. No key material lives here.
"""
import json
import os

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
ACTIONS = ("balance", "sweep", "pay", "prices", "digest", "help")
ASSETS = ("USDC", "BTC", "ETH", "SOL", "BNB")

SYSTEM = """You parse treasury commands into JSON. Reply with exactly one JSON object, no other text.
Actions and required args:
- {"action":"balance"}
- {"action":"sweep","dca_total_usdc":number optional,"dca_split":{"BTC":w,"ETH":w,"SOL":w} optional}
- {"action":"pay","to":string,"amount":number,"asset":"USDC|BTC|ETH|SOL|BNB","memo":string}
- {"action":"prices"}
- {"action":"digest"}
- {"action":"help"}
Rules: strip @ from names; default asset USDC and memo ""; amounts must be plain numbers > 0; if the text names no action, use help; never add other keys or actions."""


def parser_enabled() -> bool:
    return os.getenv("LLM_PARSER", "false").lower() == "true" and bool(os.getenv("GROQ_API_KEY", ""))


def model() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


async def parse_intent(message: str) -> dict:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model(),
                "temperature": 0,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": message[:500]},
                ],
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    try:
        intent = json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError(f"Parser returned non-JSON: {exc}") from exc
    if not isinstance(intent, dict) or intent.get("action") not in ACTIONS:
        raise RuntimeError(f"Parser returned unknown action: {content[:120]}")
    return intent
