# Binance Agent OS capability evidence

This matrix separates documentation, live observation, bounded discovery, and
paper behavior. It contains no credentials or account identifiers.

Last updated: 2026-09-08.

Treat every balance, minimum, tool schema, and permission as stale until it is
read again from an authenticated Agent OS session.

## Hosts

| Host | Date (UTC) | Result |
| --- | --- | --- |
| Codex + `binance-agent-os` | 2026-09-08 | Authenticated. `spot.getAccount` and `convert.listAllConvertPairs` succeeded. No quote, accept, order, transfer, or Earn write was executed. |
| Grok CLI / this session | 2026-09-08 21:13–21:17 | Unauthenticated `initialize` against `https://agent.binance.com/mcp/agentic` returned HTTP 401 with Bearer OAuth resource metadata. `grok mcp doctor binance-agent-os` reached the HTTP server then failed handshake: OAuth authorization required. No live account read and no write from this host. |
| Cassa standalone OAuth | earlier 2026-09-08 | Rejected as an unsupported agent. Do not retry as a product credential path. |
| Public Render backend | 2026-09-08 21:13 | `https://cassa-m5n6.onrender.com/api/health` returned `ok: true`, `provider_mode: paper`, `mock_mode: true`. Paper writes are local fixtures, not Agent OS execution. |

Grok can be configured with the documented MCP URL, but this session did not
complete Binance OAuth and did not copy tokens from Codex. Live reads and
approved writes remain on the authenticated Codex host until this host
completes its own login.

## Capability table

| Capability | Evidence | Status for Cassa |
| --- | --- | --- |
| MCP connection (Codex) | OAuth login completed against `https://agent.binance.com/mcp/agentic` | Live verified in Codex |
| MCP connection (Grok) | HTTP endpoint reachable; initialize/handshake requires OAuth | Unavailable in this session |
| Agentic asset overview | Authenticated MCP discovery and read returned totals for Spot, Funding, Cross Margin, Isolated Margin, USDⓈ-M Futures, COIN-M Futures, Earn, and Copy Trading | Live verified in Codex; the account was funded at that observation |
| Agentic Spot balances | `spot.getAccount` with `omitZeroBalances`; USER_DATA; optional `omitZeroBalances`, `recvWindow` | Live verified in Codex 2026-09-08: 6 USDT, 0.057 TWT, 0.892 USTC, 0.18667147 TIA, and 1.03433979 1000CAT free; no locked amount observed. Stale until re-read. Local Cassa snapshot `agent_os_host_snapshot` still holds these decimals with `writes_enabled: false` and empty `convert_routes` |
| Options and Trading Bots | The same overview reported these wallets inactive/unavailable | Live observed in Codex |
| Main-account asset metadata | Bounded discovery exposed `sub_account.getMainAccountAsset` with no required input and `USER_DATA` read classification | Discovered, not used for Cassa spendable funds |
| Public Spot tickers | `spot.tickerPrice` called in Codex; public REST re-checked from this host 2026-09-08 21:13 via `data-api.binance.vision` | Live public market data. 21:13 prices: USDCUSDT 1.00004000, TWTUSDT 0.56360000, USTCUSDT 0.00556000, TIAUSDT 0.41330000, 1000CATUSDT 0.00208800. These are not Convert quotes. |
| Ordinary Spot Convert pairs | `convert.listAllConvertPairs`; no required input; optional `fromAsset`, `toAsset` | Live read in Codex 2026-09-08 15:43–15:44 UTC. USDT, TWT, USTC, TIA, and 1000CAT each had a USDC route. Observed `fromAssetMinAmount`: 0.01 USDT, 0.018 TWT, 1.8 USTC, 0.024 TIA, 4.7 1000CAT. `toAssetMinAmount` 0.01 USDC. USTC 0.892 and 1000CAT 1.03433979 were below those ordinary minimums. Route metadata is not a quote. |
| Ordinary Spot Convert quote | `convert.sendQuoteRequest` labeled **TRADE**. Required: `fromAsset`, `toAsset`, and either `fromAmount` or `toAmount`. Optional `walletType` (default `SPOT`), `validTime` (`10s`/`30s`/`1m`), `recvWindow`. Notes: `quoteId` is returned only if funds are sufficient | Catalog-discovered in Codex. Never called. Binance classifies this as TRADE, so it is not part of read-only discovery. |
| Ordinary Spot Convert accept | `convert.acceptQuote` labeled **TRADE**. Required: `quoteId` | Catalog-discovered. Never called. Exact user approval of the returned quote is required before this call. |
| Ordinary Spot Convert status | `convert.orderStatus` labeled USER_DATA. Either `orderId` or `quoteId` | Catalog-discovered. Never called. Intended reconciliation read after an approved accept. |
| Ordinary Spot Convert precision | `convert.queryOrderQuantityPrecisionPerAsset` labeled USER_DATA | Catalog-discovered. Not called in the bounded audit. |
| Ordinary Spot Convert history | `convert.getConvertTradeHistory` labeled USER_DATA. Required `startTime`, `endTime` | Catalog-discovered. Not called. |
| Futures Convert | `futures_usds.listAllConvertPairs`, `sendQuoteRequest`, `orderStatus`, `acceptTheOfferedQuote` | Discovered; not a Spot cash-funding route. Never substitute for ordinary Spot Convert. |
| Direct Spot sell path | `spot.exchangeInfo` (filters), `spot.orderTest` (TRADE, does not send to matching engine), `spot.newOrder` (TRADE), `spot.getOrder` (USER_DATA) | Catalog-discovered. No symbol filter read and no test/live order for current holdings. Fallback only if Convert is unavailable. |
| Dust eligibility to USDC | No `query-convertible-assets` / dust-eligibility MCP tool in the Codex catalog sample. `wallet.dustlog` exists and is historical USER_DATA only | Not MCP-verified; paper only in Cassa |
| Dust execution | No matching MCP tool found | Not enabled live |
| Internal wallet transfer | `wallet.userUniversalTransfer` discovered. Description is wallet-to-wallet among Spot / Funding / Futures / Margin / Options / Portfolio Margin types. No external address parameter | Internal Agentic/account transfer only. Not a recipient-payment rail. Never executed. |
| Earn actions | Aggregate overview included an Earn wallet; no Earn subscribe/redeem tool retained in the bounded sample | Balance surface observed; actions unverified |
| External recipient payment / withdrawal | MCP has no withdrawal scope. `wallet.allCoinsInformation` describes deposit/withdraw metadata and was not used | Unavailable through this MCP connection |

