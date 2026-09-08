"use client";
import { useEffect, useState } from "react";
import { API, api, timeAgo } from "../../lib/api";

function resultOf(row: any): string {
  if (row.ok === false && row.reason === "SKILL_UNAVAILABLE") return "SKILL_UNAVAILABLE";
  if (row.ok === false) return "VETO";
  if (row.needs_confirm) return "NEEDS_CONFIRM";
  return "EXECUTED";
}

function tone(result: string) {
  if (result === "EXECUTED") return "bg-green-900 text-green-300";
  if (result === "NEEDS_CONFIRM") return "bg-yellow-900 text-yellow-300";
  if (result === "SKILL_UNAVAILABLE") return "bg-red-900 text-red-300";
  return "bg-zinc-700 text-zinc-200";
}

export default function LedgerPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [receipts, setReceipts] = useState<any[]>([]);
  const [reconciliations, setReconciliations] = useState<any[]>([]);
  const [evidence, setEvidence] = useState<Record<string, string>>({});
  const [actionError, setActionError] = useState("");
  const [down, setDown] = useState(false);

  useEffect(() => {
    Promise.all([api.activity(), api.receipts(), api.reconciliations()])
      .then(([activity, receiptRows, unresolved]) => { setRows(activity); setReceipts(receiptRows); setReconciliations(unresolved); })
      .catch(() => setDown(true));
  }, []);

  async function resolveFailed(operationId: string) {
    setActionError("");
    try {
      await api.resolveFailed(operationId, evidence[operationId] ?? "");
      setReconciliations(await api.reconciliations());
    } catch (error: any) {
      let reason = error.message;
      try { reason = JSON.parse(error.message)?.detail ?? error.message; } catch {}
      setActionError(String(reason).slice(0, 300));
    }
  }

  if (down) return <main className="max-w-4xl mx-auto p-6"><div className="card">Backend unreachable — ledger unknown until it is back.</div></main>;

  return (
    <main className="max-w-4xl mx-auto p-4 md:p-6 space-y-4">
      <header className="pt-2">
        <p className="eyebrow mb-1.5">Cassaforte</p>
        <h1 className="text-3xl font-extrabold tracking-tight">Ledger</h1>
        <p className="text-sm text-zinc-400">Append-only. One sequence number per record; results are stated exactly as the API returned them.</p>
      </header>
      <section className="card">
        {rows.length === 0 ? (
          <p className="text-sm text-zinc-500">No records yet. Previews that pass and confirmations that run appear here.</p>
        ) : (
          <div className="divide-y divide-zinc-800">
            {rows.map((r: any) => {
              const result = resultOf(r);
              return (
                <div key={r.ledger_entry_id} className="py-3 text-sm grid gap-1 md:grid-cols-[90px_1fr_auto] md:items-center">
                  <span className="font-mono text-zinc-500">#{r.ledger_entry_id}</span>
                  <div>
                    <div>
                      {r.type === "pay" && <>Sent ${r.amount} {r.asset} → @{r.to}</>}
                      {r.type === "sweep" && <>{r.summary ?? "Sweep"}</>}
                      {r.type === "earn" && <>Earn request</>}
                      {r.type === "x402" && <>x402 request {r.amount} {r.asset}</>}
                      {!["pay", "sweep", "earn", "x402"].includes(r.type) && <>{r.type}</>}
                      {r.memo ? <span className="text-zinc-500"> · {r.memo}</span> : null}
                    </div>
                    <div className="text-xs text-zinc-500">
                      {r.recorded_at ? new Date(r.recorded_at * 1000).toLocaleString() : ""} ({r.recorded_at ? timeAgo(r.recorded_at) : "—"})
                      {r.day ? ` · day ${r.day}` : ""} · {r.mode ?? r.rail ?? ""}
                      {r.reason ? ` · ${r.reason}` : ""}
                      {r.detail ? ` · ${r.detail}` : ""}
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full justify-self-start ${tone(result)}`}>{result}</span>
                </div>
              );
            })}
          </div>
        )}
      </section>
      <section className="card">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <div>
            <h2 className="font-semibold">Provider receipts</h2>
            <p className="text-xs text-zinc-500">Conversion evidence and completed internal transfers.</p>
          </div>
          <a className="btn-ghost text-xs" href={`${API}/api/receipts/export.csv`}>Export CSV</a>
        </div>
        {receipts.length === 0 ? <p className="text-sm text-zinc-500">No completed actions have receipts yet.</p> : (
          <div className="divide-y divide-zinc-800">
            {receipts.map((receipt) => (
              <div key={receipt.receipt_id} className="py-2 text-sm flex flex-wrap justify-between gap-2">
                <div><strong>{receipt.kind === 'small_balance_conversion' ? `${receipt.from_asset} → USDC` : `${receipt.from_amount} ${receipt.from_asset} → @${receipt.recipient}`}</strong><p className="text-xs text-zinc-500">provider {receipt.provider_id} · {receipt.recorded_at}</p></div>
                <div className="text-right">{receipt.net_usdc != null ? `$${Number(receipt.net_usdc).toFixed(2)} net` : receipt.state}<p className="text-xs text-zinc-500">{receipt.fee_usdc != null ? `$${Number(receipt.fee_usdc).toFixed(2)} fee` : 'fee not reported'}</p></div>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="card">
        <h2 className="font-semibold">Reconciliation</h2>
        <p className="text-xs text-zinc-500 mb-2">An ambiguous provider response stays locked. Resolve it only after provider history confirms that no action occurred.</p>
        {actionError && <p className="text-sm text-red-400 mb-2">{actionError}</p>}
        {reconciliations.length === 0 ? <p className="text-sm text-emerald-300">No unresolved executions.</p> : reconciliations.map((item) => (
          <div key={item.operation_id} className="py-3 border-t border-zinc-800 space-y-2">
            <p className="text-sm"><strong>{item.kind}</strong> · {item.operation_id}</p>
            <p className="text-xs text-zinc-500">{item.result?.error ?? 'Provider result is unresolved.'}</p>
            <div className="flex flex-col md:flex-row gap-2">
              <input className="input" value={evidence[item.operation_id] ?? ''} onChange={(event) => setEvidence((current) => ({ ...current, [item.operation_id]: event.target.value }))} placeholder="Provider history reference confirming failure" />
              <button className="btn-ghost" onClick={() => resolveFailed(item.operation_id)}>Record confirmed failure</button>
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}
