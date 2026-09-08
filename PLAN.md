# Cassa product and implementation plan

Status: Phases 1–2 are complete locally. Binance MCP OAuth, the funded Agentic Spot balance read, and ordinary Convert pair/minimum checks are live-verified. An in-app read-only MCP adapter is implemented and write-isolated. The paper paths for Phase 3 funding execution, Phase 4 obligation settlement, and Phase 5 receipts/reconciliation are implemented and tested; live dust eligibility, route comparison, and authenticated execution remain open.
Updated: 2026-09-08.

## Product direction

Cassa is a cash-readiness agent for people and small teams holding funds on Binance. It turns scattered crypto into usable payment funds while protecting selected holdings, upcoming obligations, and cash reserves.

Core promise: “Know what you can afford, prepare the funds, approve the actions, and verify the result.”

The flagship workflow combines portfolio discovery, small-balance recovery, payment funding plans, the **Can I afford this?** feature, and verified execution. Optional investment allocation is separate from operational cash management. A token's unit price does not make it dust: eligibility and user thresholds refer to the total value of the holding.

This roadmap is ordered by dependencies and product value, not by a hackathon deadline.

## Users and jobs

- Individual: consolidate eligible small balances and prepare a known USDC amount without selling protected holdings.
- Team operator: prepare supplier, contractor, and subscription payments while preserving operating reserves.
- Approver: understand the exact assets, amounts, costs, recipients, and resulting cash position before authorizing execution.

Initial scope is a single connected owner and Spot balances. Shared team roles follow once the underlying payment and execution capabilities are proven.

## Verified capabilities and open questions

Documentation verification is not account-level verification. Cassa has now
verified MCP authentication and a read-only Agentic Spot balance response against the
connected funded account. No authenticated dust-conversion or
recipient-payment test has established access for this project. The dated
observations and schemas are recorded in `CAPABILITIES.md`.

| Capability | Evidence | Implementation rule |
| --- | --- | --- |
| Small balances to USDC | Binance's updated small-balance guide names USDC as a target | Discover eligibility for the connected account before offering execution |
| Dust discovery | `POST /sapi/v1/asset/dust-convert/query-convertible-assets`, accepts `targetAsset` | Treat this signed POST as discovery; do not confuse it with conversion |
| Dust execution | `POST /sapi/v1/asset/dust-convert/convert`, accepts `targetAsset` | Preserve provider transaction identifiers and actual charges |
| Dust history | `GET /sapi/v1/asset/dribblet` | Reconcile uncertain results before retrying |
| Legacy dust | `/sapi/v1/asset/dust` converts to BNB | Do not present this as direct USDC conversion |
| Agentic MCP | OAuth and `spot.getAccount` succeeded on 2026-09-08 for the funded Agentic sub-account; the app now implements this exact read behind its own OAuth boundary | Spot balance read is live-verified; dust, transfer, and Earn action schemas remain gated |
| Ordinary Convert | Pair metadata showed USDC routes for the funded USDT, TWT, USTC, TIA, and 1000CAT balances, with account-visible minimums | Route presence and minimums are evidence only; no quote or acceptance occurred |
| MCP account boundary | Transfers stay within the Agentic sub-account; no external withdrawal scope | Do not label these transfers as arbitrary teammate payments |
| Main-account funds | MCP main-account visibility may be read-only | Show visible-but-unspendable balances separately |
| Recipient payments | Current app uses a sub-account transfer adapter | Verify account eligibility, recipient type, permissions, and receipts before claiming payroll support |
| Earn | Existing app has paper and REST implementations | Revalidate current endpoints, account access, redemption constraints, and rates before enabling live use |

The updated help article describes balances below 20 USDT equivalent, an hourly interval, 2% ordinary-token fees and 10% Alpha-token fees. These are reference facts, not universal hardcoded rules. Regional pages differ. Account responses and current applicable documentation control actual eligibility and estimates. UI support for Funding/Alpha wallets does not establish access through the documented Spot/Margin API.

Sources verified 2026-09-06:

