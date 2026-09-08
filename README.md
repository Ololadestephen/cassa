# Cassa

**Know what you can safely spend before anything moves.**

A wallet total is not cash. Cassa reads holdings, subtracts reserves and
obligations, skips protected or unusable assets, and prepares only the
shortfall — with an exact approval and a receipt.

**Live demo:** [cassa-sigma.vercel.app](https://cassa-sigma.vercel.app/)

The public demo runs on the **paper ledger**. Prices are live public market
data. Conversions and payments execute against local state, not a live Binance
write.

## What it does

1. Show free, reserved, protected, and unpriced balances separately.
2. Answer **Can I afford this?** against a reserve and existing obligations.
3. Build the smallest funding plan that covers the gap.
4. Bind approval to that exact plan version.
5. Execute once, then store receipts. Conversion prepares USDC; it does not
   pay a recipient.

The repeatable demo case: 18 USDC free, 25 USDC expense, 5 USDC reserve. The
shortfall is 12 USDC before payment fees.

## Stack

- FastAPI + Python (`Decimal` for money)
- SQLite for plans, approvals, receipts, and obligations
- Next.js 14 + TypeScript
- Public Binance market data for prices

## Run locally

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Point the frontend at the
API with `NEXT_PUBLIC_API=http://localhost:8000` in `frontend/.env.local` if
needed.

Default provider is paper:

```
CASSA_PROVIDER=paper
```

Reset the documented paper scenario:

```bash
curl -X POST http://127.0.0.1:8000/api/paper/reset
```

## Safety

- Planning and affordability never move funds.
- Chat cannot approve a write.
- Recipients must be allowlisted. External withdrawals are rejected.
- Per-send and daily caps apply to USDC-equivalent value.
- Ambiguous provider results stay unresolved until they are reconciled. No
  blind retries.

Live Binance Agent OS reads were verified through a supported Codex host.
Standalone app OAuth was rejected. Live dust conversion, external settlement,
and Earn writes are not enabled.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s backend/tests -v
cd frontend && npm run build
```

## License

Private / demo project.
