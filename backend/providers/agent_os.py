"""Read-only Binance Agent OS MCP adapter.

OAuth credentials are stored locally in an ignored file. This adapter exposes
only the Agentic sub-account Spot balance read; every write remains outside
this provider until its exact tool, confirmation, and reconciliation contract
has been verified.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from threading import Lock
from typing import Any

import httpx2
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import AuthorizationCodeResult, OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from pydantic import AnyUrl


MCP_URL = "https://agent.binance.com/mcp/agentic"
DEFAULT_CLIENT_METADATA_URL = (
    "https://raw.githubusercontent.com/Ololadestephen/cassa/main/"
    "docs/binance-agent-os-client.json"
)
DEFAULT_CALLBACK_URL = "http://127.0.0.1:8000/api/providers/binance-agent-os/callback"
TOKEN_PATH = Path(__file__).resolve().parents[1] / "data" / "binance_agent_os_oauth.json"


class AgentOSAuthorizationRequired(RuntimeError):
    """The account must complete the browser OAuth flow before it can be read."""


class FileTokenStorage:
    """Small MCP SDK token store with expiry tracking and restrictive permissions."""

    def __init__(self, path: Path | None = None) -> None:
        configured = os.getenv("BINANCE_MCP_TOKEN_PATH", "").strip()
        self.path = Path(configured).expanduser() if configured else (path or TOKEN_PATH)
        self._lock = Lock()

    def _read(self) -> dict[str, Any]:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text())
                return payload if isinstance(payload, dict) else {}
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                return {}

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with self._lock:
            temporary.write_text(json.dumps(payload, separators=(",", ":")))
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)

    async def get_tokens(self) -> OAuthToken | None:
        payload = self._read()
        token = payload.get("tokens")
        if not isinstance(token, dict):
            return None
        expires_at = payload.get("expires_at")
        if expires_at is not None:
            try:
                if time.time() >= float(expires_at) - 30:
                    return None
            except (TypeError, ValueError):
                return None
        try:
            return OAuthToken.model_validate(token)
        except Exception:
            return None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        payload = self._read()
        payload["tokens"] = tokens.model_dump(mode="json", exclude_none=True)
        payload["saved_at"] = time.time()
        payload["expires_at"] = time.time() + tokens.expires_in if tokens.expires_in else None
        self._write(payload)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        value = self._read().get("client_info")
        if not isinstance(value, dict):
            return None
        try:
            return OAuthClientInformationFull.model_validate(value)
        except Exception:
            return None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        payload = self._read()
        payload["client_info"] = client_info.model_dump(mode="json", exclude_none=True)
        self._write(payload)

    async def has_valid_token(self) -> bool:
        return await self.get_tokens() is not None


def callback_url() -> str:
    return os.getenv("BINANCE_MCP_CALLBACK_URL", DEFAULT_CALLBACK_URL).strip() or DEFAULT_CALLBACK_URL


def client_metadata_url() -> str:
    return os.getenv("BINANCE_MCP_CLIENT_METADATA_URL", DEFAULT_CLIENT_METADATA_URL).strip()


def client_metadata_document() -> dict[str, Any]:
    metadata_url = client_metadata_url()
    return {
        "client_id": metadata_url,
        "client_name": "Cassa",
        "client_uri": "https://github.com/Ololadestephen/cassa",
        "redirect_uris": [callback_url()],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "application_type": "native",
    }


def _metadata() -> OAuthClientMetadata:
    return OAuthClientMetadata(
        client_name="Cassa",
        client_uri="https://github.com/Ololadestephen/cassa",
        redirect_uris=[AnyUrl(callback_url())],
        grant_types=["authorization_code"],
        response_types=["code"],
        token_endpoint_auth_method="none",
        application_type="native",
    )


def _json_from_result(result: Any) -> Any:
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    texts = [getattr(item, "text", "") for item in getattr(result, "content", []) if getattr(item, "text", "")]
    combined = "\n".join(texts).strip()
    if not combined:
        return {}
    try:
        return json.loads(combined)
    except json.JSONDecodeError:
        start, end = combined.find("{"), combined.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(combined[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise RuntimeError("Binance Agent OS returned an unreadable tool response")


def _find_balances(value: Any) -> list[dict[str, Any]] | None:
    if isinstance(value, dict):
        rows = value.get("balances")
        if isinstance(rows, list) and all(isinstance(row, dict) for row in rows):
            return rows
        for child in value.values():
            found = _find_balances(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_balances(child)
            if found is not None:
                return found
    return None


class AgentOSConnection:
    def __init__(self) -> None:
        self.storage = FileTokenStorage()
        self._task: asyncio.Task[Any] | None = None
        self._authorization_url: str | None = None
        self._redirect_ready: asyncio.Event | None = None
        self._callback: asyncio.Future[AuthorizationCodeResult] | None = None
        self._last_error: str | None = None
        self._last_success_at: int | None = None

    async def _redirect_handler(self, url: str) -> None:
        self._authorization_url = url
        if self._redirect_ready is not None:
            self._redirect_ready.set()

    async def _callback_handler(self) -> AuthorizationCodeResult:
        if self._callback is None:
            raise RuntimeError("No Binance OAuth callback is pending")
        return await self._callback

    async def _call_meta(self, tool_name: str, arguments: dict[str, Any], interactive: bool) -> Any:
        if not client_metadata_url():
            raise RuntimeError("BINANCE_MCP_CLIENT_METADATA_URL is required")
        if not interactive and not await self.storage.has_valid_token():
            raise AgentOSAuthorizationRequired("Connect Binance Agent OS to read the Agentic account")
        oauth = OAuthClientProvider(
            MCP_URL,
            _metadata(),
            self.storage,
            redirect_handler=self._redirect_handler if interactive else None,
            callback_handler=self._callback_handler if interactive else None,
            client_metadata_url=client_metadata_url(),
        )
        async with httpx2.AsyncClient(auth=oauth, timeout=30.0) as http_client:
            async with streamable_http_client(MCP_URL, http_client=http_client) as streams:
                read_stream, write_stream, _ = streams
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "tool_execute",
                        {"toolName": tool_name, "arguments": arguments},
                        read_timeout_seconds=30.0,
                    )
        if getattr(result, "is_error", False):
            raise RuntimeError("Binance Agent OS rejected the read-only balance request")
        return _json_from_result(result)

    async def spot_balances(self, interactive: bool = False) -> dict[str, Any]:
        payload = await self._call_meta("spot.getAccount", {"omitZeroBalances": True}, interactive)
        rows = _find_balances(payload)
        if rows is None:
            raise RuntimeError("Binance Agent OS account response did not contain Spot balances")
        free: dict[str, str] = {}
        locked: dict[str, str] = {}
        balances: dict[str, str] = {}
        from decimal import Decimal, InvalidOperation

        for row in rows:
            asset = str(row.get("asset", "")).upper().strip()
            if not asset:
                continue
            try:
                free_amount = Decimal(str(row.get("free", "0")))
                locked_amount = Decimal(str(row.get("locked", "0")))
            except InvalidOperation:
                continue
            total = free_amount + locked_amount
            if total <= 0:
                continue
            free[asset] = str(free_amount)
            locked[asset] = str(locked_amount)
            balances[asset] = str(total)
        self._last_success_at = int(time.time())
        self._last_error = None
        return {
            "source": "binance-agent-os-mcp",
            "account_scope": "agentic-sub-account",
            "balances": balances,
            "free": free,
            "locked": locked,
            "can_trade": payload.get("canTrade") if isinstance(payload, dict) else None,
            "account_type": payload.get("accountType") if isinstance(payload, dict) else "SPOT",
            "fetched_at": self._last_success_at,
        }

    async def _authorize_and_probe(self) -> None:
        try:
            await self.spot_balances(interactive=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._last_error = str(exc)
        finally:
            if self._redirect_ready is not None:
                self._redirect_ready.set()

    async def begin_connect(self) -> dict[str, Any]:
        if await self.storage.has_valid_token():
            try:
                await self.spot_balances()
                return await self.status()
            except AgentOSAuthorizationRequired:
                pass
            except Exception as exc:
                self._last_error = str(exc)
        if self._task is None or self._task.done():
            loop = asyncio.get_running_loop()
            self._authorization_url = None
            self._last_error = None
            self._redirect_ready = asyncio.Event()
            self._callback = loop.create_future()
            self._task = loop.create_task(self._authorize_and_probe())
        try:
            await asyncio.wait_for(self._redirect_ready.wait(), timeout=12)
        except TimeoutError:
            self._last_error = "Binance authorization did not start in time"
        result = await self.status()
        if self._authorization_url:
            result["authorization_url"] = self._authorization_url
        return result

    async def complete_callback(self, code: str, state: str | None, iss: str | None) -> None:
        if self._callback is None or self._callback.done():
            raise RuntimeError("No Binance authorization is waiting for this callback")
        self._callback.set_result(AuthorizationCodeResult(code=code, state=state, iss=iss))

    async def status(self) -> dict[str, Any]:
        authorized = await self.storage.has_valid_token()
        task_running = bool(self._task and not self._task.done())
        if authorized and self._last_success_at:
            state = "connected"
        elif authorized:
            state = "authorized"
        elif self._authorization_url and task_running:
            state = "authorization_required"
        elif task_running:
            state = "connecting"
        elif self._last_error:
            state = "error"
        else:
            state = "not_connected"
        return {
            "provider": "binance-agent-os",
            "state": state,
            "authorized": authorized,
            "account_scope": "agentic-sub-account",
            "access": "read-only",
            "last_success_at": self._last_success_at,
            "error": self._last_error,
            "client_metadata_url": client_metadata_url(),
            "callback_url": callback_url(),
        }


connection = AgentOSConnection()