“Not found in bounded discovery” does not prove that Binance never exposes the
tool. It means Cassa must not claim or invoke the capability until the connected
account returns an exact schema and required permission.

## Preferred live funding path (not executed)

A safe live USDC funding action is **possible in schema** through ordinary Spot
Convert on the Agentic Spot wallet, if and only if:

1. An authenticated supported host has Trade scope.
2. A fresh `spot.getAccount` still shows free USDT at or above the current pair minimum.
3. `convert.sendQuoteRequest` is explicitly approved as a TRADE quote request.
4. The returned quote (amounts, fees/spread, `quoteId`, expiry) is shown and
   approved again before `convert.acceptQuote`.
5. Conversion is recorded as funds prepared, not as payment to a recipient.

Last useful candidate, **stale**: smallest ordinary Convert of free USDT to
USDC, provider minimum 0.01 USDT, last free USDT 6.00000000, preserved remainder
5.99 USDT if 0.01 is converted. Quote output, fees, and expiry are unknown
because no quote was requested.

## Reproducible read-only verification

1. Authenticate with `codex mcp login binance-agent-os`.
2. Restart the Codex host so the MCP tool catalog refreshes.
3. Ask: “Use the Binance MCP Server to show my Agentic account balances. Do not
   trade or transfer anything.”
4. Confirm the transcript shows Binance MCP discovery and execution, and that
   the response identifies the account boundary and wallet states.

Do not call `convert.sendQuoteRequest`, `convert.acceptQuote`, `spot.newOrder`,
or `wallet.userUniversalTransfer` during that check.

## Supported-host read boundary

Binance rejected Cassa's standalone OAuth attempt with its unsupported-agent
response. The official Binance Login documentation says OAuth access is
currently limited to close ecosystem partners. Cassa therefore keeps OAuth in
the supported Codex host. Its local MCP tool accepts only exact decimal balance
and route observations, stores no credentials or account identifiers, and
rejects every write adapter. Route/minimum observations remain evidence only;
they are not dust eligibility, a quote, or an execution receipt.

Official references:

- https://developers.binance.com/en/docs/agent-native/mcp-server/agentic
- https://developers.binance.com/en/docs/products/login/introduction
- https://www.binance.com/en/support/faq/detail/7a6e676e36fb455d96478932cb12d9f3
