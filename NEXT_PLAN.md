# Cassa live-first recovery plan

Updated: 2026-09-08

## Outcome

Produce a defensible Binance Agent OS Track A submission in which the live
integration is real, the safety decision is useful, and every unverified action
is labeled honestly. Stop optimizing the public paper demo until the strongest
available live Agent OS action has been discovered and, if the user approves,
verified end to end.

The product story remains:

> A wallet balance does not answer what can safely be spent. Cassa reads the
> account, protects obligations and reserves, finds eligible funding sources,
> prepares only the shortfall, requires an exact approval, and proves what
> happened.

## Current truth

### Live verified

- Binance Agent OS OAuth in the supported Codex host.
- Funded Agentic Spot balance read using `spot.getAccount`.
- Public Binance market pricing.
- Read-only ordinary Convert pair/minimum metadata for the observed holdings
  via `convert.listAllConvertPairs`.
- Credential-free sync into the local Cassa decision engine.

### Catalog-discovered, never executed

- Ordinary Spot Convert quote/accept/status: `convert.sendQuoteRequest` (TRADE),
  `convert.acceptQuote` (TRADE), `convert.orderStatus` (USER_DATA).
- Direct Spot order tools: `spot.exchangeInfo`, `spot.orderTest`,
  `spot.newOrder`, `spot.getOrder`. No filter read and no order placed.
- Internal wallet movement: `wallet.userUniversalTransfer`. Not a recipient rail.

### Implemented and tested, but paper only

- Dynamic portfolio normalization and small-holding discovery.
- Protected-asset and reserve policy.
- Deterministic `Can I afford this?` calculation.
- Immutable funding plans, approval versions, asset reservations, execution
  state, receipts, idempotency, partial failure, and reconciliation.
- Internal payment and Earn adapters.

### Not live verified

- Any Convert quote or accepted conversion.
- Small-balance/dust eligibility query with USDC as target (only `wallet.dustlog`
  history exists in the MCP catalog sample).
- Direct Spot sell route and filters for the currently held small assets.
- External recipient settlement.
- Earn subscription or redemption.
- Binance OAuth inside this Grok host (handshake requires authorization).

### Deployment

- GitHub `main` contains the current implementation.
- Render backend is live at `https://cassa-m5n6.onrender.com` in paper mode.
- The Render health and portfolio endpoints returned successfully on
  2026-09-08.
- The Vercel frontend should use root directory `frontend` and
  `NEXT_PUBLIC_API=https://cassa-m5n6.onrender.com`.
- Vercel deployment status has not been verified in this repository.
- The public deployment has no owner authentication. It must not receive live
  financial credentials or enable provider writes.

## Architecture decision

Do not attempt to make the public website a standalone Binance OAuth client for
this submission. Binance rejected that client path. Use the supported agent
host as the private execution plane:

```text
User
  -> supported Codex host
      -> Binance Agent OS MCP (authentication, live reads, approved writes)
      -> Cassa MCP/service (deterministic policy, plan, approval record, proof)
  -> Cassa web companion (decision view and evidence)
```

The live provider action and Cassa approval must be bound by the same immutable
manifest: account boundary, asset, quantity or approved bounds, target asset,
fees/cost ceiling, quote expiry, and operation ID.

## Priority 0 — stop further drift

- No more visual redesign, generic feature work, new trading strategies, or
  deployment-provider changes.
- Do not call paper execution “live”.
- Do not claim that a conversion pays a recipient.
- Do not attempt external payments through Agentic internal transfers.
- Do not run a real action merely to improve the demo; exact approval remains
  mandatory.

Gate: the next agent can state the verified, unavailable, and unknown surfaces
without relying on README claims.

## Priority 1 — live capability spike, read-only

Use dynamic Binance MCP discovery in the authenticated Codex host. Limit the
search to:

1. Agentic Spot account balances and permissions.
2. Ordinary Spot Convert pair, quote, accept, and status tools.
3. Spot exchange information, symbol filters, order preview/test, order, and
   order-status tools for held assets and USDC.
4. Small-balance/dust eligibility query with a USDC target.
5. Agentic transfer/payment tools and their exact account boundary.

For every candidate tool, record:

- exact name and schema;
- read or write classification;
- wallet/account scope;
- confirmation behavior;
- current asset minimum and quantity constraints;
- whether it was merely discovered, read successfully, or executed;
- timestamp and sanitized evidence.

