# Cassa demo — cash readiness on Binance

Use paper mode for the repeatable product walkthrough. Label it clearly. Use a
separate authenticated recording only for capabilities that have been verified
on the connected Binance account.

## Live Agent OS proof — 20 seconds

Before the repeatable paper story, show Codex connected to
`binance-agent-os`. Ask for the Agentic account overview with an explicit
read-only instruction. Show the MCP discovery/execution indicator and the
returned wallet states. The connected account verified on 2026-09-08 was empty,
which is acceptable evidence of authenticated access but not evidence of live
conversion.

Say: “Cassa connects through Binance Agent OS with revocable account access.
This account is empty, so the product demo now switches to a clearly labelled
paper portfolio to demonstrate planning and safeguards without pretending a
trade occurred.”

## Setup

1. Intentionally call `POST /api/paper/reset` so the same 18 USDC balance and
   small holdings appear on every run. This clears paper-only activity; never
   call it against data you need to preserve.
2. Keep dry-run on until the explicit paper-execution moment.
3. Prepare an expense amount, protected asset, and minimum reserve.
4. Do not describe internal sub-account movement as payment to an arbitrary external teammate.

## Two-minute product walkthrough

### 0–15 seconds — the problem

“Crypto portfolios often contain spendable stablecoins, protected investments,
and small leftover balances. Before paying someone, the hard question is not
what the portfolio is worth. It is what cash is safely available.”

Show the portfolio rows, free USDC, active reservations, spendable USDC, and the
paper/live capability labels.

### 15–45 seconds — Can I afford this?

Enter a 25 USDC expense, a 5 USDC reserve, and an allowlisted recipient. Run the
read-only affordability check.

Explain the calculation: free USDC minus other obligations minus the reserve,
plus only eligible net conversion proceeds, minus the payment and known fees.
Point out that a token is classified by the value of the holding—not its unit
price—and that protected or unpriced holdings are excluded.

### 45–75 seconds — small-balance recovery plan

Show an eligible paper small balance and its net USDC estimate. Protect another
asset and rerun the check to show it is removed from the proposed recovery.
Explain that live eligibility comes from Binance's signed discovery response;
the current build deliberately keeps live dust execution gated.

Create a funding plan. Review its immutable version, ten-minute validity window,
whole-balance conversions, net proceeds, 1% proceeds bound, and 2.5% cost ceiling. Approve that
exact version, then execute it against the paper ledger. Show the USDC increase,
zeroed source balances, and provider-style receipt IDs. Emphasize that this
prepares funds and changes a linked obligation to ready; it does not send the payment.

### 75–100 seconds — obligation and policy

Save the expense as an obligation. Show reserved USDC increase and spendable
USDC decrease. Preview a payment that would consume the reserve and show the
funding veto. Show the per-payment cap veto as a second policy example.

### 100–120 seconds — approval and evidence

Show that chat prepares a live payment for review instead of silently confirming
it. Review the exact recipient and amount separately from conversion. Show the
plan operation ID and explain that retrying a completed operation returns the
recorded result rather than converting or paying twice. Finish on the Activity
screen with the conversion receipts, CSV export, and empty reconciliation queue.

Close with: “Cassa tells you what you can afford, recovers eligible small
balances, protects operating reserves, and makes every money movement
reviewable.”

## Claims that require separate live evidence

- Binance MCP tools beyond the authenticated account overview recorded in
  `CAPABILITIES.md`.
- Signed dust discovery with USDC as target.
- Any successful live dust conversion and its provider transaction ID.
- Any recipient settlement rail beyond transfers inside the Agentic sub-account.
- Live Earn subscription or redemption and its current endpoint/receipt.