- [Small-balance conversion guide](https://www.binance.com/en-PH/support/faq/detail/360003012371)
- [Wallet asset API](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/asset)
- [Binance MCP capabilities and account boundaries](https://developers.binance.com/en/docs/agent-native/mcp-server/agentic)

Open checks: exact Spot ticker/balance schemas, signed REST permissions, dust target eligibility, cooldown behavior, Spot Convert quote semantics, recipient settlement rail, and current Earn APIs. Do not assume Spot testnet supports Wallet SAPI or Earn.

## Feature specification

### 1. Portfolio-wide cash discovery

Discover every nonzero supported balance dynamically. Keep free, locked, reserved, protected, read-only, and unpriced balances distinct. Record price source and timestamp. Unsupported or stale valuations must be unknown, not zero.

Show:

- Available USDC, with existing reservations deducted.
- Eligible small balances and estimated net recoverable USDC.
- Protected holdings and user exclusions.
- Locked funds, unavailable routes, and explicit reasons.
- Separate visible portfolios for each account and wallet; never imply funds can cross account boundaries automatically.

### 2. Small-balance recovery

Let users select a holding-value threshold and individual assets. Query provider eligibility with USDC as the intended target. Show estimates, charges, expiry or freshness, cooldowns when available, and exclusions before approval.

Support assets returned by discovery, rather than a fixed list of major coins. Do not automatically sell all holdings just because their token unit price is low. Preserve user-protected tokens and any configured fee-token balance.

### 3. Payment funding planner

Input: recipient or cash goal, USDC amount, due date, memo, protected holdings, reserve, and maximum acceptable conversion cost.

Process:

1. Read spendable USDC and active reservations.
2. Compute the target shortfall, including known payment fees and the required reserve.
3. Find eligible funding sources allowed by policy.
4. Compare executable alternatives by net proceeds and costs.
5. Propose only the conversions required to meet the goal where the provider permits partial amounts. If dust conversion consumes a whole eligible balance, show that explicitly.
6. Explain excluded assets and unresolved costs.
7. Present a bounded plan for approval.
8. Execute approved conversions, verify receipts and balances, then re-evaluate payment readiness.
9. Execute payment only through a verified supported rail and within the approved terms; otherwise mark funds prepared and provide an explicit user handoff.

Never silently substitute assets, recipients, rails, or a more expensive route after approval.

### 4. Can I afford this?

This is the primary decision view and a read-only tool. It must work before the user commits to conversion or payment.

Display:

- Cash available now.
- Additional estimated recoverable cash after conversion costs.
- Existing obligations and minimum reserve.
- Proposed payment and known payment costs.
- Cash remaining after the proposed action.
- Holdings that would be sold, protected holdings, and uncertain inputs.

Define `free_usdc` as unlocked, spendable USDC in the executable account. Define `other_obligations` as reservations excluding the obligation currently being evaluated. Then:

`cash_headroom = free_usdc - other_obligations - minimum_reserve`

`required = proposed_payment + known_payment_fees`

`shortfall = max(0, required - cash_headroom)`

`projected_headroom = cash_headroom + net_conversion_proceeds - required`

Do not count the same obligation or fee twice. Conversion proceeds are net of conversion costs. Unknown payment costs or stale quotes prevent an unconditional affordability claim.

Outcomes: affordable now; affordable after approved conversions; insufficient eligible funds; blocked by policy; unable to assess with current data. Funding readiness and recipient-payment availability are separate statuses.

Offer what-if changes to amount, reserve, and allowed assets. These recalculate the plan without executing or modifying saved policy unless the user explicitly saves it.

### 5. Route comparison

Adapters may offer dust conversion, ordinary Convert, and Spot sell routes where documented and authorized. Compare only routes with usable current data. Account for fees, spread, quantity increments, minimum notional, quote expiry, available balances, and intermediate-asset exposure.

Start with direct routes. Add bounded two-step routes only after direct execution is reliable. Reject cycles and uncontrolled route search. “Best route” means best among the feasible routes actually compared, with the objective shown; estimated routes must not be described as guaranteed quotes.

### 6. Obligations and reserves

Create one-off obligations with amount, asset, due date, recipient, and status. Store reservations separately from exchange balances. A reservation is an application constraint, not an exchange lock; external account activity requires revalidation.

Add recurring obligation templates and due-date notifications later. Scheduling creates proposals by default. It does not imply blanket permission to trade or pay automatically.

### 7. Payment and receipt management

Choose the first live rail only after verifying its actual recipient coverage. Validate recipient identity/type, supported settlement asset, required permissions, status-query support, and fees.

If only internal wallet transfers are available, label them accordingly. Use `funds_prepared` until external settlement is independently supported and verified. Never mark an invoice paid merely because funds were converted.

Attach provider IDs, actual amounts, fees, timestamps, and balance reconciliation to each completed action. Support an exportable activity/receipt report and a clear manual-settlement record that is distinct from provider-verified settlement.

### 8. Surplus management and optional investing

Calculate surplus only after obligations and reserves. Offer eligible Earn subscription and redemption proposals using verified provider capabilities. Distinguish estimated yield from realized interest and paper assumptions from live rates.

DCA is a separate investment workflow with its own allocation budget and approval. It must not consume funds reserved for operations.

## User experience

Primary navigation:

- Overview: spendable cash, recoverable cash, obligations, reserve, and connection status.
- Affordability: enter a proposed expense and inspect the outcome and alternatives.
- Recover balances: eligible assets, protected assets, route estimates, and approvals.
- Payments: obligations, preparation plans, supported settlement, and receipts.
- Activity: plans, approvals, provider results, failures, and reconciliations.
- Settings: accounts, permissions, exclusions, caps, reserve, and paper/live mode.

Chat and forms must call the same planning and approval services. Chat renders structured plans; an LLM cannot supply approval or bypass policy. Every screen clearly distinguishes paper execution, preview, and live execution. Do not claim unavailable features are working.

## Technical architecture

Keep FastAPI and Next.js initially. Separate provider access from application services instead of extending the misleading all-purpose `mcp_client.py` indefinitely.

Proposed backend boundaries:

- `providers/`: capability discovery, balances, market data, conversion, settlement, and Earn adapters; separate MCP, signed REST, and paper providers.
- `services/portfolio.py`: normalized balances and valuations.
- `services/affordability.py`: deterministic affordability calculation.
- `services/planner.py`: feasible funding plans and route comparisons.
- `services/policy.py`: caps, protected assets, reserves, recipient restrictions.
- `services/execution.py`: persisted action state machine and reconciliation.
- `services/obligations.py`: obligations and reservations.
- `services/receipts.py`: provider evidence and exports.

Use Decimal arithmetic for financial values and strings at API/storage boundaries where precision matters. Replace mutable JSON files with transactional SQLite for the single-instance product; use a database suited to multi-instance deployment before scaling horizontally.

Persist accounts/capabilities, balance snapshots, asset policies, obligations, reservations, plans, plan steps, quotes, approvals, execution attempts, provider receipts, and audit events. Preserve the existing paper ledger through an explicit migration or import; never reset user data implicitly.

Proposed API surface, subject to the provider capability spike:

- `GET /api/capabilities`, `GET /api/portfolio`
- `POST /api/affordability`, `POST /api/plans`
- `GET /api/plans/{id}`, `POST /api/plans/{id}/approve`
- `POST /api/plans/{id}/execute`, `GET /api/executions/{id}`
- Obligation and protected-asset management endpoints.
- Receipt/history endpoints and explicit reconciliation actions.

Planning endpoints do not move funds. Approval is bound to an immutable plan version, account, assets, amounts or explicitly approved bounds, recipient, costs, and validity window.

## Execution contract

Plan states: draft, quoted, awaiting approval, approved, executing, completed, partially completed, failed, expired, needs reconciliation, cancelled. Track step states independently.

- Authenticate the owner and authorize account access before enabling live writes or exposing the app publicly.
- Recheck policy, balance, reservations, capability, and quote validity immediately before execution.
- Lock conflicting application reservations and use unique operation identifiers.
- Do not blindly retry an external write after a timeout. Query provider status/history first; unresolved outcomes stay in needs reconciliation.
- Persist success after every step. Conversion and payment are not atomic and cannot be treated as rolled back together.
- If terms change outside approved bounds, require a new plan approval.
- Use provider confirmation requirements even if the application already has an approval.
- Enforce dollar-equivalent limits across supported payment assets. If valuation is unavailable, reject the action requiring that valuation.
- Avoid duplicate payments across chat, forms, retries, concurrent requests, and worker restarts.
- Keep secrets server-side and redact credentials from logs, exports, and errors.

## Implementation phases and acceptance gates

### Phase 0 — Capability proof

Status: MCP OAuth, account boundary, authenticated funded Spot balances, and
ordinary Convert pair/minimum metadata are verified. The in-app read-only MCP
adapter and OAuth endpoints are implemented. No Spot dust, internal-transfer,
or Earn action support has been established. See `CAPABILITIES.md`.

- Connect the intended account through the supported authentication flow.
- Inventory actual MCP tools and scopes; confirm account boundaries.
- Verify signed dust discovery with USDC, without converting funds.
- Validate normal Convert, Spot routing metadata, payment rail, and Earn availability independently.
- Record a capability matrix with documentation, observed responses, and unsupported reasons.

Gate: every proposed live action has a verified adapter path or is explicitly unavailable. Any real conversion/payment trial needs approval for its exact proposed action.

### Phase 1 — Correctness foundation

Status: complete for the current payment, sweep, and Earn write surfaces (2026-09-06).

- Fix stale-balance sweep calculations and propagate partial failure.
- Remove automatic chat confirmation and unify chat/form behavior.
- Fix multi-asset caps and protect reserved balances.
- Introduce Decimal handling, transactional persistence, durable execution records, and meaningful tests.
- Correct outdated UI/documentation claims and the README launch path.

Gate: no success is reported when a required step failed; no chat path bypasses approval; original user state survives migration.

Evidence: transactional SQLite state with lazy JSON import, durable payment and sweep operation records, explicit confirmation gates, USDC-equivalent caps, reserve-aware payment previews, partial sweep status, and the isolated backend regression suite.

### Phase 2 — Discovery and affordability

Status: implemented and tested in paper/local mode; live dust eligibility is capability-gated.

- Build dynamic portfolio normalization, dust eligibility, exclusions, obligations, and reserves.
- Implement deterministic Can I afford this? calculations and what-if controls.
- Render freshness, missing prices, non-executable balances, and separate funding/payment status.

Gate: calculations handle the selected obligation without double counting and explain every blocked or unknown outcome.

Evidence: dynamic holding normalization, paper dust discovery, protected-asset policies, USDC obligations, reserve accounting, deterministic affordability outcomes, and dashboard controls. Live provider eligibility cannot be marked complete until Phase 0 account verification succeeds.

### Phase 3 — Funding plans and conversion

Status: immutable direct dust-to-USDC plans are implemented and tested in paper mode; multi-route comparison and live conversion remain capability-gated.

- Implement direct-route estimates/quotes and cost comparison.
- Build review/approval cards with immutable plan versions.
- Execute approved conversion steps and reconcile actual proceeds.
- Use provider-driven paper fixtures for unavailable live test surfaces.

Gate: every successful conversion has a receipt and reconciled balances; expired quotes and ambiguous provider responses do not cause blind retries.

Evidence: persisted plan versions and steps, explicit approval, validity and fee ceilings, protected-asset rechecks, operation idempotency, provider-style receipts, post-conversion balance verification, and needs-reconciliation handling. The paper direct-route gate passes; Phase 3 is not complete for live use until Phase 0 and route-comparison work are finished.

Additional hardening: approval reserves selected assets across competing plans; execution atomically claims one plan, rechecks exact quantities, fees, and net-proceeds bounds, and expires changed plans before conversion. Successful provider receipts are persisted before downstream readiness checks, including partial-result paths.

### Phase 4 — Payment preparation and settlement

Status: obligation-to-plan preparation and the separate internal-payment flow are implemented and tested in paper mode; live recipient coverage remains unverified.

- Connect verified payment rail if available.
- Implement payment readiness, exact recipient review, settlement status, and receipts.
- Provide an honest funds-prepared handoff when settlement is unavailable.

Gate: conversion success alone never marks an obligation paid; retrying an interrupted plan cannot repeat a completed payment.

Evidence: a linked obligation becomes `ready` after its funding plan verifies sufficient post-conversion USDC. Payment rechecks the obligation's exact amount, asset, recipient, reservations, reserve, policy, and operation ID; only a successful settlement adapter response changes it to `paid`.

### Phase 5 — Product depth

Status: receipt export and operator-assisted failed-execution reconciliation are implemented locally; recurring proposals, alerts, and team roles remain planned.

- Add recurring obligation proposals, cash shortfall alerts, and receipt export.
- Add verified reserve-aware Earn proposals.
- Add shared roles and approval thresholds if team workflows warrant them.
- Add two-step route comparison only with cost and failure evidence.

Gate: each addition reuses the policy and execution services and does not create an alternate unrestricted write path.

### Phase 6 — Release and evidence

- Complete authentication, secret handling, deployment configuration, backups, and recovery checks.
- Publish clear setup instructions, capability limitations, and a reproducible paper demo.
- Capture an approved live integration example where account access permits it.
- Prepare the repository, demo, and submission materials with accurate claims.

Gate: another person can run the documented setup and reproduce the claimed workflow. Publication and transactions are separate authorized actions, not implied by this plan.

## Validation scenarios

1. 18 USDC available, 25 USDC expense, 5 USDC reserve: 12 USDC net funding shortfall before any additional payment fees.
2. Several holdings worth 1–5 USDC; include only provider-eligible, unprotected assets and account for actual charges.
3. A low-unit-price token with a large total holding is not automatically dust.
4. Existing obligation selected for payment is not reserved twice.
5. Protected or locked funds never count toward executable funding.
6. Missing prices, unavailable USDC target, cooldown, and insufficient net proceeds produce explicit outcomes.
7. Partial conversion failure leaves correct actual balances and the payment unexecuted if underfunded.
8. Timeout after provider success enters reconciliation; retry does not duplicate the action.
9. Approval expires or amount/recipient/route changes: execution is rejected pending renewed approval.
10. Concurrent plans and external account changes cannot spend the same application reserve silently.
11. Chat and forms enforce the same confirmations and limits, including non-USDC assets.
12. Payment success requires settlement evidence; unsupported settlement remains funds prepared.
13. Preview does not mutate trading balances. Paper execution is clearly labeled and never calls live write endpoints.
14. Earn subscription uses post-execution spendable funds after reserves, not an earlier balance snapshot.

## Demonstration and differentiation

Demonstrate: scattered balances → Can I afford this? → explained funding plan → explicit approval → verified conversion → supported payment or honest handoff → reconciled receipt.

Show one protected token, one ineligible balance, and one recovered failure. Use real provider evidence for live claims and label simulations. Evaluate usefulness through net cash recovered, payment goals funded, fees disclosed, reserve preservation, and correct reconciliation—not the number of endpoints or coins displayed.

## Current status

- Implemented: FastAPI/Next.js foundation, transactional state, dynamic portfolio view, paper dust eligibility and conversion, protected assets, USDC obligations, reserves, affordability outcomes, immutable funding plans, asset reservations, exact execution preflight, explicit version approval, obligation readiness, conversion and payment receipts, CSV export, reconciliation UI, chat intent parsing, corrected sweep/payment policy, durable operation IDs, Earn confirmation gates, in-app Agent OS OAuth/read-only Spot adapter, and an updated demo.
- Verified: isolated backend financial tests including balance conservation, cost and proceeds bounds, expiry, changed quantities, competing plans, duplicate execution, obligation term binding, receipt persistence/export, protected-asset rechecks and ambiguous-provider resolution; TypeScript checks; production frontend build; public Binance pricing; and preservation of existing JSON configuration/address book data during SQLite import.
- Known incomplete: completed in-app browser authorization against the newly hosted metadata document, live dust eligibility/conversion, executable comparison with normal Convert and Spot routes, external recipient settlement proof, automatic provider-history reconciliation, current live Earn verification, application-owner authentication for public deployment, and full browser end-to-end automation.
- Phase 4+ features and the remaining live/multi-route Phase 3 work stay planned until their acceptance gates pass.