Do not call quote or order endpoints if Binance classifies them as financial
writes without first explaining that fact. Do not accept any quote or submit
any order during this phase.

Acceptance gate: one current capability table establishes whether a safe live
USDC funding action is possible through the connected account.

## Priority 2 — prepare one bounded live proof

Preferred path, in order:

1. Ordinary Spot Convert from a small amount of free USDT to USDC.
2. Direct Spot sell from one unprotected holding to USDC.
3. No write; verified live read plus deterministic plan if neither path is
   available.

The proposal must show:

- source and target asset;
- exact amount or narrow approved bound;
- current free balance and preserved remainder;
- provider minimum and precision;
- quoted output, fees/spread, and expiration where available;
- protected assets and obligations left untouched;
- operation ID and reconciliation method;
- explicit statement that the action prepares USDC and does not pay anyone.

Stop and request explicit user approval for that exact proposal. An approval
for implementation, testing, or “continue” is not financial authorization.

Acceptance gate: the user has approved a specific provider action in the
current conversation, or the plan records that no safe action is available.

## Priority 3 — execute and reconcile only if approved

Immediately before execution:

1. Re-read the account balance and permissions.
2. Revalidate the quote, minimum, precision, fee/cost ceiling, and expiry.
3. Reject changed terms outside the approval.
4. Submit once with a unique operation ID.
5. Persist the provider response before downstream work.
6. Query status/history after ambiguous results; never blindly retry.
7. Re-read balances and reconcile actual source debit, USDC credit, and fees.
8. Recompute affordability.

Acceptance gate: provider identifier plus post-action balance reconciliation.
Without both, mark the outcome unresolved rather than successful.

## Priority 4 — connect the proof to Cassa

Only after Priority 1 establishes the schema:

- Add a provider-neutral external-action manifest to Cassa if the existing plan
  model cannot represent the live action exactly.
- Add a narrow Cassa MCP tool to record the approved manifest and sanitized
  provider result. It must not accept credentials or arbitrary execution
  instructions.
- Keep Binance tool invocation in the supported host.
- Render the live receipt, reconciliation state, remaining reserve, and updated
  affordability result in Evidence.
- Add tests for approval binding, changed terms, duplicate submission,
  ambiguous timeout, balance conservation, precision, and receipt persistence.

Acceptance gate: the same immutable terms appear in the proposal, approval,
provider action, and receipt.

## Priority 5 — submission package

Build the demo around `Problem - Execution - Pain - Story - Demo`:

1. **Problem:** portfolio value is not safely spendable cash.
2. **Pain:** small balances, route minimums, protected holdings, obligations,
   and reserves make a blanket “sell all” action unsafe.
3. **Execution:** show live Agent OS authentication and a fresh account read.
4. **Story:** ask whether a concrete payment goal can be funded while keeping
   the reserve.
5. **Demo:** show Cassa's deterministic decision, exclusions, bounded plan,
   approval boundary, and either a reconciled live funding action or an honest
   unavailable state.

Update `CAPABILITIES.md`, `DEMO.md`, `SUBMISSION.md`, and README claims to match
the evidence obtained. Capture no secrets, authorization URLs, account IDs, or
tokens.

Acceptance gate:

- Public repository and demo URL work.
- Video link is publicly viewable.
- Every “live” claim has provider evidence.
- Paper states are labeled.
- GitHub, X reply/quote-repost, and survey are submitted before the stated
  September 8, 2026 23:59 UTC deadline.

## Verification suite

Run after relevant implementation changes:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -c "import backend.main"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s backend/tests -v
frontend/node_modules/.bin/tsc -p frontend/tsconfig.json --noEmit --incremental false
cd frontend && npm run build
```

Also verify the public backend with:

```sh
curl -sS https://cassa-m5n6.onrender.com/api/health
```

Do not run automated tests against live provider write APIs or the user's live
ledger.

## Definition of done

The next phase is done only when one of these statements is supported by
evidence:

1. “Cassa used Binance Agent OS to execute one explicitly approved, bounded
   Spot funding action and reconciled the provider result,” or
2. “The connected Binance Agent OS account exposes live reads but no verified
   safe Spot funding action; Cassa demonstrates the decision and approval
   system without claiming execution.”

Anything between those statements is unresolved, not complete.
