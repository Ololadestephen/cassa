# Cassa — Know What You Can Afford
Cash readiness for Binance holdings: protect reserves, recover eligible small
balances, prepare payment funds, and review every action before execution.

Hackathon recording, claims, X copy, and final checklist: [`SUBMISSION.md`](SUBMISSION.md).

## Modes
- `CASSA_PROVIDER=paper` (default): local paper ledger with the same request/response
  schemas as live, priced at live public market data. Preview → confirm →
  ledger entry all execute for real against the local ledger.
- `CASSA_PROVIDER=agent-os-readonly`: a read-only Agentic Spot snapshot imported
  from Binance Agent OS by the supported Codex host. Every trade, conversion,
  transfer, and Earn write is hard-disabled in this mode.
- `CASSA_PROVIDER=binance-rest`: older live exchange adapter. Requires `BINANCE_API_KEY` +
  `BINANCE_API_SECRET` and fails closed without them. Testnet first.

`MOCK_MODE=true|false` remains a backwards-compatible fallback only when
`CASSA_PROVIDER` is unset.

The application REST adapter and the Binance Agent OS MCP connection are
separate trust boundaries. REST keys belong only in the local `.env`. MCP uses
browser OAuth stored by the supported agent host; MCP credentials never belong
in this repository or `.env`.

## Connect Binance Agent OS through Codex

Binance rejected Cassa's attempted standalone OAuth client with its
"AI Agent ... not currently supported" response. Binance Login OAuth is
currently partner-only, so the app no longer presents a misleading direct
connect button or stores MCP credentials. Authentication stays in a supported
host—Codex—and Cassa receives only validated, credential-free observations.

For an independent Codex-hosted capability check, this repository also includes
`.codex/config.toml`. After trusting the project, authenticate once:

```bash
codex mcp login binance-agent-os
```

Restart Codex so it loads both configured MCP servers, then run the read-only
sync:

> Use the Binance MCP Server to read my Agentic Spot balances, then sync those
> exact balances to Cassa. Do not trade, convert, or transfer anything.

On 2026-09-08 this flow authenticated successfully and returned the funded
Agentic Spot balances recorded in `CAPABILITIES.md`. See
`CAPABILITIES.md` for the exact evidence and limitations, and `AGENT.md` for the
agent workflow and safety contract.

## Current capability surface
Market data, balances, positions, Spot, internal sub-account transfer, and
Simple Earn REST/paper adapters exist. Binance MCP authentication and the
Agentic Spot balance read are live-verified through the Codex host; the app uses
a local Cassa MCP tool to persist a read-only snapshot without copying tokens.
MCP dust conversion, external
recipient settlement, and Earn actions are not verified.
Paper mode includes dynamic small-balance discovery, reviewable funding plans,
and receipt-backed conversion into USDC. Live dust execution remains disabled
until authenticated account-level verification succeeds.
x402 is gated:
`/api/x402/preview` and `/api/x402/pay` return
`{ "ok": false, "reason": "SKILL_UNAVAILABLE" }` and write an activity record.

## Policy as code (backend/policy.py, enforced before any execute)
- Allowlist: recipient must exist in `/api/addressbook`.
- No external withdraw: on-chain-looking destinations are rejected.
- Per-pay and daily caps use USDC-equivalent value for every supported asset.
- Every live write needs explicit confirmation; larger payments are also marked by the policy threshold.
- Active obligations and the minimum cash reserve reduce spendable USDC.

## Run
```bash
cd cassa
cp .env.example .env
.venv/bin/python -m uvicorn backend.main:app --port 8000
cd frontend && npm install && npm run dev
```
Success: backend `/api/health` identifies paper, Agent OS read-only, and REST boundaries;
`/api/market` returns four live symbols; `/api/capabilities` describes provider
boundaries; and the frontend builds with zero type errors.

## Implemented cash-readiness workflow

- `GET /api/portfolio`: dynamic priced holdings, protected assets, obligations,
  spendable USDC, and provider-eligible paper dust.
- `POST /api/affordability`: deterministic **Can I afford this?** result with
  shortfall, reserve, selected conversion estimates, and settlement status.
- `/api/plans`: persist an immutable, expiring funding plan; review its exact
  assets and estimated fees; approve its version; then execute it once in paper
  mode. Completed steps retain provider-style receipt IDs and actual proceeds.
- `/api/receipts` and `/api/receipts/export.csv`: inspect or export conversion
  and completed internal-payment evidence.
- `/api/reconciliations`: list ambiguous provider outcomes. After provider
  history confirms no action occurred, record that evidence and close the
  failed attempt without blindly retrying it.
- `/api/obligations`: create and track reserved payment obligations.
- `/api/asset-policies/{asset}`: protect a holding or retain a minimum quantity.
- `GET /api/capabilities`: distinguishes available, paper, unverified, and
  unavailable provider functions.
- `POST /api/paper/reset`: deliberately clears local paper activity and restores
  the documented 18 USDC demo scenario. It is unavailable outside paper mode.

Financial state is stored transactionally in SQLite. Existing JSON data is
imported on first access and retained as a backup.

Funding-plan execution prepares USDC and changes a linked obligation to `ready`.
It never marks the recipient paid. The current settlement adapter is limited to
allowlisted internal transfers; its separately confirmed request must match the
linked obligation before a successful provider response changes it to `paid`.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s backend/tests -v
cd frontend && npm run build
```

## Chat parsing (rules by default, Groq optional)
The desk ships with a deterministic rules router: `balance`, `sweep`,
`pay @name amount ASSET`, `prices`, `digest`. Set `LLM_PARSER=true` plus
`GROQ_API_KEY` to let Groq map free phrasing to the same intents
(`GROQ_MODEL` defaults to `llama-3.3-70b-versatile`). The parser only fills
preview arguments. Chat never supplies approval: live payments and investment
sweeps must use their explicit review paths. Parser failures fall back to rules.
`/api/health` reports `parser: rules|groq`.

## Demo and submission

Use `DEMO.md` for the current cash-readiness story. Paper and preview results
must be labeled as such. Only describe dust conversion, settlement, or Earn as
live after preserving an authenticated provider receipt for that capability.
The prepared Track A pitch, X copy, survey answers, and final checklist are in
`SUBMISSION.md`.
