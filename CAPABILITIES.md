# Binance Agent OS capability evidence

This matrix separates documentation, live observation, bounded discovery, and
paper behavior. It contains no credentials or account identifiers.

Last verified: 2026-09-08.

| Capability | Evidence | Status for Cassa |
| --- | --- | --- |
| MCP connection | OAuth login completed against `https://agent.binance.com/mcp/agentic` | Live verified |
| Agentic asset overview | Authenticated MCP discovery and read returned totals for Spot, Funding, Cross Margin, Isolated Margin, USDⓈ-M Futures, COIN-M Futures, Earn, and Copy Trading | Live verified; the account is now funded |
| Agentic Spot balances | `spot.getAccount` with `omitZeroBalances`; response preserved free and locked quantities | Live verified: 6 USDT, 0.057 TWT, 0.892 USTC, 0.18667147 TIA, and 1.03433979 1000CAT free; no locked amount observed |
| Options and Trading Bots | The same overview reported these wallets inactive/unavailable | Live observed |
| Main-account asset metadata | Bounded discovery exposed `sub_account.getMainAccountAsset` with no required input and `USER_DATA` read classification | Discovered, not used for Cassa spendable funds |
| Futures account balances | Discovery exposed COIN-M and USDⓈ-M account/balance reads | Discovered; not needed for initial Spot cash workflow |
| Futures Convert pairs | `futures_usds.listAllConvertPairs`, no required input | Discovered, not executed |
| Futures Convert quote | `futures_usds.sendQuoteRequest`; requires `fromAsset`, `toAsset`, and either `fromAmount` or `toAmount` | Discovered quote surface; not a verified Spot funding route |
| Futures Convert status | `futures_usds.orderStatus`; description requires `orderId` or `quoteId` | Discovered read surface, not executed |
| Futures Convert acceptance | `futures_usds.acceptTheOfferedQuote`; requires `quoteId` | Write surface; never executed; exact user confirmation required |
| Spot ticker / 24-hour change | Supported by current Binance documentation; exact tool schema was not retained by bounded account discovery | Documented, not live-verified in this project |
| Ordinary Convert route checks | Read-only pair checks showed USDT, TWT, USTC, TIA, and 1000CAT support a route to USDC. Observed ordinary minimums were 0.01 USDT, 0.018 TWT, 1.8 USTC, 0.024 TIA, and 4.7 1000CAT | Live metadata observed; no quote requested and no conversion executed. Current USTC and 1000CAT quantities were below these ordinary minimums |
| Dust eligibility to USDC | No matching MCP tool was found in the bounded discovery sample. Signed Wallet API endpoints are documented separately | Not MCP-verified; paper only in Cassa |
| Dust execution | No matching MCP tool was found in bounded discovery | Not enabled live |
| Internal Agentic transfer | Documented as wallet-to-wallet inside the same Agentic sub-account; no exact tool was retained in bounded discovery | Documented, not a recipient-payment rail |
| Earn | Aggregate overview included an Earn wallet, but no Earn action tool was found in bounded discovery | Balance surface observed; actions unverified |
| External recipient payment | MCP has no withdrawal scope | Unavailable through this MCP connection |

“Not found in bounded discovery” does not prove that Binance never exposes the
tool. It means Cassa must not claim or invoke the capability until the connected
account returns an exact schema and required permission.

## Reproducible read-only verification

1. Authenticate with `codex mcp login binance-agent-os`.
2. Restart the Codex host so the MCP tool catalog refreshes.
3. Ask: “Use the Binance MCP Server to show my Agentic account balances. Do not
   trade or transfer anything.”
4. Confirm the transcript shows Binance MCP discovery and execution, and that
   the response identifies the account boundary and wallet states.

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
