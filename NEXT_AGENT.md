# Cassa next-agent execution brief

You are taking over Cassa in `/Users/apple/Documents/cassa`. The user is upset
because substantial work went into a polished paper-mode website before the
live Binance execution path was proven. Do not repeat that mistake.

## Objective

Turn Cassa into a credible Binance Agent OS submission by proving the strongest
safe live workflow available through a supported agent host. The intended
architecture is agent-native:

- Binance Agent OS in Codex is the authenticated execution plane.
- Cassa is the deterministic affordability, reserve, policy, planning,
  approval, reconciliation, and evidence engine.
- The website is a decision and evidence companion. It is not the Binance
  credential holder.

The immediate target is one reproducible flow:

1. Read real Agentic Spot balances through Binance MCP.
2. Sync the exact observation into Cassa without credentials.
3. Calculate whether a stated USDC expense can be funded while preserving the
   reserve and protected assets.
4. Discover an exact supported Spot funding action.
5. Present its account, asset, amount, fees or bounds, expiry, and expected
   result for explicit user approval.
6. Only after that exact approval, execute once through Binance MCP.
7. Re-read balances and store provider evidence. Never describe conversion as
   recipient settlement.

## Read before doing anything

Read these files in order:

1. `AGENTS.md`
2. `NEXT_PLAN.md`
3. `PLAN.md`
4. `CAPABILITIES.md`
5. `AGENT.md`
6. `SUBMISSION.md`

Then inspect Git status and the relevant implementation. Preserve user data,
credentials, and unrelated changes.

## Facts already established

- Repository: `https://github.com/Ololadestephen/cassa`, branch `main`.
- Render paper backend: `https://cassa-m5n6.onrender.com`.
- Binance Agent OS OAuth works inside the supported Codex host.
- `spot.getAccount` returned the funded Agentic Spot account.
- The last recorded nonzero balances were 6 USDT, 0.057 TWT, 0.892 USTC,
  0.18667147 TIA, and 1.03433979 1000CAT, all free at observation time.
- Read-only ordinary Convert metadata exposed USDC routes for those assets.
  USTC and 1000CAT were below the observed ordinary Convert minimums; route
  metadata is not a quote or execution permission.
- Standalone Cassa OAuth was rejected as an unsupported agent.
- No live dust conversion, external recipient payment, or Earn action has been
  verified.
- The public backend intentionally runs in paper mode because it has no owner
  authentication and cannot inherit a visitor's private Codex MCP session.

Treat every balance, minimum, tool schema, and permission as stale until it is
read again.

## Required operating rules

- Do not redesign the site or add speculative features before the live
  capability gate is resolved.
- Do not call a write tool during capability discovery.
- Do not trade, convert, transfer, subscribe, redeem, or pay without showing
  the complete proposed action and receiving explicit approval for it in the
  current conversation.
- Chat language never constitutes financial approval.
- Prefer a minimal ordinary Spot Convert to USDC if and only if the connected
  MCP exposes exact quote, accept, and status tools. Do not substitute a
  futures Convert tool.
- Do not use a Spot market order unless the exact symbol, quantity filters,
  expected proceeds, fees, and post-trade reconciliation path are established.
- Do not present Agentic wallet-to-wallet movement as payment to an arbitrary
  recipient. External settlement is a separate capability.
- Never expose OAuth URLs, tokens, API keys, signatures, account identifiers,
  or authenticated connection strings.
- Use Decimal for application money calculations. Treat missing valuation as
  unknown, not zero.
- Persist provider identifiers and reconcile ambiguous outcomes before retry.
- Keep live provider facts, estimates, user inputs, and paper fixtures visibly
  distinct in code, UI, documentation, and the demo.

## First work item: bounded live capability audit

Without mutating the account, dynamically discover and record only the tools
needed to answer these questions:

1. Does the connected Agentic Spot account expose ordinary Spot Convert quote,
   accept, and status tools?
2. If not, does it expose a direct Spot order path for any currently held,
   unprotected asset into USDC, with readable filters and status?
3. Is there an exact small-balance/dust eligibility query with USDC as target?
4. Is any payment tool an external settlement rail, or only an internal
   Agentic-account transfer?
5. What confirmation does Binance require for each available write?

Keep discovery narrow. Save exact schemas and dated observations in
`CAPABILITIES.md`. “Not found” means unavailable for this implementation until
new evidence appears.

## Decision after the audit

- If a safe Spot Convert path exists, prepare the smallest useful USDT-to-USDC
  proposal that satisfies the current provider minimum. Stop and request exact
  user approval before accepting the quote.
- If only Spot orders exist, prepare one bounded sell proposal only after
  proving the symbol and filters. Stop for approval.
- If neither exists, do not fabricate live execution. Complete the submission
  around the verified live read plus Cassa's deterministic safety decisions,
  and state the limitation plainly.
- Do not spend time trying to make arbitrary external payments through a tool
  whose documented boundary excludes withdrawal or recipient settlement.

## Verification commands

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -c "import backend.main"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s backend/tests -v
frontend/node_modules/.bin/tsc -p frontend/tsconfig.json --noEmit --incremental false
cd frontend && npm run build
```

Use temporary isolated data for tests. Never run tests against the user's live
ledger or provider write APIs.

## Required handoff result

Report:

- Exact live tools and scopes found.
- Exact actions still unavailable.
- What code changed and why.
- Checks actually run.
- Provider evidence obtained, with secrets removed.
- The next concrete action requiring user approval.

Do not claim success because a mock or paper test passed.
