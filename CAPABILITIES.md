# Binance Agent OS capability evidence

This matrix separates documentation, live observation, bounded discovery, and
paper behavior. It contains no credentials or account identifiers.

Last verified: 2026-09-08.

| Capability | Evidence | Status for Cassa |
| --- | --- | --- |
| MCP connection | OAuth login completed against `https://agent.binance.com/mcp/agentic` | Live verified |
| Agentic asset overview | Authenticated MCP discovery and read returned totals for Spot, Funding, Cross Margin, Isolated Margin, USDⓈ-M Futures, COIN-M Futures, Earn, and Copy Trading | Live verified; connected account was empty |
| Options and Trading Bots | The same overview reported these wallets inactive/unavailable | Live observed |
| Main-account asset metadata | Bounded discovery exposed `sub_account.getMainAccountAsset` with no required input and `USER_DATA` read classification | Discovered, not used for Cassa spendable funds |
| Futures account balances | Discovery exposed COIN-M and USDⓈ-M account/balance reads | Discovered; not needed for initial Spot cash workflow |
| Futures Convert pairs | `futures_usds.listAllConvertPairs`, no required input | Discovered, not executed |
| Futures Convert quote | `futures_usds.sendQuoteRequest`; requires `fromAsset`, `toAsset`, and either `fromAmount` or `toAmount` | Discovered quote surface; not a verified Spot funding route |
| Futures Convert status | `futures_usds.orderStatus`; description requires `orderId` or `quoteId` | Discovered read surface, not executed |
| Futures Convert acceptance | `futures_usds.acceptTheOfferedQuote`; requires `quoteId` | Write surface; never executed; exact user confirmation required |
| Spot ticker / 24-hour change | Supported by current Binance documentation; exact tool schema was not retained by bounded account discovery | Documented, not live-verified in this project |
| Spot balances by asset | Aggregate Agentic overview was verified, but the exact per-asset Spot schema was not retained | Partially verified; connected account had no assets |
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

Official references:

- https://developers.binance.com/en/docs/agent-native/mcp-server/agentic
- https://www.binance.com/en/support/faq/detail/7a6e676e36fb455d96478932cb12d9f3
