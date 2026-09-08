# Cassa — Binance Agent OS Mini Hackathon submission

## Track

Track A: an AI agent built with Binance Agent OS. A trade is not required for
this track. Do not imply Track B eligibility unless a separately approved real
trade is completed.

## One-line pitch

Cassa turns scattered Binance balances into payment readiness: it protects
reserves, identifies usable small holdings, answers “Can I afford this?”, and
binds every proposed money movement to an exact approval and receipt trail.

## Two-minute recording

1. **Problem — 0:00–0:15.** “A portfolio balance is not the same thing as cash
   I can safely spend. Some funds are locked, protected, promised to an
   obligation, or too small for an available conversion route.”
2. **Live Agent OS proof — 0:15–0:35.** In Codex, show the read-only Binance MCP
   call returning the funded Agentic Spot balances. Show the Cassa sync result.
   Do not reveal an authorization URL, token, account identifier, or credential.
3. **Decision desk — 0:35–0:55.** Refresh Cassa. Point to
   `binance-agent-os-mcp-via-codex`, the Agentic sub-account boundary, the five
   discovered assets, the observation age, and **writes locked**.
4. **Pain and judgment — 0:55–1:15.** Explain that a cheap token is not
   automatically dust. Cassa uses total holding value, provider eligibility,
   route minimums, user protection, obligations, and the cash reserve.
5. **Can I afford this? — 1:15–1:35.** Use the repeatable paper scenario: 18
   USDC available, 25 USDC expense, 5 USDC reserve. The shortfall is 12 USDC
   before payment fees. Protect one holding and rerun to show the plan change.
6. **Execution and evidence — 1:35–1:55.** Create the immutable paper funding
   plan, approve its exact version, execute it once, and show receipts plus the
   idempotent operation ID. State clearly that funds prepared is not recipient
   settlement.
7. **Close — 1:55–2:00.** “Cassa tells you what can safely move before an agent
   moves anything.”

## Claims safe to make

- Binance Agent OS authentication and funded Spot balance reads were verified
  through the supported Codex host.
- Cassa dynamically supports discovered holdings rather than a major-coin
  allowlist.
- Cassa keeps protected assets, obligations, reserves, and unsupported or
  unpriced assets out of spendable cash.
- Cassa's conversion, payment, receipt, and reconciliation workflow is
  repeatable in paper mode.
- Live dust execution, external recipient settlement, and Earn actions remain
  disabled because they have not been account-verified.

## Why it is different

Most trading agents ask what to buy. Cassa asks whether money can safely leave
the account at all. It supports dynamically discovered holdings, deducts
obligations and reserves before proposing recovery, binds approval to an
immutable plan, records partial outcomes, and never calls an internal Agentic
wallet movement an external recipient payment.

## X reply / quote-repost copy

> Cassa answers: what can I safely spend? Built with @Binance Agent OS + Codex,
> it reads Agentic balances, protects reserves, identifies usable small
> holdings, and creates approval-bound funding plans with receipts. Demo:
> [VIDEO] Code: https://github.com/Ololadestephen/cassa

## Prepared survey answers

Project name:

> Cassa

Project description:

> Cassa is a Binance cash-readiness agent that discovers spendable and small
> balances, protects obligations and reserves, answers “Can I afford this?”,
> and creates immutable, cost-bounded funding plans with explicit approvals,
> idempotent execution, reconciliation, and receipts.

How Agent OS is used:

> Cassa uses Binance Agent OS through the supported Codex host to read the
> dedicated Agentic Spot account without copying OAuth tokens or API keys into
> the application. A local Cassa MCP tool validates and stores exact read-only
> observations for the deterministic decision engine. Provider writes remain
> disabled until their schemas, permissions, quotes, and confirmation flow are
> verified on the connected account.

Primary user problem:

> Portfolio value is not spendable cash. Funds may be locked, protected,
> reserved for obligations, unpriced, or below a provider route minimum. Cassa
> determines what can safely fund a payment before anything moves.

Technical stack:

> Binance Agent OS MCP, Codex, a local Cassa MCP server, FastAPI, Python Decimal
> calculations, SQLite transactional state, Next.js, and TypeScript.

Safety and permissions:

> Read-only Agent OS snapshot ingestion, no withdrawal path, protected-asset
> and reserve enforcement, immutable versioned approvals, dollar-equivalent
> caps, quote expiry and cost bounds, unique operation IDs, persisted receipts,
> partial-failure reporting, and reconciliation before retry.

## Final submission checklist

- [ ] Follow `@Binance` and repost the official hackathon announcement.
- [ ] Record and upload the demo; verify the link is publicly viewable.
- [ ] Replace `[VIDEO]` in the X copy and post it as a reply or quote-repost.
- [ ] Confirm the GitHub repository is public and the README renders correctly.
- [ ] Complete the survey linked from the official announcement.
- [ ] Confirm jurisdiction and Binance-account eligibility.
- [ ] Finish all steps before September 8, 2026 at 23:59 UTC.
