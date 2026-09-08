# Cassa — Binance Agent OS Mini Hackathon submission

## Submission identity

- Track: A — Build an AI agent using Agent OS
- Project: Cassa
- Tagline: Know what you can actually afford.
- One sentence: Cassa turns scattered Binance balances into a safe,
  reviewable payment-funding plan while protecting obligations, chosen assets,
  and a minimum cash reserve.
- Repository: https://github.com/Ololadestephen/cassa
- Demo video: add the final public video URL here

## Short pitch

Wallet value is not the same as spendable cash. Cassa discovers what is free,
locked, protected, reserved, read-only, unpriced, or provider-eligible; answers
“Can I afford this?”; and prepares the smallest bounded funding plan needed for
an expense. It considers every supported holding returned by discovery, not
only major coins. A token is “dust” because the total holding is small, not
because one token has a low unit price.

Cassa separates AI intent from deterministic financial decisions. The agent
uses Binance Agent OS for live market/account capability discovery, while the
application enforces reserve protection, obligations, immutable approvals,
cost bounds, idempotency, reconciliation, and receipts. Conversion success
means funds are prepared; recipient payment requires separate settlement
evidence.

## Why it is different

Most trading agents ask what to buy. Cassa asks whether money can safely leave
the account at all.

- Portfolio-wide recovery: supports dynamically discovered eligible tokens,
  including small holdings worth roughly 1–5 USDC.
- Cash-first decisioning: deducts other obligations and the minimum reserve
  before proposing any conversion.
- Explainable plans: shows assets, quantities, costs, net proceeds, exclusions,
  expiry, and post-action cash.
- Two confirmations: Cassa approval is bound to an immutable plan, and Binance
  confirmation remains required for provider writes.
- Honest settlement: Agentic internal-wallet transfers are not presented as
  arbitrary teammate payments.
- Failure safety: partial results and ambiguous timeouts are persisted and
  reconciled instead of blindly retried.

## Agent OS evidence

- Binance MCP OAuth completed successfully on 2026-09-08.
- An authenticated Agentic Spot balance read succeeded after the account was funded.
- The live account showed 6 USDT plus small TWT, USTC, TIA, and 1000CAT
  balances; no trade or transfer was used to manufacture the proof.
- Read-only route checks showed all five assets have a Convert path to USDC;
  TWT and TIA cleared the observed ordinary minimums while USTC and 1000CAT did not.
- Bounded discovery exposed account reads and futures Convert schemas.
- MCP dust, Spot Convert, internal-transfer, and Earn action schemas remain
  explicitly unverified. See `CAPABILITIES.md`.

## Demo outline

1. Show the authenticated Binance MCP account overview and funded Agentic Spot
   balances. State that this is live read evidence, not conversion evidence.
2. Switch to the clearly labelled paper fixture for a reproducible workflow.
3. Show 18 USDC free, a 25 USDC expense, and a 5 USDC reserve: the funding
   shortfall is 12 USDC.
4. Show small DOGE, ADA, TRX, and XRP holdings, each below the configured
   holding-value threshold. Show BTC excluded because it is not a small holding.
5. Protect one eligible token and recalculate to prove user exclusions work.
6. Restore the demo seed, create the funding plan, and show the exact selected
   assets, estimated costs, net proceeds, expiry, and projected headroom.
7. Approve the immutable paper plan and execute it once.
8. Show provider-style conversion receipts, the obligation becoming ready, and
   the separate recipient-payment status.
9. Retry the completed operation ID and show that it returns the stored result
   rather than converting twice.
10. Finish on Activity, receipts export, and the empty reconciliation queue.

Use the detailed narration in `DEMO.md`. Keep the live and paper portions
visually and verbally distinct.

## Suggested X post

> Meet Cassa: the cash-readiness agent for Binance Agent OS. It answers “Can I
> afford this?”, recovers eligible small balances—not just major coins—protects
> reserves and obligations, and requires reviewable approvals. Demo: [VIDEO]
> GitHub: https://github.com/Ololadestephen/cassa #BinanceAgentOS

Attach the demo video directly if the submission rules prefer uploaded media.
Replace `[VIDEO]` only with the final public video URL; do not publish the
placeholder.

## Prepared survey answers

Project name:

> Cassa

Project description:

> Cassa is a Binance cash-readiness agent that discovers spendable and eligible
> small balances, protects obligations and reserves, answers “Can I afford
> this?”, and creates immutable, cost-bounded funding plans with explicit
> approvals, idempotent execution, reconciliation, and receipts.

How Agent OS is used:

> Cassa connects to the Binance Agent OS MCP server using browser OAuth and a
> dedicated Agentic sub-account. The agent dynamically discovers market and
> account tools, reads the funded Spot balances without API keys, keeps
> main-account visibility read-only, and subjects any
> future provider write to both Cassa's exact plan approval and Binance's own
> confirmation. The submitted evidence includes a successful authenticated
> Agentic account overview; unsupported action capabilities remain gated.

Primary user problem:

> Crypto holders may have enough portfolio value but not enough safe payment
> cash after obligations and reserves. Small recoverable balances are scattered,
> and ordinary portfolio totals hide what is actually spendable.

Technical stack:

> FastAPI, Python Decimal calculations, SQLite transactional state, Next.js,
> TypeScript, Binance Agent OS MCP, and Binance public/signed REST adapters kept
> behind separate provider boundaries.

Safety and permissions:

> Least-privilege MCP scopes, no withdrawal capability, protected-asset and
> reserve enforcement, immutable versioned approvals, dollar-equivalent caps,
> quote expiry and cost bounds, unique operation IDs, persisted step receipts,
> partial-failure reporting, and reconciliation before retry.

## Final human-controlled checklist

- Confirm the account and jurisdiction are eligible.
- Make `Ololadestephen/cassa` public and verify README rendering.
- Record and upload the demo without credentials, OAuth URLs, account IDs, or
  other sensitive information.
- Follow `@Binance` and repost the official announcement.
- Publish the reply or quote-post with the real video and GitHub links.
- Complete the official survey.
- Submit before 2026-09-08 23:59 UTC.
