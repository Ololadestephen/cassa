# Working on Cassa

## Mission and source of truth

Read `PLAN.md` before substantial product or architecture changes. Cassa is a cash-readiness agent: discover spendable funds, recover eligible small balances, evaluate affordability, prepare obligations, and execute only approved supported actions.

The flagship feature is **Can I afford this?**, connected to a payment funding planner. Dust means small total holding value, not a token's unit price. Support discovered eligible assets rather than hardcoding major coins. Keep optional investing separate from operational reserves.

Follow the user's authorized scope. A review or planning request does not authorize implementation, publishing, account changes, or transactions. Do not spawn subagents unless the user explicitly requests delegation or another applicable instruction requires it.

## Repository and commands

- Backend: `backend/`, FastAPI and Python; existing virtual environment is `.venv/` at repository root.
- Frontend: `frontend/`, Next.js App Router and TypeScript.
- Current data: `backend/data/`; preserve it unless a reset is explicitly requested.
- Documentation: `PLAN.md`, `README.md`, `DEMO.md`.

Run from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -c "import backend.main"
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
frontend/node_modules/.bin/tsc -p frontend/tsconfig.json --noEmit --incremental false
```

Run `npm run build` from `frontend/` when relevant and filesystem permissions permit. The isolated financial regression suite is in `backend/tests/`; extend it for changed money or execution behavior and keep its command accurate in the README. Never claim a test passed without running it.

## Inspect before changing

Check current files and Git state; this directory did not have a Git repository when initially reviewed. Preserve unrelated edits, credentials, and ledger state. Do not assume README claims prove a capability works. Update plan status based on tested implementation, and keep setup/demo claims consistent with actual behavior.

Regression-sensitive behaviors that were previously defective and now have tests:

- Sweep must use the post-trade balance for Earn and report partial failures.
- Chat must never supply payment or investment confirmation.
- Dollar caps must cover the USDC-equivalent value of every supported payment asset.
- Payment preview, obligations, reserves, and Earn descriptions must stay consistent.
- SQLite transactions, operation IDs, plan claims, and asset locks must prevent conflicting or duplicate execution.

## Provider boundaries

Consult current official Binance documentation before implementing an endpoint; validate exact schemas and permissions. `PLAN.md` contains verified source links and unresolved capability checks.

- MCP Convert support does not establish MCP dust support.
- Agentic MCP wallet transfers stay inside the same sub-account; do not present them as arbitrary recipient payments.
- Main-account read access does not authorize moving its funds.
- Dust discovery and execution use distinct signed endpoints. Discover eligibility and target support before proposing a conversion.
- Do not assume Wallet SAPI or Earn works on Spot testnet.
- UI support for a wallet or asset does not prove API access for the connected account.
- Keep documented, account-verified, paper-only, and unavailable capabilities distinct.
- Use account eligibility and current provider data for fees, minimums, and limits; do not universally hardcode FAQ examples.

## Financial and execution invariants

- Use Decimal for monetary calculations and preserve provider precision. Do not use binary floats as the basis of ledger arithmetic.
- Separate free, locked, protected, reserved, and read-only funds. Missing valuation is unknown, not zero.
- Count each obligation and fee once. Deduct reserves before proposing investment or surplus Earn.
- Recheck balances, policy, quote validity, and account permissions before writing.
- Planning, affordability, and preview operations do not trade or pay.
- Bind explicit approval to an immutable plan version and its account, recipient, assets, amounts/bounds, costs, and validity window.
- An LLM may propose structured intent; it cannot grant confirmation, change policy, or invoke an unrestricted execution path.
- Chat and forms use the same deterministic planning, policy, and execution services.
- Apply dollar-equivalent payment limits to every supported asset; reject valuation-dependent writes when a reliable valuation is missing.
- Respect provider confirmation requirements for every relevant write.
- Persist each execution step and provider identifier. After ambiguous timeouts, reconcile before retrying.
- Never retry an entire multi-step plan blindly or repeat a completed payment.
- Report partial success and unresolved outcomes honestly. Conversions and payments are not atomic.
- Conversion success means funds prepared, not an invoice paid. Settlement requires a verified supported rail and evidence.

## Architecture and product practices

Separate provider adapters from portfolio, affordability, planner, policy, execution, obligations, and receipt services. Migrate mutable JSON state to transactional persistence with an explicit preservation strategy. Use authenticated account ownership before live writes or public exposure.

Keep UI explanations focused on user decisions: spendable cash, net proceeds, costs, protected assets, remaining reserve, and next action. Clearly label preview, paper, live, unavailable, and needs-reconciliation states. Never display estimated returns as guaranteed income.

Do not add unrelated trading features to increase feature count. New work should advance the connected funding and affordability workflow or its reliability.

## Verification and handoff

For financial changes, test conservation of balances, fee handling, reserve protection, asset precision, quote expiry, explicit confirmation, duplicate requests, partial failures, and reconciliation. Include the 18 USDC / 25 USDC expense / 5 USDC reserve example: the shortfall is 12 USDC before additional payment fees.

Use isolated temporary data or mocks for tests. Never run tests against the user's ledger or live write APIs by default. An approved implementation task alone does not authorize a real trade, conversion, subscription, or payment; show the concrete transaction and obtain the required approval before executing it.

Never print or commit `.env`, API keys, signatures, access tokens, or authenticated connection URLs. Add appropriate ignore rules before preparing a repository commit; do not overwrite secrets or user data while doing so.

Finish with what changed, checks actually run, unresolved limitations, and the next relevant implementation step. Update `PLAN.md` completion status only when its acceptance gate is met. Do not invent completion percentages or claim live capability from paper tests.
